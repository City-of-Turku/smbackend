import json
import logging
import re
import zoneinfo
from datetime import datetime, timedelta

import numpy as np
import polyline
import requests
from django import db
from django.conf import settings
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import LineString, Point
from django.utils import timezone
from munigeo.models import AdministrativeDivision, AdministrativeDivisionGeometry
from munigeo.utils import get_default_srid

from maintenance.models import (
    DEFAULT_SRID,
    GeometryHistory,
    MaintenanceUnit,
    MaintenanceWork,
    SPORT_NAMES_UNIT_EXTRA_KEY,
    UnitMaintenance,
)
from services.models import Unit

from .constants import (
    CONTRACTS,
    EVENT_MAPPINGS,
    EVENTS,
    INFRAROAD,
    KUNTEC,
    KUNTEC_KEY,
    ROUTES,
    TIMESTAMP_FORMATS,
    TOKEN,
    UNITS,
    URLS,
    VEHICLES,
    WORKS,
    YIT,
)

logger = logging.getLogger("maintenance")

SPORTS_FACILITY_UNIT_ID_OFFSET = 100000

# In seconds
MAX_WORK_LENGTH = 60
VALID_LINESTRING_MAX_POINT_DISTANCE = 0.01


def get_turku_boundary():
    try:
        division_turku = AdministrativeDivision.objects.get(name="Turku")
    except AdministrativeDivision.DoesNotExist:
        return None
    turku_boundary = AdministrativeDivisionGeometry.objects.get(
        division=division_turku
    ).boundary
    turku_boundary.transform(DEFAULT_SRID)
    return turku_boundary


TURKU_BOUNDARY = get_turku_boundary()


def get_json_data(url):
    if url.startswith(URLS[INFRAROAD][WORKS].split("=")[0] + "="):
        response = requests.get(url, headers=URLS[INFRAROAD][TOKEN])
    else:
        response = requests.get(url)
    if response.status_code != 200:
        logger.warning(
            f"Fetching Maintenance Unit {url} status code: {response.status_code} response: {response.content}"
        )
        return {}
    return response.json()


def check_linestring_validity(
    linestring, threshold=VALID_LINESTRING_MAX_POINT_DISTANCE
):
    """
    The LineString is considered invalid if distance between two points is
    greater than VALID_LINESTRING_MAX_POINT_DISTANCE.
    The lower the threshold value the more serve the validating will be.
    """
    prev_coord = None
    for coord in linestring.coords:
        if prev_coord:
            p1 = Point(coord, srid=DEFAULT_SRID)
            p2 = Point(prev_coord, srid=DEFAULT_SRID)
            if p1.distance(p2) > threshold:
                return False
        prev_coord = coord
    return True


def add_geometry_history_objects(objects, points, elem, provider):
    """
    A GeometryHistory instance is added to objects that is passed by reference.
    Returns number of discarded linestring.
    """
    geometry = LineString(points, srid=DEFAULT_SRID)
    if check_linestring_validity(geometry, 0.005):
        objects.append(
            GeometryHistory(
                provider=provider,
                coordinates=geometry.coords,
                timestamp=elem.timestamp,
                events=elem.events,
                geometry=geometry,
            )
        )
        return 0
    else:
        return 1


def get_valid_linestrings(linestring, threshold=VALID_LINESTRING_MAX_POINT_DISTANCE):
    prev_coord = None
    coords = []
    geometries = []
    for coord in linestring.coords:
        if prev_coord:
            p1 = Point(coord, srid=DEFAULT_SRID)
            p2 = Point(prev_coord, srid=DEFAULT_SRID)
            if p1.distance(p2) > threshold:
                if len(coords) > 1:
                    geometries.append(LineString(coords, srid=DEFAULT_SRID))
                    coords = [prev_coord]
                else:
                    coords = []

        coords.append(coord)
        prev_coord = coord

    if len(coords) > 1:
        geometry = LineString(coords, srid=DEFAULT_SRID)
        if check_linestring_validity(geometry, threshold):
            geometries.append(geometry)
    return geometries


