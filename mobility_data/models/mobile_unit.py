import uuid

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import (  # add the Postgres recommended GIN index
    GinIndex,
)
from django.contrib.postgres.search import SearchVectorField
from munigeo.models import Municipality

from . import ContentType, GroupType


class BaseUnit(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    is_active = models.BooleanField(default=True)
    created_time = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=256, null=True)
    description = models.TextField(null=True)

    class Meta:
        abstract = True
        ordering = ["-created_time"]

    def __str__(self):
        if self.name:
            return self.name
        else:
            return ""


class MobileUnitGroup(BaseUnit):
    """
    Umbrella model to order MobileUnits into groups.
    Every Group has a relation to GroupType that describes the group.
    i.e. A walkingroute group can have routedata, sights as mobile_units.
    """

    group_type = models.ForeignKey(
        GroupType, on_delete=models.CASCADE, related_name="unit_groups"
    )


class MobileUnit(BaseUnit):
    """
    MobileUnit is the base model. It contains basic information about the
    MobileUnit such as name, geometry. Eeach MobileUnit has a relation to a
    ContentType that describes the specific type of the unit. MobileUnits
    can also have a relation to a UnitGroup. The extra field can contain
    data that are specific for a data source.
    """

    class Meta:
        indexes = (
            GinIndex(fields=["search_column_fi"]),
            GinIndex(fields=["search_column_sv"]),
            GinIndex(fields=["search_column_en"]),
        )

    geometry = models.GeometryField(srid=settings.DEFAULT_SRID, null=True)
    address = models.CharField(max_length=100, null=True)
    municipality = models.ForeignKey(
        Municipality, null=True, db_index=True, on_delete=models.CASCADE
    )
    address_zip = models.CharField(max_length=10, null=True)

    content_types = models.ManyToManyField(ContentType, related_name="mobile_units")
    unit_id = models.IntegerField(
        null=True,
        verbose_name="optional id to a unit in the servicemap, if id exist data is serialized from services_unit table",
    )
    mobile_unit_group = models.ForeignKey(
        MobileUnitGroup,
        on_delete=models.CASCADE,
        null=True,
        related_name="mobile_units",
    )
    extra = models.JSONField(null=True)
    search_column_fi = SearchVectorField(null=True)
    search_column_sv = SearchVectorField(null=True)
    search_column_en = SearchVectorField(null=True)

    content_type_names_fi = ArrayField(models.CharField(max_length=200), default=list)
    content_type_names_sv = ArrayField(models.CharField(max_length=200), default=list)
    content_type_names_en = ArrayField(models.CharField(max_length=200), default=list)

    @classmethod
    def get_search_column_indexing(cls, lang):
        """
        Defines the columns to be to_tsvector to the search_column
        ,config language and weight.
        """
        if lang == "fi":
            return [
                ("name_fi", "finnish", "A"),
                ("content_type_names_fi", "finnish", "A"),
                ("description_fi", "finnish", "B"),
                ("extra", None, "C"),
                ("address_zip", None, "D"),
            ]
        elif lang == "sv":
            return [
                ("name_sv", "swedish", "A"),
                ("content_type_names_sv", "swedish", "A"),
                ("description_sv", "swedish", "B"),
                ("extra", None, "C"),
                ("address_zip", None, "D"),
            ]
        elif lang == "en":
            return [
                ("name_en", "english", "A"),
                ("content_type_names_en", "english", "A"),
                ("description_en", "english", "B"),
                ("extra", None, "C"),
                ("address_zip", None, "D"),
            ]
        else:
            return []
