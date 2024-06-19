import logging

from django.core.management.base import BaseCommand

from mobility_data.importers.utils import set_content_type_names
from mobility_data.models import ContentType, MobileUnit
from services.management.commands.index_search_columns import (
    generate_syllables,
    get_search_column,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        logger.info("Setting content type names to all mobile units...")
        [set_content_type_names(m_u) for m_u in MobileUnit.objects.all()]

        for lang in ["fi", "sv", "en"]:
            key = "search_column_%s" % lang
            # Only generate syllables for the finnish language
            if lang == "fi":
                logger.info(f"Generating syllables for language: {lang}.")
                logger.info(
                    f"Syllables generated for {generate_syllables(MobileUnit)} MobileUnits"
                )
                logger.info(
                    f"Syllables generated for {generate_syllables(ContentType)} ContentTypes"
                )
            logger.info(
                f"{lang} MobileUnits indexed: {MobileUnit.objects.update(**{key: get_search_column(MobileUnit, lang)})}"
            )
            logger.info(
                f"{lang} ContentTypes indexed: {ContentType.objects.update(**{key: get_search_column(ContentType, lang)})}"
            )
