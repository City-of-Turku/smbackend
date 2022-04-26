import logging

from django import db
from django.conf import settings
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import Point
from munigeo.models import AdministrativeDivision, AdministrativeDivisionGeometry

from mobility_data.models import ContentType, MobileUnit

from .utils import (
    delete_mobile_units,
    get_closest_address_full_name,
    get_municipality_name,
    get_or_create_content_type,
    set_translated_field,
)

FI_KEY = "fi"
SV_KEY = "sv"
EN_KEY = "en"
NAME_PREFIX = {
    FI_KEY: "Pyöräpysäköinti",
    SV_KEY: "Cykelparkering",
    EN_KEY: "Bicycle parking",
}
BICYCLE_STANDS_URL = "{}{}".format(
    settings.TURKU_WFS_URL,
    "?service=WFS&request=GetFeature&typeName=GIS:Polkupyoraparkki&outputFormat=GML3",
)
SOURCE_DATA_SRID = 3877
logger = logging.getLogger("mobility_data")
division_turku = AdministrativeDivision.objects.get(name="Turku")
turku_boundary = AdministrativeDivisionGeometry.objects.get(
    division=division_turku
).boundary


class BicyleStand:

    HULL_LOCKABLE_STR = "runkolukitusmahdollisuus"
    COVERED_IN_STR = "katettu"

    geometry = None
    model = None
    name = None
    number_of_stands = None
    number_of_places = None  # The total number of places for bicycles.
    hull_lockable = None
    covered = None
    city = None
    street_address = None
    maintained_by_turku = None

    @classmethod
    def locates_in_turku(cls, feature):
        """
        Returns True if the geometry of the feature is inside the boundaries
        of Turku.
        """
        point = Point(feature.geom.x, feature.geom.y, srid=SOURCE_DATA_SRID)
        point.transform(settings.DEFAULT_SRID)
        return turku_boundary.contains(point)

    def __init__(self, feature):
        self.name = {}
        self.prefix_name = {}
        self.street_address = {}
        object_id = feature["id"].as_string()
        # If ObjectId is set to "0", the bicycle stand is not maintained by Turku
        if object_id == "0":
            self.maintained_by_turku = False
        else:
            self.maintained_by_turku = True

        self.geometry = Point(feature.geom.x, feature.geom.y, srid=SOURCE_DATA_SRID)
        self.geometry.transform(settings.DEFAULT_SRID)

        model_elem = feature["Malli"]
        if model_elem is not None:
            self.model = model_elem.as_string()
        katu_name_elem = feature["Katuosa_nimi"].as_string()
        viher_name_elem = feature["Viherosa_nimi"].as_string()
        if katu_name_elem:
            name = katu_name_elem
        elif viher_name_elem:
            name = viher_name_elem
        else:
            name = None
        num_stands_elem = feature["Lukumaara"]
        if num_stands_elem is not None:
            num = num_stands_elem.as_int()
            # for bicycle stands that are Not maintained by Turku
            # the number of stands is set to 0 in the input data
            # but in reality there is no data so None is set.
            if num == 0 and not self.maintained_by_turku:
                self.number_of_stands = None
            else:
                self.number_of_stands = num

        num_places_elem = feature["Pyorapaikkojen_lukumaara"].as_string()

        if num_places_elem:
            # Parse the numbers inside the string and finally sum them.
            # The input can contain string such as "8 runkolukittavaa ja 10 ei runkolukittavaa paikkaa"
            numbers = [int(s) for s in num_places_elem.split() if s.isdigit()]
            self.number_of_places = sum(numbers)

        quality_elem = feature["Pyorapaikkojen_laatutaso"].as_string()

        if quality_elem:
            quality_text = quality_elem.lower()
            if self.HULL_LOCKABLE_STR in quality_text:
                self.hull_lockable = True
            else:
                self.hull_lockable = False

            if self.COVERED_IN_STR in quality_text:
                self.covered = True
            else:
                self.covered = False
        self.city = get_municipality_name(self.geometry)
        full_names = get_closest_address_full_name(self.geometry)
        # Finnish name not found, assing closest address full names to all languages.
        if not name:
            self.name = full_names
        # Finnish name in source data, assign closest address full names to "sv" and "en" names.
        else:
            self.name[FI_KEY] = name
            self.name[SV_KEY] = full_names[SV_KEY]
            self.name[EN_KEY] = full_names[EN_KEY]
        self.prefix_name = {k: f"{NAME_PREFIX[k]} {v}" for k, v in self.name.items()}


def get_bicycle_stand_objects(ds=None):
    """
    Returns a list containg instances of BicycleStand class.
    """
    if not ds:
        ds = DataSource(BICYCLE_STANDS_URL)
    layer = ds[0]
    bicycle_stands = []
    for feature in layer:
        if BicyleStand.locates_in_turku(feature):
            bicycle_stands.append(BicyleStand(feature))
    logger.info(f"Retrieved {len(bicycle_stands)} bicycle stands.")
    return bicycle_stands


@db.transaction.atomic
def delete_bicycle_stands():
    delete_mobile_units(ContentType.BICYCLE_STAND)


@db.transaction.atomic
def create_bicycle_stand_content_type():
    description = "Bicycle stands in The Turku Region."
    name = "Bicycle Stands"
    content_type, _ = get_or_create_content_type(
        ContentType.BICYCLE_STAND, name, description
    )
    return content_type


@db.transaction.atomic
def save_to_database(objects, delete_tables=True):
    if delete_tables:
        delete_bicycle_stands()

    content_type = create_bicycle_stand_content_type()
    for object in objects:
        mobile_unit = MobileUnit.objects.create(
            content_type=content_type,
        )
        extra = {}
        extra["model"] = object.model
        extra["maintained_by_turku"] = object.maintained_by_turku
        extra["number_of_stands"] = object.number_of_stands
        extra["number_of_places"] = object.number_of_places
        extra["hull_lockable"] = object.hull_lockable
        extra["covered"] = object.covered
        mobile_unit.extra = extra
        mobile_unit.geometry = object.geometry
        set_translated_field(mobile_unit, "name", object.name)
        mobile_unit.save()