def get_linestrings_from_points(objects, queryset, provider):
    """
    Point data is generated into LineStrings. This is done by iterating the
    point data for every MaintenanceUnit for the given provider.
    """
    unit_ids = (
        queryset.order_by("maintenance_unit_id")
        .values_list("maintenance_unit_id", flat=True)
        .distinct("maintenance_unit_id")
    )
    discarded_linestrings = 0
    discarded_points = 0
    for unit_id in unit_ids:
        # Temporary store points to list for LineString creation
        points = []
        qs = queryset.filter(maintenance_unit_id=unit_id).order_by(
            "events", "timestamp"
        )
        prev_timestamp = None
        current_events = None
        prev_geometry = None

        for elem in qs:
            if not current_events:
                current_events = elem.events
            if prev_timestamp and prev_geometry:
                delta_time = abs(elem.timestamp - prev_timestamp)
                # If delta_time is bigger than the MAX_WORK_LENGTH, then we can assume
                # that the work should not be in the same linestring/point or the events
                # has changed.
                if (
                    delta_time.seconds > MAX_WORK_LENGTH
                    or current_events != elem.events
                ):
                    if len(points) > 1:
                        discarded_linestrings += add_geometry_history_objects(
                            objects, points, elem, provider
                        )
                    else:
                        discarded_points += 1
                    current_events = elem.events
                    points = []
            prev_geometry = elem.geometry
            points.append(elem.geometry)
            prev_timestamp = elem.timestamp
        if len(points) > 1:
            discarded_linestrings += add_geometry_history_objects(
                objects, points, elem, provider
            )
    return discarded_linestrings, discarded_points


@db.transaction.atomic
def precalculate_geometry_history(provider):
    """
    Function that populates the GeometryHistory model for a provider.
    LineString geometries in MaintenanceWorks will be added as they are.
    """
    GeometryHistory.objects.filter(provider=provider).delete()
    objects = []
    queryset = MaintenanceWork.objects.filter(
        maintenance_unit__provider=provider
    ).order_by("timestamp")
    elements_to_remove = []
    # Add works that are linestrings,
    discarded_linestrings = 0
    discarded_points = 0
    for elem in queryset:
        if isinstance(elem.geometry, LineString):
            if check_linestring_validity(elem.geometry):
                objects.append(
                    GeometryHistory(
                        provider=provider,
                        coordinates=elem.geometry.coords,
                        timestamp=elem.timestamp,
                        events=elem.events,
                        geometry=elem.geometry,
                    )
                )
            else:
                discarded_linestrings += 1
            elements_to_remove.append(elem.id)

    # Remove the linestring elements, as they are not needed when generating
    # linestrings from point data
    queryset = queryset.exclude(id__in=elements_to_remove)
    results = get_linestrings_from_points(objects, queryset, provider)
    discarded_linestrings += results[0]
    discarded_points += results[1]
    GeometryHistory.objects.bulk_create(objects)
    logger.info(f"Discarded {discarded_points} points in linestring generation")
    logger.info(f"Discarded {discarded_linestrings} invalid LineStrings")
    logger.info(f"Created {len(objects)} HistoryGeometry rows for provider: {provider}")


def get_linestring_in_boundary(linestring, boundary):
    """
    Returns a linestring from the input linestring where all the coordinates
    are inside the boundary. If linestring creation is not possible return False.
    """
    coords = [
        coord
        for coord in linestring.coords
        if boundary.covers(Point(coord, srid=DEFAULT_SRID))
    ]
    if len(coords) > 1:
        linestring = LineString(coords, srid=DEFAULT_SRID)
        return linestring
    else:
        return False


def handle_unit(filter, objs_to_delete):
    num_created = 0
    queryset = MaintenanceUnit.objects.filter(**filter)
    queryset_count = queryset.count()
    if queryset_count == 0:
        MaintenanceUnit.objects.create(**filter)
        num_created += 1
    else:
        # Keep the first element and if duplicates leave them for deletion.
        id = queryset.first().id
        if id in objs_to_delete:
            objs_to_delete.remove(id)
    return num_created


def handle_work(filter, objs_to_delete):
    num_created = 0
    queryset = MaintenanceWork.objects.filter(**filter)
    queryset_count = queryset.count()

    if queryset_count == 0:
        MaintenanceWork.objects.create(**filter)
        num_created += 1
    else:
        # Keep the first element and if duplicates leave them for deletion.
        id = queryset.first().id
        if id in objs_to_delete:
            objs_to_delete.remove(queryset.first().id)
    return num_created


