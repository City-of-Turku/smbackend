from modeltranslation.translator import TranslationOptions, translator

from mobility_data.models import MobileUnit, MobileUnitGroup


class MobileUnitGroupTranslationOptions(TranslationOptions):
    fields = ("name", "description")


translator.register(MobileUnitGroup, MobileUnitGroupTranslationOptions)


class MobileUnitTranslationOptions(TranslationOptions):
    fields = ("name", "address", "description")


translator.register(MobileUnit, MobileUnitTranslationOptions)
