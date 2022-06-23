import logging

from django import db
from django.conf import settings
from django.contrib.gis.gdal import DataSource as GDALDataSource
from django.contrib.gis.geos import GEOSGeometry

from mobility_data.importers.utils import (
    delete_mobile_units,
    get_or_create_content_type,
    set_translated_field,
)
from mobility_data.models import ContentType, DataSource, MobileUnit

logger = logging.getLogger("bicycle_network")
SOURCE_DATA_SRID = 3877
GEOJSON_FILENAME = "Yhteiskayttoautojen_pysakointi_2022.geojson"

LANGUAGES = [language[0] for language in settings.LANGUAGES]


class CarShareParkingPlace:
    RESTRICTION_FIELD = "Rajoit_lis"
    EXCLUDE_FIELDS = ["id", "Osoite", RESTRICTION_FIELD]
    CAR_PARKING_NAME = {
        "fi": "Yhteiskäyttöautojen pysäköintipaikka",
        "sv": "Bilpoolbilars parkeringsplats",
        "en": "Parking place for car sharing cars",
    }

    def __init__(self, feature):
        self.name = {}
        self.extra = {}
        self.address = {}
        street_name = {}
        self.geometry = GEOSGeometry(feature.geom.wkt, srid=SOURCE_DATA_SRID)
        self.geometry.transform(settings.DEFAULT_SRID)

        for field in feature.fields:
            if field not in self.EXCLUDE_FIELDS:
                self.extra[field] = feature[field].as_string()

        address_fi, address_sv = [
            address.strip() for address in feature["Osoite"].as_string().split("/")
        ]
        restrictions = feature[self.RESTRICTION_FIELD].as_string().split("/")

        street_name["fi"] = address_fi.split(",")[0]
        street_name["sv"] = address_sv.split(",")[0]
        street_name["en"] = street_name["fi"]
        self.extra[self.RESTRICTION_FIELD] = {}
        for i, language in enumerate(LANGUAGES):
            self.name[
                language
            ] = f"{self.CAR_PARKING_NAME[language]}, {street_name[language]}"
            self.address[language] = street_name[language]
            self.extra[self.RESTRICTION_FIELD][language] = restrictions[i].strip()


def get_car_share_parking_place_objects(geojson_file=None):
    car_share_parking_places = []
    file_name = None
    if hasattr(settings, "PROJECT_ROOT"):
        root_dir = settings.PROJECT_ROOT
    else:
        root_dir = settings.BASE_DIR

    if not geojson_file:
        data_source_qs = DataSource.objects.filter(
            type_name=ContentType.SHARE_CAR_PARKING_PLACE
        )
        # If data source found, use the uploaded data file.
        if data_source_qs.exists():
            file_name = str(data_source_qs.first().data_file.file)
        else:
            file_name = f"{root_dir}/mobility_data/data/{GEOJSON_FILENAME}"
    else:
        # Use the test data file
        file_name = f"{root_dir}/mobility_data/tests/data/{geojson_file}"

    data_layer = GDALDataSource(file_name)[0]
    for feature in data_layer:
        car_share_parking_places.append(CarShareParkingPlace(feature))
    return car_share_parking_places


@db.transaction.atomic
def delete_car_share_parking_places():
    delete_mobile_units(ContentType.SHARE_CAR_PARKING_PLACE)


@db.transaction.atomic
def create_car_share_parking_place_content_type():
    description = "Car share parking places in the Turku region."
    name = "Car share parking place"
    content_type, _ = get_or_create_content_type(
        ContentType.SHARE_CAR_PARKING_PLACE, name, description
    )
    return content_type


@db.transaction.atomic
def save_to_database(objects, delete_tables=True):
    if delete_tables:
        delete_car_share_parking_places()
    content_type = create_car_share_parking_place_content_type()
    for object in objects:
        mobile_unit = MobileUnit.objects.create(
            content_type=content_type, extra=object.extra
        )
        set_translated_field(mobile_unit, "name", object.name)
        set_translated_field(mobile_unit, "address", object.address)
        mobile_unit.save()