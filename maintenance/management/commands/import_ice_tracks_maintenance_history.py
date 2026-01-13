import logging
from datetime import datetime

import pytz
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from maintenance.models import DEFAULT_SRID, UnitMaintenance, UnitMaintenanceGeometry
from services.models import Unit

from .constants import ICE_TRACKS_DATE_FIELD_FORMAT
from .utils import get_json_data, get_unit_maintenance_instance

logger = logging.getLogger(__name__)

TIMEZONE = pytz.timezone("Europe/Helsinki")


def save_maintenance_history(json_data):
    objs_to_delete = list(
        UnitMaintenance.objects.filter(target=UnitMaintenance.ICE_TRACK).values_list(
            "id", flat=True
        )
    )
    num_created = 0
    num_updated = 0
    features = json_data.get("features", None)
    if not features:
        logger.error("No features found in JSON response.")
        return

    for feature in features:
        properties = feature.get("properties", None)
        if not properties:
            logger.warning(
                f"'properties' not found for feature: {feature}, skipping..."
            )
            continue

        external_id = properties.get("external_id", None)
        if external_id:
            try:
                unit = Unit.objects.get(id=external_id)
            except Unit.DoesNotExist:
                logger.error(f"Unit {external_id} not found, skipping...")
                continue

        filter = {
            "unit": unit,
            "target": UnitMaintenance.ICE_TRACK,
        }

        unit_maintenance, is_created = get_unit_maintenance_instance(filter)
        maintained_at = properties.get("conditioned_at", None)
        if maintained_at:
            try:
                maintained_at = TIMEZONE.localize(
                    datetime.strptime(maintained_at, ICE_TRACKS_DATE_FIELD_FORMAT)
                )
            except Exception as exp:
                logger.warning(
                    f"Feature {feature}, invalid 'maintained_at' field, reason {exp}."
                )
        condition_val = properties.get("conditioned", None)

        if condition_val is None:
            condition = UnitMaintenance.UNDEFINED
        elif condition_val is True:
            condition = UnitMaintenance.USABLE
        else:
            condition = UnitMaintenance.UNUSABLE

        unit_maintenance.condition = condition
        unit_maintenance.maintained_at = maintained_at
        unit_maintenance.last_imported_time = TIMEZONE.localize(
            datetime.now().replace(microsecond=0)
        )
        try:
            unit_maintenance.save()
        except Exception as exp:
            logger.error(f"unable to save ice track maintenance history, reason: {exp}")
            continue

        geometry = feature.get("geometry", None)
        if geometry:
            coordinates = geometry.get("coordinates", None)
            if coordinates and len(coordinates) == 2:
                lon = coordinates[0]
                lat = coordinates[1]
                point = Point(lon, lat, srid=DEFAULT_SRID)
                unit_maintenance_geometry, _ = (
                    UnitMaintenanceGeometry.objects.get_or_create(
                        unit_maintenance=unit_maintenance
                    )
                )
                unit_maintenance_geometry.geometry = point
                unit_maintenance_geometry.save()
            else:
                logger.error(
                    f"Missing or invalid field 'coordinates' for feature {feature}, skipping geometry..."
                )
        else:
            logger.error(
                f"Missing 'geometry' field for featrure {feature}, skipping geometry..."
            )

        if is_created:
            num_created += 1
        else:
            num_updated += 1
        if unit_maintenance.id in objs_to_delete:
            objs_to_delete.remove(unit_maintenance.id)

    UnitMaintenance.objects.filter(id__in=objs_to_delete).delete()
    logger.info(
        f"Created {num_created}, updated {num_updated}, deleted {len(objs_to_delete)} ice track maintenance histories"
    )


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete ice tracks maintenance history.",
        )

    def handle(self, *args, **options):
        if options.get("delete", False):
            UnitMaintenance.objects.filter(target=UnitMaintenance.ICE_TRACK).delete()

        json_data = get_json_data(settings.ICE_TRACKS_MAINTENANCE_HISTORY_URL)
        save_maintenance_history(json_data)
