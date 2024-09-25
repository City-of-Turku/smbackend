import logging

from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos.error import GEOSException
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from maintenance.models import UnitMaintenance, UnitMaintenanceGeometry

from .utils import get_data_layer

logger = logging.getLogger(__name__)

URL = (
    "https://api.paikannuspalvelu.fi/v1/public/track/"
    "?data_key=cftqHZ8mjwf3uYpXz9HAUH3nXY6IjrvrvYmRMnbZ&author=?&format=geojson"
)


def save_trails(layer):
    num_saved = 0
    for feature in layer:
        try:
            geometry = UnitMaintenanceGeometry()
            try:
                geometry.geometry = GEOSGeometry(
                    feature.geom.wkt, srid=feature.geom.srid
                )
            except GEOSException:
                logger.error(f"Invalid geometry {feature.geom.wkt}, skipping...")
                continue

            geometry.geometry_id = feature["construction_point_id"].as_int()
            try:
                geometry.save()
                num_saved += 1
            except IntegrityError:
                logger.error(f"geometry id {geometry.geometry_id} exists, skipping...")
        except Exception as exp:
            logger.error(f"Could not save ski trail {feature}, reason {exp}")
    return num_saved


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete all ski trails that have a unit maintenance relationship, before importing.",
        )

    def handle(self, *args, **options):
        if options.get("delete", False):
            UnitMaintenanceGeometry.objects.filter(
                unit_maintenance__target=UnitMaintenance.SKI_TRAIL
            ).delete()
        layer = get_data_layer(URL)
        logger.info(f"Saved {save_trails(layer)} ski trails.")