@db.transaction.atomic
def create_yit_maintenance_works(access_token, history_size):
    contract = get_yit_contract(access_token)
    list_of_events = get_yit_event_types(access_token)
    event_name_mappings = create_dict_from_yit_events(list_of_events)
    routes = get_yit_routes(access_token, contract, history_size)
    objs_to_delete = list(
        MaintenanceWork.objects.filter(maintenance_unit__provider=YIT).values_list(
            "id", flat=True
        )
    )
    num_created = 0
    for route in routes:
        if len(route["geography"]["features"]) > 1:
            logger.warning(
                f"Route contains multiple features. {route['geography']['features']}"
            )
        coordinates = route["geography"]["features"][0]["geometry"]["coordinates"]

        if is_nested_coordinates(coordinates) and len(coordinates) > 1:
            geometry = LineString(coordinates, srid=DEFAULT_SRID)
        else:
            # Remove other data, contains faulty linestrings.
            continue
        # Create linestring that is inside the boundary of Turku
        # and discard parts of the geometry if they are outside the boundary.
        geometry = get_linestring_in_boundary(geometry, TURKU_BOUNDARY)
        if not geometry:
            continue
        events = []
        original_event_names = []
        operations = route["operations"]
        for operation in operations:
            event_name = event_name_mappings[operation].lower()
            if event_name in EVENT_MAPPINGS:
                for e in EVENT_MAPPINGS[event_name]:
                    # If mapping value is None, the event is not used.
                    if e:
                        if e not in events:
                            events.append(e)
                        original_event_names.append(event_name_mappings[operation])
            else:
                logger.warning(
                    f"Found unmapped event: {event_name_mappings[operation]}"
                )

        # If no events found discard the work
        if len(events) == 0:
            continue
        if len(route["geography"]["features"]) > 1:
            logger.warning(
                f"Route contains multiple features. {route['geography']['features']}"
            )
        unit_id = route["vehicleType"]
        try:
            unit = MaintenanceUnit.objects.get(unit_id=unit_id)
        except MaintenanceUnit.DoesNotExist:
            logger.warning(f"Maintenance unit: {unit_id}, not found.")
            continue
        filter = {
            "timestamp": route["startTime"],
            "maintenance_unit": unit,
            "geometry": geometry,
            "events": events,
            "original_event_names": original_event_names,
        }
        num_created += handle_work(filter, objs_to_delete)

    MaintenanceWork.objects.filter(id__in=objs_to_delete).delete()
    return num_created, len(objs_to_delete)


@db.transaction.atomic
def create_kuntec_maintenance_works(history_size):
    num_created = 0
    now = datetime.now()
    start = (now - timedelta(days=history_size)).strftime(TIMESTAMP_FORMATS[KUNTEC])
    end = now.strftime(TIMESTAMP_FORMATS[KUNTEC])
    objs_to_delete = list(
        MaintenanceWork.objects.filter(maintenance_unit__provider=KUNTEC).values_list(
            "id", flat=True
        )
    )
    for unit in MaintenanceUnit.objects.filter(provider=KUNTEC):
        url = URLS[KUNTEC][WORKS].format(
            key=KUNTEC_KEY, start=start, end=end, unit_id=unit.unit_id
        )
        json_data = get_json_data(url)
        if "data" in json_data:
            for unit_data in json_data["data"]["units"]:
                for route in unit_data["routes"]:
                    events = []
                    original_event_names = []
                    # Routes of type 'stop' are discarded.
                    if route["type"] == "route":
                        # Check for mapped events to include as works.
                        for name in unit.names:
                            event_name = name.lower()
                            if event_name in EVENT_MAPPINGS:
                                for e in EVENT_MAPPINGS[event_name]:
                                    # If mapping value is None, the event is not used.
                                    if e:
                                        if e not in events:
                                            events.append(e)
                                        original_event_names.append(name)
                            else:
                                logger.warning(f"Found unmapped event: {event_name}")
                    # If route has mapped event(s) and contains a polyline add work.
                    if len(events) > 0 and "polyline" in route:
                        coords = polyline.decode(route["polyline"], geojson=True)
                        if len(coords) > 1:
                            geometry = LineString(coords, srid=DEFAULT_SRID)
                        else:
                            continue
                        # Create linestring that is inside the boundary of Turku
                        # and discard parts of the geometry if they are outside the boundary.
                        geometry = get_linestring_in_boundary(geometry, TURKU_BOUNDARY)
                        if not geometry:
                            continue
                        timestamp = route["start"]["time"]
                        filter = {
                            "timestamp": timestamp,
                            "maintenance_unit": unit,
                            "geometry": geometry,
                            "events": events,
                            "original_event_names": original_event_names,
                        }
                        num_created += handle_work(filter, objs_to_delete)

    MaintenanceWork.objects.filter(id__in=objs_to_delete).delete()
    return num_created, len(objs_to_delete)


