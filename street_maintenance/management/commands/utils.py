import logging
import zoneinfo
from datetime import datetime, timedelta

import numpy as np
import requests
from django import db
from django.conf import settings
from django.contrib.gis.geos import LineString
from munigeo.models import AdministrativeDivision, AdministrativeDivisionGeometry

from street_maintenance.models import (
    DEFAULT_SRID,
    GeometryHistory,
    MaintenanceUnit,
    MaintenanceWork,
)

from .constants import (
    AUTORI,
    AUTORI_CONTRACTS_URL,
    AUTORI_DATE_TIME_FORMAT,
    AUTORI_EVENTS_URL,
    AUTORI_ROUTES_URL,
    AUTORI_TOKEN_URL,
    AUTORI_VEHICLES_URL,
    INFRAROAD,
    INFRAROAD_UNITS_URL,
    KUNTEC,
    KUNTEC_UNITS_URL,
)

logger = logging.getLogger("street_maintenance")
# In seconds
MAX_WORK_LENGTH = 180


@db.transaction.atomic
def precalculate_geometry_history(provider):
    """
    Function that populates the GeometryHistory model for a provider.
    LineString geometrys in MaintenanceWorks will be added as they are.
    Point data is generated into LineStrings. This is done by iterating the
    point data for every MaintenanceUnit for the given provider.
    The LineStrings are then generated by comparing the timestamps delta time
    with the MAX_WORK_LENGTH, if withing the point is added to the LineString.
    """
    GeometryHistory.objects.filter(provider=provider).delete()
    objects = []
    queryset = MaintenanceWork.objects.filter(
        maintenance_unit__provider=provider
    ).order_by("timestamp")
    elements_to_remove = []
    # Add works that are linestrings,
    for elem in queryset:
        if isinstance(elem.geometry, LineString):
            objects.append(
                GeometryHistory(
                    provider=provider,
                    coordinates=elem.geometry.coords,
                    timestamp=elem.timestamp,
                    events=elem.events,
                    geometry=elem.geometry,
                )
            )
            elements_to_remove.append(elem.id)

    # Remove the linestring elements, as they are not needed when generaing
    # linestrings from point data
    queryset = queryset.exclude(id__in=elements_to_remove)

    unit_ids = (
        queryset.order_by("maintenance_unit_id")
        .values_list("maintenance_unit_id", flat=True)
        .distinct("maintenance_unit_id")
    )
    discarded_points = 0
    for unit_id in unit_ids:
        # Temporary store points to list for LineString creation
        points = []
        qs = queryset.filter(maintenance_unit_id=unit_id).order_by("timestamp")
        prev_timestamp = None
        for elem in qs:

            if prev_timestamp:
                delta_time = elem.timestamp - prev_timestamp
                # If delta_time is bigger than the MAX_WORK_LENGTH, then we can assume
                # that the work should not be in the same linestring/point .
                if delta_time.seconds > MAX_WORK_LENGTH:
                    if len(points) > 1:
                        geometry = LineString(points, srid=DEFAULT_SRID)
                        objects.append(
                            GeometryHistory(
                                provider=provider,
                                coordinates=geometry.coords,
                                timestamp=elem.timestamp,
                                events=elem.events,
                                geometry=geometry,
                            )
                        )
                    else:
                        discarded_points += 1

                    points = []
            points.append(elem.geometry)
            prev_timestamp = elem.timestamp

        if len(points) > 1:
            geometry = LineString(points, srid=DEFAULT_SRID)
            objects.append(
                GeometryHistory(
                    provider=provider,
                    coordinates=geometry.coords,
                    timestamp=elem.timestamp,
                    events=elem.events,
                    geometry=geometry,
                )
            )
        else:
            discarded_points += 1

    GeometryHistory.objects.bulk_create(objects)
    logger.info(f"Discarded {discarded_points} points")
    logger.info(f"Created {len(objects)} HistoryGeometry rows for provider: {provider}")


def get_turku_boundary():
    division_turku = AdministrativeDivision.objects.get(name="Turku")
    turku_boundary = AdministrativeDivisionGeometry.objects.get(
        division=division_turku
    ).boundary
    turku_boundary.transform(DEFAULT_SRID)
    return turku_boundary


def create_infraroad_maintenance_units():
    response = requests.get(INFRAROAD_UNITS_URL)
    assert (
        response.status_code == 200
    ), "Fetching Maintenance Unit {} status code: {}".format(
        INFRAROAD_UNITS_URL, response.status_code
    )
    for unit in response.json():
        # The names of the unit is derived from the events.
        names = [n for n in unit["last_location"]["events"]]
        MaintenanceUnit.objects.create(
            unit_id=unit["id"], names=names, provider=INFRAROAD
        )
    logger.info(
        f"Imported {MaintenanceUnit.objects.filter(provider=INFRAROAD).count()}"
        + " Infraroad mainetance Units."
    )


