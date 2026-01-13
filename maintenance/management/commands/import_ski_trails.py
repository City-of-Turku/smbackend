import logging

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos.error import GEOSException
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from maintenance.models import UnitMaintenance, UnitMaintenanceGeometry

from .utils import get_data_layer

logger = logging.getLogger(__name__)


def save_trails(layer):
    num_created = 0
    num_updated = 0
    for feature in layer:
        is_created = False
        is_updated = False
        try:
            geometry = None

            try:
                geometry = GEOSGeometry(feature.geom.wkt, srid=feature.geom.srid)
            except GEOSException:
                logger.error(f"Invalid geometry {feature.geom.wkt}, skipping...")
                continue

            geometry_id = feature["construction_point_id"].as_int()
            filter = {"geometry_id": geometry_id}
            queryset = UnitMaintenanceGeometry.objects.filter(**filter)

            if queryset.count() == 0:
                unit_maintenance_geometry = UnitMaintenanceGeometry(**filter)
                unit_maintenance_geometry.geometry = geometry
                is_created = True
            else:
                unit_maintenance_geometry = queryset.first()
                if not unit_maintenance_geometry.geometry.equals(geometry):
                    unit_maintenance_geometry.geometry = geometry
                    is_updated = True

            try:
                unit_maintenance_geometry.save()
            except IntegrityError:
                logger.error(f"geometry id {geometry.geometry_id} exists, skipping...")

        except Exception as exp:
            logger.error(f"Could not save ski trail {feature}, reason {exp}")
        num_created = num_created + 1 if is_created else num_created
        num_updated = num_updated + 1 if is_updated else num_updated
    return num_created, num_updated


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

        layer = get_data_layer(settings.SKI_TRAILS_URL)
        num_created, num_updated = save_trails(layer)
        logger.info(f"Created {num_created}, updated {num_updated} ski trails.")
