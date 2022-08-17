import logging
from enum import Enum

from django import db
from django.conf import settings
from django.contrib.gis.gdal import DataSource as GDALDataSource
from django.contrib.gis.geos import GEOSGeometry
from munigeo.models import Municipality

from mobility_data.importers.utils import (
    delete_mobile_units,
    get_file_name_from_data_source,
    get_or_create_content_type,
    get_root_dir,
    set_translated_field,
)
from mobility_data.models import ContentType, MobileUnit

logger = logging.getLogger("mobility_data")

SOURCE_DATA_SRID = 3877

GEOJSON_FILENAME = "autopysäköinti_eihlö.geojson"
LANGUAGES = [language[0] for language in settings.LANGUAGES]


class FieldTypes(Enum):
    STRING = 1
    MULTILANG_STRING = 2
    INTEGER = 3
    FLOAT = 4


class NoStaffParking:
    extra_field_mappings = {
        "saavutettavuus": {
            "type": FieldTypes.MULTILANG_STRING,
        },
        "paikkoja_y": {"type": FieldTypes.INTEGER},
        "invapaikkoja": {"type": FieldTypes.INTEGER},
        "sahkolatauspaikkoja": {
            "type": FieldTypes.INTEGER,
        },
        "tolppapaikkoja": {"type": FieldTypes.INTEGER},
        "rajoitukset/maksullisuus": {"type": FieldTypes.STRING},
        "aikarajoitus": {"type": FieldTypes.STRING},
        "paivays": {"type": FieldTypes.STRING},
        "lastauspiste": {"type": FieldTypes.MULTILANG_STRING},
        "lisatietoja": {
            "type": FieldTypes.MULTILANG_STRING,
        },
        "rajoitustyyppi": {"type": FieldTypes.MULTILANG_STRING},
        "maksuvyohyke": {"type": FieldTypes.INTEGER},
        "max_aika_h": {"type": FieldTypes.FLOAT},
        "max_aika_m": {"type": FieldTypes.FLOAT},
        "rajoitus_maksul_arki": {
            "type": FieldTypes.STRING,
        },
        "rajoitus_maksul_l": {
            "type": FieldTypes.STRING,
        },
        "rajoitus_maksul_s": {
            "type": FieldTypes.STRING,
        },
        "rajoitettu_ark": {"type": FieldTypes.STRING},
        "rajoitettu_l": {"type": FieldTypes.STRING},
        "rajoitettu_s": {"type": FieldTypes.STRING},
        "voimassaolokausi": {"type": FieldTypes.STRING},
        "rajoit_lisat": {
            "type": FieldTypes.MULTILANG_STRING,
        },
        "varattu_tiet_ajon": {"type": FieldTypes.STRING},
        "erityisluv": {"type": FieldTypes.STRING},
        "vuoropys": {"type": FieldTypes.STRING},
        "talvikunno": {"type": FieldTypes.STRING},
    }

    def __init__(self, feature):
        self.address = {}
        self.name = {}
        # Addresses are in format e.g.: Kupittaankuja 1, 20520 Turku / Kuppisgränden 1 20520 Åbo
        # Create a list, where every language is a item where trailing spaces, comma, postalcode
        # and municipality are removed. e.g. ["Kupittaankuja 1", "Kuppisgränden 1"]
        addresses = [
            " ".join(a.strip().split(" ")[:-2]).rstrip(",")
            for a in feature["osoite"].as_string().split("/")
        ]
        names = [n.strip() for n in feature["kohde"].as_string().split("/")]
        for i, lang in enumerate(LANGUAGES):
            if i < len(addresses):
                self.address[lang] = addresses[i]
            else:
                # assign Fi if translation not found
                self.address[lang] = addresses[0]
            if i < len(names):
                self.name[lang] = names[i]
            else:
                self.name[lang] = names[0]
        self.address_zip, municipality = (
            feature["osoite"].as_string().split("/")[0].strip().split(" ")[-2:]
        )
        try:
            municipality = Municipality.objects.get(name=municipality)
            self.municipality = municipality
        except Municipality.DoesNotExist:
            self.municipality = None

        self.geometry = GEOSGeometry(feature.geom.wkt, srid=SOURCE_DATA_SRID)
        self.geometry.transform(settings.DEFAULT_SRID)
        self.extra = {}
        for field in feature.fields:
            if field in self.extra_field_mappings:
                # It is possible to define a name in the extra_field_mappings
                # and this name will be used in the extra field and serialized data.
                if hasattr(self.extra_field_mappings[field], "name"):
                    field_name = self.extra_field_mappings[field]["name"]
                else:
                    field_name = field
                match self.extra_field_mappings[field]["type"]:
                    case FieldTypes.STRING:
                        self.extra[field_name] = feature[field].as_string()
                    case FieldTypes.MULTILANG_STRING:
                        self.extra[field_name] = {}
                        field_content = feature[field].as_string()
                        if field_content:
                            strings = field_content.split("/")
                            for i, lang in enumerate(LANGUAGES):
                                if i < len(strings):
                                    self.extra[field_name][lang] = strings[i].strip()
                    case FieldTypes.INTEGER:
                        self.extra[field_name] = feature[field].as_int()
                    case FieldTypes.FLOAT:
                        self.extra[field_name] = feature[field].as_double()


def get_no_staff_parking_objects(geojson_file=None):
    no_staff_parkings = []
    file_name = None

    if not geojson_file:
        file_name = get_file_name_from_data_source(ContentType.NO_STAFF_PARKING)
        if not file_name:
            file_name = f"{get_root_dir()}/mobility_data/data/{GEOJSON_FILENAME}"
    else:
        # Use the test data file
        file_name = f"{get_root_dir()}/mobility_data/tests/data/{geojson_file}"

    data_layer = GDALDataSource(file_name)[0]
    for feature in data_layer:
        no_staff_parkings.append(NoStaffParking(feature))
    return no_staff_parkings


@db.transaction.atomic
def delete_no_staff_parkings():
    delete_mobile_units(ContentType.NO_STAFF_PARKING)


@db.transaction.atomic
def get_and_create_no_staff_parking_content_type():
    description = "No staff parkings in the Turku region."
    name = "No staff parking"
    content_type, _ = get_or_create_content_type(
        ContentType.NO_STAFF_PARKING, name, description
    )
    return content_type


@db.transaction.atomic
def save_to_database(objects, delete_tables=True):
    if delete_tables:
        delete_no_staff_parkings()

    content_type = get_and_create_no_staff_parking_content_type()
    for object in objects:
        mobile_unit = MobileUnit.objects.create(
            content_type=content_type, extra=object.extra, geometry=object.geometry
        )
        set_translated_field(mobile_unit, "name", object.name)
        set_translated_field(mobile_unit, "address", object.address)
        mobile_unit.address_zip = object.address_zip
        mobile_unit.municipality = object.municipality
        mobile_unit.save()