def get_autori_contract(access_token):
    response = requests.get(
        AUTORI_CONTRACTS_URL, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert (
        response.status_code == 200
    ), "Fetcing Autori Contract {} failed, status code: {}".format(
        AUTORI_CONTRACTS_URL, response.status_code
    )
    return response.json()[0].get("id", None)


def get_autori_event_types(access_token):
    response = requests.get(
        AUTORI_EVENTS_URL, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert (
        response.status_code == 200
    ), " Fetching Autori event types {} failed, status code: {}".format(
        AUTORI_EVENTS_URL, response.status_code
    )
    return response.json()


def create_dict_from_autori_events(list_of_events):
    events = {}
    for event in list_of_events:
        events[event["id"]] = event["operationName"]
    return events


def create_kuntec_maintenance_units():
    response = requests.get(KUNTEC_UNITS_URL)
    assert (
        response.status_code == 200
    ), "Fetching Maintenance Unit {} status code: {}".format(
        KUNTEC_UNITS_URL, response.status_code
    )
    no_io_din = 0
    for unit in response.json()["data"]["units"]:
        names = []
        if "io_din" in unit:
            on_states = 0
            # example io_din field: {'no': 3, 'label': 'Muu työ', 'state': 0}
            for io in unit["io_din"]:
                if io["state"] == 1:
                    on_states += 1
                    names.append(io["label"])
        # If names, we have a unit with at least one io_din with State On.
        if len(names) > 0:
            unit_id = unit["unit_id"]
            MaintenanceUnit.objects.create(
                unit_id=unit_id, names=names, provider=KUNTEC
            )
        else:
            no_io_din += 1
    logger.info(
        f"Discarding {no_io_din} Kuntec units that do not have a io_din with Status 'On'(1)."
    )
    logger.info(
        f"Imported {MaintenanceUnit.objects.filter(provider=KUNTEC).count()}"
        + " Kuntec mainetance Units."
    )


def create_autori_maintenance_units(access_token):
    response = requests.get(
        AUTORI_VEHICLES_URL, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert (
        response.status_code == 200
    ), " Fetching Autori vehicles {} failed, status code: {}".format(
        AUTORI_VEHICLES_URL, response.status_code
    )
    for unit in response.json():
        names = [unit["vehicleTypeName"]]
        MaintenanceUnit.objects.create(unit_id=unit["id"], names=names, provider=AUTORI)
    logger.info(
        f"Imported {MaintenanceUnit.objects.filter(provider=AUTORI).count()}"
        + " Autori(YIT) mainetance Units."
    )


def get_autori_routes(access_token, contract, history_size):
    now = datetime.now()
    end = now.replace(tzinfo=zoneinfo.ZoneInfo("Europe/Helsinki")).strftime(
        AUTORI_DATE_TIME_FORMAT
    )
    start = (
        (now - timedelta(days=history_size))
        .replace(tzinfo=zoneinfo.ZoneInfo("Europe/Helsinki"))
        .strftime(AUTORI_DATE_TIME_FORMAT)
    )
    params = {
        "contract": contract,
        "start": start,
        "end": end,
    }
    response = requests.get(
        AUTORI_ROUTES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
    )
    assert (
        response.status_code == 200
    ), "Fetching Autori routes {}, failed, status code: {}".format(
        AUTORI_ROUTES_URL, response.status_code
    )
    return response.json()


def get_autori_access_token():
    assert settings.AUTORI_SCOPE, "AUTOR_SCOPE not defined in environment."
    assert settings.AUTORI_CLIENT_ID, "AUTOR_CLIENT_ID not defined in environment."
    assert (
        settings.AUTORI_CLIENT_SECRET
    ), "AUTOR_CLIENT_SECRET not defined in environment."
    data = {
        "grant_type": "client_credentials",
        "scope": settings.AUTORI_SCOPE,
        "client_id": settings.AUTORI_CLIENT_ID,
        "client_secret": settings.AUTORI_CLIENT_SECRET,
    }
    response = requests.post(AUTORI_TOKEN_URL, data=data)
    assert (
        response.status_code == 200
    ), "Fetchin oauth2 token from Autori {} failed, status code: {}".format(
        AUTORI_TOKEN_URL, response.status_code
    )
    access_token = response.json().get("access_token", None)
    return access_token


def is_nested_coordinates(coordinates):
    return bool(np.array(coordinates).ndim > 1)
