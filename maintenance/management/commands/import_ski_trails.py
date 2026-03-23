import logging

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos.error import GEOSException
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from maintenance.models import UnitMaintenance, UnitMaintenanceGeometry
from services.models import Unit

from .utils import (
    SPORTS_FACILITY_UNIT_ID_OFFSET,
    apply_maintenance_unit_description_json,
    get_data_layer,
    get_or_create_sports_facility_unit,
    get_unit_maintenance_description_source,
    merge_ski_trail_unit_description,
)

logger = logging.getLogger(__name__)


def _feature_first_int(feature, keys):
    for key in keys:
        try:
            return feature[key].as_int()
        except Exception:
            continue
    return None


def _feature_first_nonempty_string(feature, keys):
    for key in keys:
        val = _feature_str_field(feature, key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def _feature_str_field(feature, key):
    """Read an optional OGR feature field as a string (length may be numeric)."""
    try:
        field = feature[key]
    except (KeyError, IndexError, AttributeError):
        return None
    try:
        s = field.as_string()
        if s:
            return s
    except Exception:
        pass
    try:
        return str(field.as_int())
    except Exception:
        pass
    try:
        return str(field.as_double())
    except Exception:
        return None


def save_trails(layer):
    num_created = 0
    num_updated = 0
    num_units_synced = 0
    skip_geom_logged = False
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

            geometry_id = _feature_first_int(
                feature,
                (
                    "construction_point_id",
                    "location_id",
                    "id",
                    "track_id",
                    "point_id",
                    "fid",
                    "FID",
                    "OBJECTID",
                    "objectid",
                ),
            )
            if geometry_id is None:
                if not skip_geom_logged:
                    try:
                        logger.warning(
                            "Ski trail: no geometry id on feature; example OGR field names: %s",
                            list(feature.keys()),
                        )
                    except Exception as exp:
                        logger.warning(
                            "Ski trail: could not list OGR fields (%s); check SKI_TRAILS_URL layer",
                            exp,
                        )
                    skip_geom_logged = True
                continue
            filter = {"geometry_id": geometry_id}
            queryset = UnitMaintenanceGeometry.objects.filter(**filter)

            trail_length = _feature_str_field(feature, "length")
            trail_lights = _feature_str_field(feature, "lights")

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
                logger.warning(
                    f"geometry id {unit_maintenance_geometry.geometry_id} exists, skipping..."
                )
            else:
                trail_name = _feature_first_nonempty_string(
                    feature, ("name", "nimi", "title")
                )
                unit = get_or_create_sports_facility_unit(
                    geometry_id=geometry_id,
                    name=trail_name,
                    geometry=geometry,
                )
                if unit is None:
                    try:
                        unit = Unit.objects.get(
                            pk=SPORTS_FACILITY_UNIT_ID_OFFSET + geometry_id
                        )
                    except Unit.DoesNotExist:
                        unit = None
                if unit is not None:
                    existing_desc = get_unit_maintenance_description_source(unit)
                    apply_maintenance_unit_description_json(
                        unit,
                        merge_ski_trail_unit_description(
                            existing_desc,
                            length=trail_length,
                            lights=trail_lights,
                        ),
                    )
                    num_units_synced += 1

        except Exception as exp:
            logger.error(f"Could not save ski trail {feature}, reason {exp}")
        num_created = num_created + 1 if is_created else num_created
        num_updated = num_updated + 1 if is_updated else num_updated
    return num_created, num_updated, num_units_synced


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
        num_created, num_updated, num_units_synced = save_trails(layer)
        logger.info(
            "Ski trails geometry: created %s, updated %s rows; "
            "synced %s service units (names + description JSON).",
            num_created,
            num_updated,
            num_units_synced,
        )