@db.transaction.atomic
def create_maintenance_works(provider, history_size, fetch_size):
    turku_boundary = get_turku_boundary()
    num_created = 0

    import_from_date_time = datetime.now() - timedelta(days=history_size)
    import_from_date_time = import_from_date_time.replace(
        tzinfo=zoneinfo.ZoneInfo("Europe/Helsinki")
    )
    objs_to_delete = list(
        MaintenanceWork.objects.filter(maintenance_unit__provider=provider).values_list(
            "id", flat=True
        )
    )
    for unit in MaintenanceUnit.objects.filter(provider=provider):
        json_data = get_json_data(
            URLS[provider][WORKS].format(
                id=unit.unit_id,
                history_size=fetch_size,
                start=import_from_date_time.strftime("%Y-%m-%dT%H:%M"),
                end=datetime.now().strftime("%Y-%m-%dT%H:%M"),
            )
        )
        if provider == INFRAROAD:
            json_data = transform_infraroad_routa(json_data)
        elif "location_history" in json_data:
            json_data = json_data["location_history"]
        else:
            logger.warning(f"Location history not found for unit: {unit.unit_id}")
            continue
        for work in json_data:
            timestamp = datetime.strptime(
                work["timestamp"], TIMESTAMP_FORMATS[provider]
            ).replace(tzinfo=zoneinfo.ZoneInfo("Europe/Helsinki"))
            # Discard events older than import_from_date_time as they will
            # never be displayed
            if timestamp < import_from_date_time:
                continue
            coords = work["coords"]
            coords = [float(c) for c in re.sub(r"[()]", "", coords).split(" ")]
            point = Point(coords[0], coords[1], srid=DEFAULT_SRID)
            # discard events outside Turku.
            if not turku_boundary.covers(point):
                continue

            events = []
            original_event_names = []
            for event in work["events"]:
                event_name = event.lower()
                if event_name in EVENT_MAPPINGS:
                    for e in EVENT_MAPPINGS[event_name]:
                        # If mapping value is None, the event is not used.
                        if e:
                            if e not in events:
                                events.append(e)
                            original_event_names.append(event)
                else:
                    logger.warning(f"Found unmapped event: {event}")
            # If no events found discard the work
            if len(events) == 0:
                continue
            filter = {
                "timestamp": timestamp,
                "maintenance_unit": unit,
                "geometry": point,
                "events": events,
                "original_event_names": original_event_names,
            }
            num_created += handle_work(filter, objs_to_delete)

    MaintenanceWork.objects.filter(id__in=objs_to_delete).delete()
    return num_created, len(objs_to_delete)


@db.transaction.atomic
def create_maintenance_units(provider):
    num_created = 0
    objs_to_delete = list(
        MaintenanceUnit.objects.filter(provider=provider).values_list("id", flat=True)
    )
    # Infraroad is not dependant on individual units, so use one unit for everything
    if provider == INFRAROAD:
        contract_number = re.search(r"contract=(\d+)", URLS[INFRAROAD][WORKS])
        unit_data = [
            {
                "id": contract_number.group(1) if contract_number else provider,
                "last_location": {"events": ["infraroad"]},
            }
        ]
    else:
        unit_data = get_json_data(URLS[provider][UNITS])
    for unit in unit_data:
        # The names of the unit is derived from the events.
        names = [n for n in unit["last_location"]["events"]]
        filter = {
            "unit_id": unit["id"],
            "names": names,
            "provider": provider,
        }
        num_created += handle_unit(filter, objs_to_delete)

    MaintenanceUnit.objects.filter(id__in=objs_to_delete).delete()
    return num_created, len(objs_to_delete)


