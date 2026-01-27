import logging
from datetime import datetime

import pytz
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from maintenance.models import DEFAULT_SRID, UnitMaintenance, UnitMaintenanceGeometry

from .constants import ICE_TRACKS_DATE_FIELD_FORMAT
from .utils import get_json_data, get_or_create_sports_facility_unit

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
    num_geometry_linked = 0
    features = json_data.get("features", None)
    if not features:
        logger.error("No features found in JSON response.")
        return

    logger.info(f"Processing {len(features)} features from ice tracks maintenance history API")

    for feature in features:
        properties = feature.get("properties", None)
        if not properties:
            logger.warning(
                f"'properties' not found for feature: {feature}, skipping..."
            )
            continue

        # Use 'id' as geometry_id (similar to ski trails using location_id)
        geometry_id = properties.get("id", None)
        if not geometry_id:
            logger.warning(
                f"'id' not found in properties for feature: {feature}, skipping..."
            )
            continue

        # Get or create geometry by geometry_id
        try:
            geometry, geometry_created = UnitMaintenanceGeometry.objects.get_or_create(
                geometry_id=geometry_id,
                defaults={"geometry": None}  # Will be set below
            )
        except Exception as exp:
            logger.error(f"Error getting/creating geometry for geometry_id={geometry_id}: {exp}")
            continue

        # Get or create Unit record for this ice track
        # Extract storable information from properties
        name = properties.get("name", None)
        address = properties.get("address", None)
        zip_code = properties.get("zip", None)
        description = properties.get("description", None)
        
        # Get geometry from feature (Point) for location
        geometry_data = feature.get("geometry", None)
        point_geometry = None
        if geometry_data:
            coordinates = geometry_data.get("coordinates", None)
            if coordinates and len(coordinates) == 2:
                from django.contrib.gis.geos import Point
                lon = coordinates[0]
                lat = coordinates[1]
                point_geometry = Point(lon, lat, srid=DEFAULT_SRID)
        
        unit = get_or_create_sports_facility_unit(
            geometry_id=geometry_id,
            name=name,
            description=description,
            address=address,
            zip_code=zip_code,
            geometry=point_geometry,
        )
        
        # Determine which UnitMaintenance to use/update
        # Strategy: Link maintenance to geometry via geometry_id
        # Each geometry gets its own UnitMaintenance record (or reuses existing)
        if geometry.unit_maintenance:
            # Geometry already linked, update existing record
            unit_maintenance = geometry.unit_maintenance
            is_created = False
            # Update unit if it was None or different
            if unit_maintenance.unit != unit:
                unit_maintenance.unit = unit
        else:
            # Create a new UnitMaintenance for this geometry
            unit_maintenance = UnitMaintenance(unit=unit, target=UnitMaintenance.ICE_TRACK)
            is_created = True
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
        elif bool(condition_val):
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
            if is_created:
                logger.info(f"Created UnitMaintenance for ice track (geometry_id: {geometry_id})")
            else:
                logger.debug(f"Updated UnitMaintenance for ice track (geometry_id: {geometry_id})")
        except Exception as exp:
            logger.error(f"Unable to save ice track maintenance history for geometry_id={geometry_id}, reason: {exp}")
            continue

        # Update geometry with Point coordinates and link to unit_maintenance
        geometry_data = feature.get("geometry", None)
        if geometry_data:
            coordinates = geometry_data.get("coordinates", None)
            if coordinates and len(coordinates) == 2:
                lon = coordinates[0]
                lat = coordinates[1]
                point = Point(lon, lat, srid=DEFAULT_SRID)
                geometry.geometry = point
            else:
                logger.warning(
                    f"Missing or invalid field 'coordinates' for feature geometry_id={geometry_id}, skipping geometry update..."
                )
        else:
            logger.warning(
                f"Missing 'geometry' field for feature geometry_id={geometry_id}, skipping geometry update..."
            )

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
        f"Created {num_created}, updated {num_updated}, deleted {len(objs_to_delete)} ice track maintenance histories. "
        f"Linked {num_geometry_linked} geometries."
    )
    logger.info(summary)


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
