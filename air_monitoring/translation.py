from modeltranslation.translator import TranslationOptions, translator

from air_monitoring.models import Station


class StationTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(Station, StationTranslationOptions)