def get_yit_contract(access_token):
    response = requests.get(
        URLS[YIT][CONTRACTS], headers={"Authorization": f"Bearer {access_token}"}
    )
    assert (
        response.status_code == 200
    ), "Fetcing YIT Contract {} failed, status code: {}".format(
        URLS[YIT][CONTRACTS], response.status_code
    )
    return response.json()[0].get("id", None)


def get_yit_event_types(access_token):
    response = requests.get(
        URLS[YIT][EVENTS], headers={"Authorization": f"Bearer {access_token}"}
    )
    assert (
        response.status_code == 200
    ), " Fetching YIT event types {} failed, status code: {}".format(
        URLS[YIT][EVENTS], response.status_code
    )
    return response.json()


def create_dict_from_yit_events(list_of_events):
    events = {}
    for event in list_of_events:
        events[event["id"]] = event["operationName"]
    return events


@db.transaction.atomic
def create_kuntec_maintenance_units():
    json_data = get_json_data(URLS[KUNTEC][UNITS])
    no_io_din = 0
    num_created = 0
    objs_to_delete = list(
        MaintenanceUnit.objects.filter(provider=KUNTEC).values_list("id", flat=True)
    )
    for unit in json_data["data"]["units"]:
        names = []
        if "io_din" in unit:
            on_states = 0
            # example io_din field: {'no': 3, 'label': 'Muu työ', 'state': 0}
            for io in unit["io_din"]:
                on_states += 1
                names.append(io["label"])
        # If names, we have a unit with at least one io_din with State On.
        if len(names) > 0:
            filter = {
                "unit_id": unit["unit_id"],
                "names": names,
                "provider": KUNTEC,
            }
            num_created += handle_unit(filter, objs_to_delete)
        else:
            no_io_din += 1
    MaintenanceUnit.objects.filter(id__in=objs_to_delete).delete()
    logger.info(f"Discarding {no_io_din} Kuntec units that do not have a io_din data.")
    return num_created, len(objs_to_delete)


def get_yit_vehicles(access_token):
    response = requests.get(
        URLS[YIT][VEHICLES], headers={"Authorization": f"Bearer {access_token}"}
    )
    assert (
        response.status_code == 200
    ), " Fetching YIT vehicles {} failed, status code: {}".format(
        URLS[YIT][VEHICLES], response.status_code
    )
    return response.json()


@db.transaction.atomic
def create_yit_maintenance_units(access_token):
    vehicles = get_yit_vehicles(access_token)
    num_created = 0
    objs_to_delete = list(
        MaintenanceUnit.objects.filter(provider=YIT).values_list("id", flat=True)
    )
    for unit in vehicles:
        names = [unit["vehicleTypeName"]]
        filter = {
            "unit_id": unit["id"],
            "names": names,
            "provider": YIT,
        }
        num_created += handle_unit(filter, objs_to_delete)

    MaintenanceUnit.objects.filter(id__in=objs_to_delete).delete()
    return num_created, len(objs_to_delete)


def get_yit_routes(access_token, contract, history_size):
    now = datetime.now()
    end = now.replace(tzinfo=zoneinfo.ZoneInfo("Europe/Helsinki")).strftime(
        TIMESTAMP_FORMATS[YIT]
    )
    start = (
        (now - timedelta(days=history_size))
        .replace(tzinfo=zoneinfo.ZoneInfo("Europe/Helsinki"))
        .strftime(TIMESTAMP_FORMATS[YIT])
    )
    params = {
        "contract": contract,
        "start": start,
        "end": end,
    }
    response = requests.get(
        URLS[YIT][ROUTES],
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
    )
    assert (
        response.status_code == 200
    ), "Fetching YIT routes {}, failed, status code: {}".format(
        URLS[YIT][ROUTES], response.status_code
    )
    return response.json()


