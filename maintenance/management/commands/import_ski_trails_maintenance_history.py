import logging
from datetime import datetime

import pytz
from django import db
from django.conf import settings
from django.core.management.base import BaseCommand

from maintenance.models import UnitMaintenance, UnitMaintenanceGeometry

from .constants import SKI_TRAILS_DATE_FIELD_FORMAT
from .utils import get_json_data, get_or_create_sports_facility_unit

logger = logging.getLogger(__name__)
TIMEZONE = pytz.timezone("Europe/Helsinki")


def save_maintenance_history(json_data):
    objs_to_delete = list(
        UnitMaintenance.objects.filter(target=UnitMaintenance.SKI_TRAIL).values_list(
            "id", flat=True
        )
    )
    num_created = 0
    num_updated = 0
    num_skipped_invalid_date = 0
    num_geometry_linked = 0
    num_geometry_not_found = 0

    features = json_data.get("features", None)
    if not features:
        logger.error("No features found in JSON response.")
        return

    logger.info(f"Processing {len(features)} features from maintenance history API")

    for feature in features:
        properties = feature.get("properties", None)
        if not properties:
            logger.warning(
                f"'properties' not found for feature: {feature}, skipping..."
            )
            continue
        name = properties.get("name", None)
        if not name:
            logger.warning(f"Feature missing 'name' property: {properties}")
            continue

        date_str = properties.get("date", None)
        if not date_str:
            logger.warning(f"Feature '{name}' missing 'date' field, skipping...")
            num_skipped_invalid_date += 1
            continue

        try:
            maintained_at = TIMEZONE.localize(
                datetime.strptime(date_str, SKI_TRAILS_DATE_FIELD_FORMAT)
            )
        except ValueError as exp:
            logger.error(
                f"Skipping feature '{name}', invalid 'date' field '{date_str}'"
                f"(expected format: {SKI_TRAILS_DATE_FIELD_FORMAT}), reason: {exp}."
            )
            num_skipped_invalid_date += 1
            continue

        geometry_id = properties.get("location_id", None)
        if not geometry_id:
            logger.warning(f"No location_id found in properties for feature '{name}', skipping...")
            continue

        # Get geometry by geometry_id (construction_point_id)
        # This is the reliable link between maintenance history and geometries
        try:
            geometry = UnitMaintenanceGeometry.objects.get(geometry_id=geometry_id)
        except UnitMaintenanceGeometry.DoesNotExist:
            logger.warning(
                f"Geometry with geometry_id={geometry_id} not found for '{name}', skipping..."
            )
            num_geometry_not_found += 1
            continue

        # Get or create Unit record for this ski trail
        unit = get_or_create_sports_facility_unit(
            geometry_id=geometry_id,
            name=name,
            description=properties.get("description", None),
            geometry=geometry.geometry,
        )

        # Determine which UnitMaintenance to use/update
        # Strategy: Link maintenance to geometry via geometry_id
        # Each geometry gets its own UnitMaintenance record (or reuses existing)
        if geometry.unit_maintenance:
            # Geometry already linked, update existing record
            unit_maintenance = geometry.unit_maintenance
            is_created = False
            # Update unit if it was None before
            if unit_maintenance.unit != unit:
                unit_maintenance.unit = unit
        else:
            # Create a new UnitMaintenance for this geometry
            unit_maintenance = UnitMaintenance(unit=unit, target=UnitMaintenance.SKI_TRAIL)
            is_created = True

        # Map conditioned field to condition
        # conditioned: 0 = UNUSABLE, 1 = USABLE, 2 = USABLE (fair condition), null/None = UNDEFINED
        conditioned = properties.get("conditioned", None)
        if conditioned is not None:
            if conditioned == 0:
                unit_maintenance.condition = UnitMaintenance.UNUSABLE
            elif conditioned in [1, 2]:
                unit_maintenance.condition = UnitMaintenance.USABLE
            else:
                unit_maintenance.condition = UnitMaintenance.UNDEFINED
        else:
            unit_maintenance.condition = UnitMaintenance.UNDEFINED

        unit_maintenance.maintained_at = maintained_at
        unit_maintenance.last_imported_time = TIMEZONE.localize(
            datetime.now().replace(microsecond=0)
        )

        try:
            unit_maintenance.save()
            if is_created:
                logger.info(f"Created UnitMaintenance for '{name}' (geometry_id: {geometry_id})")
            else:
                logger.debug(f"Updated UnitMaintenance for '{name}' (geometry_id: {geometry_id})")
        except Exception as exp:
            logger.error(f"Unable to save ski trail maintenance history for '{name}', reason: {exp}")
            continue

        # Link geometry to unit_maintenance
        geometry.unit_maintenance = unit_maintenance
        geometry.save()
        num_geometry_linked += 1
        logger.debug(f"Linked geometry {geometry_id} to unit_maintenance {unit_maintenance.id}")

        if is_created:
            num_created += 1
        else:
            num_updated += 1
        if unit_maintenance.id in objs_to_delete:
            objs_to_delete.remove(unit_maintenance.id)

    UnitMaintenance.objects.filter(id__in=objs_to_delete).delete()
    summary = (
        f"Created {num_created}, updated {num_updated}, deleted {len(objs_to_delete)} ski trail maintenance histories. "
        f"Skipped {num_skipped_invalid_date} due to invalid date. "
        f"Linked {num_geometry_linked} geometries, {num_geometry_not_found} geometries not found."
    )
    logger.info(summary)


class Command(BaseCommand):

    @db.transaction.atomic
    def handle(self, *args, **options):
        logger.info("Starting ski trails maintenance history import...")
        try:
            json_data = get_json_data(settings.SKI_TRAILS_MAINTENANCE_HISTORY_URL)
            if not json_data:
                logger.error("Failed to fetch JSON data from API")
                return
            logger.info(f"Successfully fetched JSON data. Keys: {list(json_data.keys())}")
            save_maintenance_history(json_data)
            logger.info("Ski trails maintenance history import completed.")
        except Exception as e:
            logger.exception(f"Error during ski trails maintenance history import: {e}")
            raise
