import uuid

from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField


class BaseType(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    type_name = models.CharField(max_length=64, null=True, unique=True)
    name = models.CharField(max_length=128, null=True)
    description = models.TextField(
        null=True, verbose_name="Optional description of the content type."
    )

    class Meta:
        abstract = True
        ordering = ["type_name"]

    def __str__(self):
        if self.type_name:
            return self.type_name
        return str(self.id)


class ContentType(BaseType):
    class Meta(BaseType.Meta):
        indexes = (
            GinIndex(fields=["search_column_fi"]),
            GinIndex(fields=["search_column_sv"]),
            GinIndex(fields=["search_column_en"]),
        )

    search_column_fi = SearchVectorField(null=True)
    search_column_sv = SearchVectorField(null=True)
    search_column_en = SearchVectorField(null=True)

    syllables_fi = ArrayField(models.CharField(max_length=16), default=list)

    @classmethod
    def get_search_column_indexing(cls, lang):
        """
        Defines the columns to be to_tsvector to the search_column
        ,config language and weight.
        """
        if lang == "fi":
            return [
                ("name_fi", "finnish", "A"),
                ("syllables_fi", "finnish", "A"),
                ("description_fi", "finnish", "B"),
            ]
        elif lang == "sv":
            return [
                ("name_sv", "swedish", "A"),
                ("description_sv", "swedish", "B"),
            ]
        elif lang == "en":
            return [
                ("name_en", "english", "A"),
                ("description_en", "english", "B"),
            ]
        else:
            return []

    @classmethod
    def get_syllable_fi_columns(cls):
        """
        Defines the columns that will be used when populating
        finnish syllables to syllables_fi column. The content
        will be tokenized to lexems(to_tsvector) and added to
        the search_column.
        """
        return ["name_fi"]


class GroupType(BaseType):
    pass
