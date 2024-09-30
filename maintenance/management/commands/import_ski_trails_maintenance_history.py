import logging
from datetime import datetime

import pytz
from django import db
from django.core.management.base import BaseCommand

from maintenance.models import UnitMaintenance, UnitMaintenanceGeometry
from services.models import Unit

from .constants import SKI_TRAILS_DATE_FIELD_FORMAT
from .utils import get_json_data

logger = logging.getLogger(__name__)
URL = (
    "https://api.paikannuspalvelu.fi/v1/public/location/lastvisit/"
    "?data_key=cftqHZ8mjwf3uYpXz9HAUH3nXY6IjrvrvYmRMnbZ&author=?&format=geojson&max_distance=50"
)
SKITRAIL_TO_UNIT_ID_MAPPINGS = {
    "Impivaara-Isosuo": 805,
    "Impivaara-Mälikkälä": 804,
    "Kuloisten reitti": 803,
    "Oriketo-Räntämäki": 801,
    "Oriketo-Halinen": 800,
    "Ispoinen-Harittu-Lauste": 799,
    "Orikedon kuntorata": 790,
    "Nunnavuoren kuntoreitti": 789,
    "Luolavuori-Ispoinen": 796,
    "Ispoisten kuntoreitti": None,
    "Ispoisten kuntorata (Wibeliuksenpuisto)": 785,
    "Lausteen kuntorata": 786,
    "Hirvensalo": 783,
    "Härkämäki": 784,
    "Maaria": 787,
    "Moisio": 788,
    "Pansio": 791,
    "Suikkila": 792,
    "Varissuo": 795,
}
TIMEZONE = pytz.timezone("Europe/Helsinki")


def get_unit(name):
    try:
        return Unit.objects.get(id=SKITRAIL_TO_UNIT_ID_MAPPINGS[name])
    except (Unit.DoesNotExist, KeyError):
        return None


def save_maintenance_history(json_data):
    objs_to_delete = list(
        UnitMaintenance.objects.filter(target=UnitMaintenance.SKI_TRAIL).values_list(
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
        is_created = False
        properties = feature.get("properties", None)
        if not properties:
            logger.warning(
                f"'properties' not found for feature: {feature}, skipping..."
            )
            continue
        name = properties.get("name", None)
        maintained_at = None
        try:
            maintained_at = TIMEZONE.localize(
                datetime.strptime(
                    properties.get("date", ""), SKI_TRAILS_DATE_FIELD_FORMAT
                )
            )
        except ValueError as exp:
            logger.error(
                f"Skipping feature {feature}, missing or invalid 'date' field, reason {exp}."
            )
            continue

        unit = get_unit(name)
        if not unit:
            logger.warning(f"Unit not found for {name}")

        filter = {
            "unit": unit,
            "target": UnitMaintenance.SKI_TRAIL,
        }
        queryset = UnitMaintenance.objects.filter(**filter)

        if queryset.count() == 0:
            unit_maintenance = UnitMaintenance(**filter)
            queryset = UnitMaintenance.objects.filter(**filter)
            is_created = True
        else:
            unit_maintenance = UnitMaintenance.objects.filter(**filter).first()
            if queryset.count() > 1:
                logger.warning(f"Found duplicate UnitMaintenance {filter}")

        unit_maintenance.maintained_at = maintained_at
        unit_maintenance.last_imported_time = TIMEZONE.localize(
            datetime.now().replace(microsecond=0)
        )

        try:
            unit_maintenance.save()
        except Exception as exp:
            logger.error(f"unable to save ski trail maintenance history, reason: {exp}")
            continue

        geometry_id = properties.get("location_id", None)
        try:
            geometry = UnitMaintenanceGeometry.objects.get(geometry_id=geometry_id)
            geometry.unit_maintenance = unit_maintenance
            geometry.save()
        except UnitMaintenanceGeometry.DoesNotExist:
            logger.warning(
                f"'geometry not set, cause: geometry {geometry_id} not found."
            )

        if is_created:
            num_created += 1
        else:
            num_updated += 1
        if unit_maintenance.id in objs_to_delete:
            objs_to_delete.remove(unit_maintenance.id)

    UnitMaintenance.objects.filter(id__in=objs_to_delete).delete()
    logger.info(
        f"Created {num_created}, updated {num_updated}, deleted {len(objs_to_delete)} ski trail maintenance histories"
    )


class Command(BaseCommand):

    @db.transaction.atomic
    def handle(self, *args, **options):
        json_data = get_json_data(URL)
        save_maintenance_history(json_data)