def get_yit_access_token():
    """
    Note the IP address of the host calling Autori API (hosts YIT data) must be
    given for whitelistning.
    """
    assert settings.YIT_SCOPE, "YIT_SCOPE not defined in environment."
    assert settings.YIT_CLIENT_ID, "YIT_CLIENT_ID not defined in environment."
    assert settings.YIT_CLIENT_SECRET, "YIT_CLIENT_SECRET not defined in environment."
    data = {
        "grant_type": "client_credentials",
        "scope": settings.YIT_SCOPE,
        "client_id": settings.YIT_CLIENT_ID,
        "client_secret": settings.YIT_CLIENT_SECRET,
    }
    response = requests.post(URLS[YIT][TOKEN], data=data)
    assert (
        response.status_code == 200
    ), "Fetchin oauth2 token from YIT {} failed, status code: {}".format(
        URLS[YIT][TOKEN], response.status_code
    )
    access_token = response.json().get("access_token", None)
    return access_token


def is_nested_coordinates(coordinates):
    return bool(np.array(coordinates).ndim > 1)


def get_data_layer(url):
    ds = DataSource(url)
    assert len(ds) == 1
    return ds[0]


def get_unit_maintenance_instance(filter):
    is_created = False
    queryset = UnitMaintenance.objects.filter(**filter)

    if queryset.count() == 0:
        unit_maintenance = UnitMaintenance(**filter)
        is_created = True
    else:
        unit_maintenance = UnitMaintenance.objects.filter(**filter).first()
        if queryset.count() > 1:
            logger.warning(f"Found duplicate UnitMaintenance {filter}")

    return unit_maintenance, is_created


