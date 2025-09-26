import logging

from django.conf import settings
from django.contrib.gis.geos import Point
from munigeo.models import Municipality

from .utils import fetch_json, MobileUnitDataBase, fetch_json_with_headers, get_municipality_name, locates_in_turku, \
    get_closest_address_full_name, get_postal_code

"""
    Föli park_and_ride objects have moved from data.foli.fi to use Fintraffic Parking data in 2025.
"""

# URL = "https://data.foli.fi/geojson/poi"
URL = "https://parking.fintraffic.fi/api/v1/hubs"
FACILITIES_URL = "https://parking.fintraffic.fi/api/v1/facilities"
HEADERS = {"Accept": "application/geo+json;charset=UTF-8"}
FOLI_PARKANDRIDE_CARS_STOP_CONTENT_TYPE_NAME = "FoliParkAndRideCarsStop"
FOLI_PARKANDRIDE_BIKES_STOP_CONTENT_TYPE_NAME = "FoliParkAndRideBikesStop"
PARKANDRIDE = "PARK_AND_RIDE"
# PARKANDRIDE_CARS = "PARKANDRIDE_CARS"
# PARKANDRIDE_BIKES = "PARKANDRIDE_BIKES"
SOURCE_DATA_SRID = 4326
logger = logging.getLogger("mobility_data")


class ParkAndRideStop(MobileUnitDataBase):
    def __init__(self, feature):
        super().__init__()
        properties = feature["properties"]
        self.name = {
            "fi": properties["name"]["fi"],
            "sv": properties["name"]["sv"],
            "en": properties["name"]["en"],
        }
        # self.description["fi"] = properties["text"]
        geometry = feature["geometry"]
        self.geometry = Point(
            geometry["coordinates"][0],
            geometry["coordinates"][1],
            srid=SOURCE_DATA_SRID,
        )
        self.geometry.transform(settings.DEFAULT_SRID)
        try:
            self.municipality = Municipality.objects.get(name=get_municipality_name(self.geometry))
        except Municipality.DoesNotExist:
            self.municipality = None
        try:
            self.address = get_closest_address_full_name(self.geometry)
            self.address_zip = get_postal_code(self.geometry)
        except Exception as e:
            logger.warning("Unable to get address or zip code for a stop.")
            logger.warning(e)


def get_parkandride_car_stop_objects():
    turku_hubs = get_fintraffic_hubs()
    car_stops = []
    for feature in turku_hubs:
        if check_usage(feature["properties"]["facilityIds"], "CAR") is not None:
            car_stops.append(ParkAndRideStop(feature))
    logging.debug('Found {} car stops'.format(len(car_stops)))
    return car_stops


def get_parkandride_bike_stop_objects():
    turku_hubs = get_fintraffic_hubs()
    bike_stops = []
    for feature in turku_hubs:
        if check_usage(feature["properties"]["facilityIds"], "BICYCLE") is not None:
            bike_stops.append(ParkAndRideStop(feature))
    logging.debug('Found {} bike stops'.format(len(bike_stops)))
    return bike_stops


def get_fintraffic_hubs():
    """
    Fintraffic https://parking.fintraffic.fi/docs/index.html#hub-search hub search currently
    does not work with geometry search, so need to filter hubs on site.
    """
    json_data = fetch_json_with_headers(URL, HEADERS)
    turku_hubs = []
    for feature in json_data["features"]:
        try:
            coords = feature["geometry"]["coordinates"]
            lon, lat = coords[0], coords[1]
            wkt = f'POINT({lon} {lat})'
            if locates_in_turku(wkt, SOURCE_DATA_SRID):
                turku_hubs.append(feature)
        except Exception as e:
            logger.warning(e)
    return turku_hubs


def check_usage(facility_ids, capacity_type):
    """ Get usage by fetching related facilities """
    try:
        if facility_ids is not None and len(facility_ids) > 0:
            json_data = fetch_json(FACILITIES_URL + "?" + "&".join(f"ids={i}" for i in facility_ids))
            return find_parking_object(json_data["results"], capacity_type)
        else:
            return None
    except Exception as e:
        logger.warning("Exception: {}".format(e))
        return None


def find_parking_object(data, capacity_type):
    """
    Finds the first object in data with usage='PARK_AND_RIDE' and given capacity type.
    Returns None if data is None or no match is found.
    """
    if not data:
        return None
    return next(
        (obj for obj in data if "PARK_AND_RIDE" in obj.get("usages", []) and obj.get("type") == capacity_type),
        None
    )
