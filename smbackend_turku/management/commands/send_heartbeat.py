import logging

import requests
from django.core.management.base import BaseCommand

logger = logging.getLogger("smbackend")


class Command(BaseCommand):
    help = "Ping a heartbeat URL (e.g. a Betterstack heartbeat endpoint) to signal liveness."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            type=str,
            required=True,
            help="The heartbeat URL to ping.",
        )

    def handle(self, *args, **options):
        url = options["url"]
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        logger.debug(
            f"Heartbeat sent successfully to {url} (HTTP {response.status_code})"
        )
