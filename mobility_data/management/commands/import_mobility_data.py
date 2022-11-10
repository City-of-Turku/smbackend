"""
Main importer for mobility data sources.
"""
import logging

from django.core import management
from django.core.management import BaseCommand

from mobility_data.management.commands.import_wfs import get_configured_cotent_types

# Names of the mobility_data importers to be include when importing data.
importers = [
    "culture_routes",
    "gas_filling_stations",
    "charging_stations",
    "bicycle_stands",
    "speed_limit_zones",
    "bike_service_stations",
    "share_car_parking_places",
    "bicycle_networks",
    "marinas",
    "disabled_and_no_staff_parkings",
    "loading_and_unloading_places",
    "lounaistieto_shapefiles",
]
# Read the content types to be imported
wfs_content_types = get_configured_cotent_types()
logger = logging.getLogger("mobility_data")


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("Importing mobility data...")
        management.call_command("import_wfs", wfs_content_types)
        for importer in importers:
            management.call_command(f"import_{importer}")
