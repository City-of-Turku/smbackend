import logging

from django.core.management.base import BaseCommand

from eco_counter.constants import ECO_COUNTER
from eco_counter.management.commands.utils import save_stations

logger = logging.getLogger("eco_counter")


class Command(BaseCommand):
    help = "Refresh Eco-Visio station list/geometry without deleting missing stations."

    def handle(self, *args, **options):
        logger.info("Refreshing Eco-Visio stations (keeping missing stations).")
        save_stations(ECO_COUNTER, delete_missing=False)