# Infraroad swithced from Fluentprogress to Routa as API provider
# Using current info, transforming that data into a list that existing functions can use
def transform_infraroad_routa(work):
    events = []
    for street in work:
        for geom in street["geometry"]:
            for task in street["tasks"]:
                timestamp = datetime.fromtimestamp(task["time"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                coords = f"({geom['x']} {geom['y']})"
                event_name = task["name"]

                events.append(
                    {"timestamp": timestamp, "coords": coords, "events": [event_name]}
                )
    return events


def _nonempty_str(value):
    return value is not None and str(value).strip() != ""


_NULL_WORD_IN_CONDITION_NOTE = re.compile(r"\bnull\b", re.IGNORECASE)


def sanitize_maintenance_condition_note(value):
    """
    Normalize API/legacy condition_note for JSON: None becomes JSON null.
    Treats missing/blank, JSON null, the literal \"null\", and strings containing
    the word \"null\" (e.g. model garbage like null<attention>null</attention>) as absent.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.lower() == "null":
        return None
    if _NULL_WORD_IN_CONDITION_NOTE.search(s):
        return None
    return s


def _bootstrap_sports_facility_name_without_translations(raw):
    """
    Display name when the source has no reliable per-language strings (e.g. ski
    maintenance). Uses the segment before the first '|' so piped placeholders are
    not stored verbatim on the unit.
    """
    if not _nonempty_str(raw):
        return ""
    text = str(raw).strip()
    first = text.split("|", 1)[0].strip()
    return first or text


def parse_trilingual_name(raw):
    """
    Parse finnish|swedish|english from the source name field.
    If there is no '|', use the same string for all languages.
    With two segments (fi|sv), English falls back to Finnish.
    """
    if raw is None:
        return "", "", ""
    text = str(raw).strip()
    if not text:
        return "", "", ""
    parts = [p.strip() for p in text.split("|")]
    if len(parts) == 1:
        n = parts[0]
        return n, n, n
    if len(parts) == 2:
        fi, sv = parts[0], parts[1]
        return fi, sv, fi
    return parts[0], parts[1], parts[2]


def apply_sport_facility_trilingual_names(unit, name_fi, name_sv, name_en):
    """Set unit.name, name_fi/sv/en (DB), and extra sport_names for sports imports."""
    sf = name_fi or ""
    sv = name_sv if name_sv else sf
    sen = name_en if name_en else sf
    unit.name = sf
    unit.name_fi = sf
    unit.name_sv = sv
    unit.name_en = sen
    extra = dict(unit.extra) if unit.extra else {}
    extra[SPORT_NAMES_UNIT_EXTRA_KEY] = {"fi": sf, "sv": sv, "en": sen}
    unit.extra = extra


def _services_unit_description_json_string(payload: dict) -> str:
    """
    Value for services_unit.description: a single JSON object as a Unicode string
    (json.dumps), never a Python dict.
    """
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _is_ski_trail_description_json(obj):
    return (
        isinstance(obj, dict)
        and "length" in obj
        and "lights" in obj
        and "condition_note" in obj
        and "description" not in obj
    )


def _is_ice_track_description_json(obj):
    return isinstance(obj, dict) and "condition_note" in obj and "description" in obj


def _ski_json_str(value):
    return "" if value is None else str(value)


def merge_ski_trail_unit_description(
    existing_text, length=None, lights=None, condition_note=None
) -> str:
    """
    Returns stringified JSON for services_unit.description:
    {"length":"","lights":"","condition_note":<str or JSON null>}
    None for length/lights/condition_note means leave the previous value when
    merging from API; condition_note is normalized (faulty \"null\" values -> JSON null).
    """
    cur = None
    if existing_text:
        try:
            parsed = json.loads(existing_text)
            if _is_ski_trail_description_json(parsed):
                cur = parsed
        except (json.JSONDecodeError, TypeError):
            pass
    if cur is None:
        cur = {"length": "", "lights": "", "condition_note": ""}
    if length is not None:
        cur["length"] = _ski_json_str(length)
    if lights is not None:
        cur["lights"] = _ski_json_str(lights)
    if condition_note is not None:
        cur["condition_note"] = condition_note
    cn_out = (
        sanitize_maintenance_condition_note(condition_note)
        if condition_note is not None
        else sanitize_maintenance_condition_note(cur.get("condition_note"))
    )
    return _services_unit_description_json_string(
        {
            "length": _ski_json_str(cur.get("length", "")),
            "lights": _ski_json_str(cur.get("lights", "")),
            "condition_note": cn_out,
        }
    )


def merge_ice_track_unit_description(
    existing_text, condition_note=None, description=None
) -> str:
    """
    Returns stringified JSON for services_unit.description:
    {"condition_note":<str or JSON null>,"description":"<html from API>"}
    None means leave previous value when existing JSON is ice-shaped.
    Non-JSON existing text is treated as legacy HTML and wrapped in description.
    condition_note is normalized like merge_ski_trail_unit_description.
    """
    cur = None
    if existing_text is not None and str(existing_text).strip():
        try:
            parsed = json.loads(existing_text)
            if _is_ice_track_description_json(parsed):
                cur = parsed
            else:
                # Other JSON shape or unknown structure — preserve raw text in description
                cur = {"condition_note": "", "description": str(existing_text)}
        except (json.JSONDecodeError, TypeError):
            cur = {"condition_note": "", "description": str(existing_text)}
    if cur is None:
        cur = {"condition_note": "", "description": ""}
    if condition_note is not None:
        cur["condition_note"] = condition_note
    if description is not None:
        cur["description"] = str(description)
    cn_out = (
        sanitize_maintenance_condition_note(condition_note)
        if condition_note is not None
        else sanitize_maintenance_condition_note(cur.get("condition_note"))
    )
    return _services_unit_description_json_string(
        {
            "condition_note": cn_out,
            "description": (
                ""
                if cur.get("description") is None
                else str(cur.get("description", ""))
            ),
        }
    )


def maintenance_import_property_value(properties, key):
    """
    Value for merging into description JSON: None if key absent (do not overwrite),
    otherwise string (empty string if API sent null).
    """
    if key not in properties:
        return None
    v = properties[key]
    if v is None:
        return ""
    return str(v)


def get_unit_maintenance_description_source(unit):
    """
    Current description text for merge_* helpers.
    With django-modeltranslation, the same JSON should live in description_fi/sv/en;
    read the first non-empty language column.
    """
    for lang_code, _ in settings.LANGUAGES:
        fname = f"description_{lang_code}"
        if hasattr(unit, fname):
            val = getattr(unit, fname, None)
            if val is not None and str(val).strip():
                return str(val)
    val = getattr(unit, "description", None)
    if val is not None and str(val).strip():
        return str(val)
    return None


def apply_maintenance_unit_description_json(unit, json_string: str) -> None:
    """
    Persist stringified JSON on Unit.description for all configured languages.
    Saving only ``description`` / partial update_fields leaves description_sv/en
    stale when modeltranslation is enabled.
    """
    unit.last_modified_time = timezone.now()
    update_fields = ["last_modified_time"]
    for lang_code, _ in settings.LANGUAGES:
        fname = f"description_{lang_code}"
        if hasattr(unit, fname):
            setattr(unit, fname, json_string)
            update_fields.append(fname)
    if len(update_fields) == 1:
        unit.description = json_string
        update_fields.append("description")
    unit.save(update_fields=update_fields)


def get_or_create_sports_facility_unit(
    geometry_id,
    name,
    description=None,
    address=None,
    zip_code=None,
    geometry=None,
    update_translation_names=True,
):
    """
    Get or create a Unit record for a sports facility (ski trail or ice track).

    Uses geometry_id with an offset to generate a unique Unit ID.
    Sports facilities use Unit IDs starting from 100000 to avoid conflicts.

    Args:
        geometry_id: The geometry_id from UnitMaintenanceGeometry (used as base for Unit ID)
        name: Name of the facility (optionally finnish|swedish|english)
        description: Deprecated, ignored; use merge_*_unit_description on the unit.
        address: Optional street address
        zip_code: Optional postal code
        geometry: Optional geometry object (will be transformed to PROJECTION_SRID)
        update_translation_names: If False (ski maintenance import), do not change
            names on an existing unit; new units get a single bootstrap name (first
            segment before ``|``). Geometry imports should pass True to apply piped names.

    Returns:
        Unit instance
    """

    # Use geometry_id + offset to generate unique Unit ID
    # Offset ensures we don't conflict with regular Unit IDs
    unit_id = SPORTS_FACILITY_UNIT_ID_OFFSET + geometry_id

    try:
        unit = Unit.objects.get(id=unit_id)
        unit_created = False
    except Unit.DoesNotExist:
        if not _nonempty_str(name):
            return None
        unit = Unit(id=unit_id)
        unit_created = True

    # Names: geometry / ice imports use piped translations; ski maintenance must not
    # overwrite existing name_fi/sv/en (see update_translation_names).
    if unit_created:
        if update_translation_names:
            name_fi, name_sv, name_en = parse_trilingual_name(name)
            if not name_fi:
                fallback = str(name).strip()
                name_fi = name_sv = name_en = fallback
            apply_sport_facility_trilingual_names(unit, name_fi, name_sv, name_en)
        else:
            bootstrap = _bootstrap_sports_facility_name_without_translations(name)
            if bootstrap:
                apply_sport_facility_trilingual_names(
                    unit, bootstrap, bootstrap, bootstrap
                )
    elif update_translation_names and _nonempty_str(name):
        name_fi, name_sv, name_en = parse_trilingual_name(name)
        if not name_fi:
            fallback = str(name).strip()
            name_fi = name_sv = name_en = fallback
        apply_sport_facility_trilingual_names(unit, name_fi, name_sv, name_en)
    if address:
        unit.street_address = address
    if zip_code:
        unit.address_zip = zip_code

    # Set geometry if provided (transform from DEFAULT_SRID to PROJECTION_SRID)
    if geometry:
        projection_srid = get_default_srid()

        # Clone and transform geometry
        geom = geometry.clone()
        if geom.srid != projection_srid:
            geom.transform(projection_srid)

        # For Point geometries, set location; for LineString, set geometry
        if isinstance(geometry, Point):
            unit.location = geom
        else:
            unit.geometry = geom

    unit.last_modified_time = timezone.now()
    unit.save()

    label = unit.name or f"id {unit_id}"
    if unit_created:
        logger.info(
            f"Created Unit {unit_id} for sports facility '{label}' (geometry_id: {geometry_id})"
        )
    else:
        logger.debug(
            f"Updated Unit {unit_id} for sports facility '{label}' (geometry_id: {geometry_id})"
        )

    return unit
