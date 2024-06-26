import logging
import os

import yaml
from django.core.management import BaseCommand

from mobility_data.importers.lounaistieto_shapefiles import (
    import_lounaistieto_data_source,
)
from mobility_data.importers.utils import delete_mobile_units, get_root_dir

logger = logging.getLogger("mobility_data")
CONFIG_FILE = "lounaistieto_shapefiles_config.yml"


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--delete-data-source",
            action="store",
            type=str,
            nargs="+",
            help="",
        )

    def handle(self, *args, **options):
        if options["delete_data_source"]:
            content_type = options["delete_data_source"]
            if len(content_type) == 0:
                logger.warning("Specify the content type to delete.")
            delete_mobile_units(content_type[0])
            logger.info(f"Deleted MobileUnit and ContentType for {content_type[0]}")
        else:
            config_path = f"{get_root_dir()}/mobility_data/importers/data/"
            path = os.path.join(config_path, CONFIG_FILE)
            config = yaml.safe_load(open(path, "r", encoding="utf-8"))
            for data_source in config["data_sources"]:
                try:
                    import_lounaistieto_data_source(data_source)
                except Exception as e:
                    logger.warning(f"Skipping data_source {data_source} : {e}")
