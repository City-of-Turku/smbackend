import json
import logging
from xml.parsers.expat import ExpatError

import requests
import xmltodict
from django.core.cache import cache
from django.core.management.base import BaseCommand

from iot.models import IoTData, IoTDataSource
from iot.utils import clear_source_names_from_cache, get_cache_keys, get_source_names

logger = logging.getLogger("iot")


def save_data_to_db(source):
    IoTData.objects.filter(data_source=source).delete()
    try:
        response = requests.get(source.url, headers=source.headers)
    except requests.exceptions.ConnectionError:
        logger.error(f"Could not fetch data from: {source.url}")
        return
    if source.is_xml:
        try:
            json_data = xmltodict.parse(response.text)
        except ExpatError as err:
            logger.error(
                f"Could not parse XML data from the give url {source.url}. {err}"
            )
            return
    else:
        try:
            json_data = response.json()
        except json.decoder.JSONDecodeError as err:
            logger.error(f"Could not decode data to JSON from: {source.url}. {err}")
            return

    IoTData.objects.create(data_source=source, data=json_data)


def clear_cache(source_name):
    key_queryset, key_serializer = get_cache_keys(source_name)
    cache.delete_many([key_queryset, key_serializer])
    clear_source_names_from_cache()


class Command(BaseCommand):
    help = "Import IoT-Data for intermediate storage."
    source_names = get_source_names()

    def add_arguments(self, parser):
        parser.add_argument(
            "source_name",
            help=f"Three letter name of the source to import. Available source names are: {self.source_names} ",
        )

    def handle(self, *args, **options):
        source_name = options["source_name"]
        if source_name not in self.source_names:
            logger.error(f"{source_name} not found, choices are {self.source_names}")
            return
        # Clear cache every time data is imported.
        # This ensures that the data is up to date.
        clear_cache(source_name)
        source = IoTDataSource.objects.get(source_name=source_name)
        save_data_to_db(source)
