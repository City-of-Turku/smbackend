import logging
from datetime import datetime

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry
from django.core.management import BaseCommand
from django.utils import timezone

from exceptional_situations.models import (
    Situation,
    SituationAnnouncement,
    SituationLocation,
    SituationType,
)

logger = logging.getLogger(__name__)
# TODO, NOTE, change the URL when the source data is available in the production environment
URL = (
    "http://tkuikp/TeklaOGCWeb/WFS.ashx?service="
    "WFS&request=GetFeature&typeName=GIS:Kaivuluvat&srsName=EPSG:4326&outputFormat=GML3&maxFeatures=10000"
)
PERMISSION_START = "853"
LUPA_MYONNETTY = "Lupa myönnetty"
JATKOLUPA = "Jatkolupa"
NOW = timezone.now()
DATE_FORMAT = "%d.%m.%Y"
SITUATION_TYPE_NAME = "TURKU_ROAD_WORK"


def get_layer():
    ds = DataSource(URL)
    assert len(ds) == 1, "Invalid number of layers"
    return ds[0]


def get_filtered_features(layer) -> dict:
    """
    Include only if:
    * 'Lupanumero' start with 853
    * Käsittely vaihe is 'Lupa myönnetty' or 'Jatkolupa'
    * start date <= current date
    * end_date >= current_date or end date is None
    Saisiko tuosta eroteltua esimerkiksi ne, missä käsittelyvaihe on Myönnetty tai Jatkolupa ja
    päivämäärätieto ei ole tyhjä tai nykyinen päivä osuu annetulle aikavälille
    tai jos ei ole loppupäivää niin aloituspäivä on jo mennyt.
    Ja lupanumero alkaa 853.
    """
    features = {}
    for feature in layer:
        # If 'Lupanumero' does not start with PERMISSION_START, discard
        if not feature["Lupanumero"].as_string():
            continue
        if feature["Lupanumero"].as_string()[0:3] != PERMISSION_START:
            continue

        handling_phase = feature["Kasittelyvaihe"].as_string()
        if LUPA_MYONNETTY not in handling_phase and JATKOLUPA not in handling_phase:
            continue

        # If no timespan, discard
        validity_period = feature["Voimassaoloaika"].as_string()
        if not validity_period:
            continue
        end_time_str = None
        splitted = validity_period.split("-")
        # start_time_str, end_time_str = validity_period.split("-")
        start_time_str = splitted[0]
        if len(splitted) > 0:
            end_time_str = splitted[1]
        start_time = timezone.make_aware(
            datetime.strptime(start_time_str.strip(), DATE_FORMAT)
        )
        if NOW <= start_time:
            continue

        if end_time_str:
            end_time = timezone.make_aware(
                datetime.strptime(end_time_str.strip(), DATE_FORMAT)
            )

            if NOW >= end_time:
                continue
        else:
            end_time = None

        key = feature["Id"].as_string()
        # Convert GDAL geometry to GEOS geometry
        geometry = GEOSGeometry(feature.geom.wkt)
        # A situation can contain multiple features, features then have
        # the same properties, except for the geometry.
        if key not in features:
            features[key] = {
                "Id": feature["Id"].as_string(),
                "HakijaNimi": feature["HakijaNimi"].as_string(),
                "Lupatyyppi": feature["Lupatyyppi"].as_string(),
                "geometries": [geometry],
                "start_time": start_time,
                "end_time": end_time,
            }
        else:
            features[key]["geometries"].append(geometry)

    return features


def save_features_to_database(features):
    num_imported = 0
    for key in features.keys():
        feature = features[key]
        type_name = feature["Lupatyyppi"]
        situation_type, _ = SituationType.objects.get_or_create(type_name=type_name)

        filter = {
            "situation_id": feature["Id"],
            "situation_type": situation_type,
        }
        situation, created = Situation.objects.get_or_create(**filter)
        if not created:
            SituationAnnouncement.objects.filter(situation=situation).delete()
            situation.announcements.clear()

        announcement = SituationAnnouncement.objects.create(
            start_time=feature["start_time"], end_time=feature["end_time"]
        )
        announcement.additional_info = {"HakijaNimi": feature["HakijaNimi"]}
        announcement.save()

        for geometry in feature["geometries"]:
            SituationLocation.objects.create(
                announcement=announcement, geometry=geometry
            )

        situation.announcements.add(announcement)
        num_imported += 1

    logger.info(f"Imported/updated {num_imported} excavation permits.")


class Command(BaseCommand):
    def handle(self, *args, **options):
        layer = get_layer()
        features = get_filtered_features(layer)
        save_features_to_database(features)
