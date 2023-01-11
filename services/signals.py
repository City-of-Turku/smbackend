import operator
from functools import reduce

from django.contrib.postgres.search import SearchVector
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from munigeo.models import Address, AdministrativeDivision

from services.models import Service, ServiceNode, Unit
from services.search.utils import hyphenate


@receiver(post_save, sender=Unit)
def unit_on_save(sender, **kwargs):
    obj = kwargs["instance"]
    generate_syllables(obj)
    # Do transaction after successfull commit.
    transaction.on_commit(populate_search_column(obj))


@receiver(post_save, sender=Service)
def service_on_save(sender, **kwargs):
    obj = kwargs["instance"]
    generate_syllables(obj)
    transaction.on_commit(populate_search_column(obj))


@receiver(post_save, sender=ServiceNode)
def servicenode_on_save(sender, **kwargs):
    obj = kwargs["instance"]
    generate_syllables(obj)
    # To avoid conflicts with Service names, only index if service_reference is None
    if not obj.service_reference:
        transaction.on_commit(populate_search_column(obj))


@receiver(post_save, sender=Address)
def address_on_save(sender, **kwargs):
    obj = kwargs["instance"]
    transaction.on_commit(populate_search_column(obj))


@receiver(post_save, sender=AdministrativeDivision)
def administrative_division_on_save(sender, **kwargs):
    obj = kwargs["instance"]
    transaction.on_commit(populate_search_column(obj))


def generate_syllables(obj):
    model = obj._meta.model
    syllables_fi = []
    for column in obj.get_syllable_fi_columns():
        row_content = getattr(obj, column, None)
        if row_content:
            if isinstance(row_content, str):
                row_content = row_content.split()
            for word in row_content:
                syllables = hyphenate(word)
                for s in syllables:
                    syllables_fi.append(s)
    # Use update instead of save. Save triggers the post_save signal and MPTT building.
    model.objects.filter(id=obj.id).update(syllables_fi=syllables_fi)


def populate_search_column(obj):
    # Get the information of search_columns and weights to be added to sear from the model
    search_columns = {}
    search_columns["fi"] = obj.get_search_column_indexing("fi")
    search_columns["sv"] = obj.get_search_column_indexing("sv")
    search_columns["en"] = obj.get_search_column_indexing("en")
    id = obj.id

    def on_commit():
        search_vectors = {}
        for lang in ["fi", "sv", "en"]:
            search_vectors[lang] = []
            for column in search_columns[lang]:
                search_vectors[lang].append(
                    SearchVector(column[0], config=column[1], weight=column[2])
                )

            # Add all SearchVectors in search_vectors list to search_column.
            key = "search_column_%s" % lang
            obj.__class__.objects.filter(id=id).update(
                **{key: reduce(operator.add, search_vectors[lang])}
            )
        # Update finnish search column without syllables for Units
        if isinstance(obj, Unit):
            columns = obj.get_search_column_indexing_without_syllables()
            search_vectors = []
            for column in columns:
                search_vectors.append(
                    SearchVector(column[0], config=column[1], weight=column[2])
                )
            key = "search_column_fi_without_syllables"
            obj.__class__.objects.filter(id=id).update(
                **{key: reduce(operator.add, search_vectors)}
            )

    return on_commit
