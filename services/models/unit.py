from django.apps import apps
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField, HStoreField
from django.contrib.postgres.indexes import (  # add the Postgres recommended GIN index
    GinIndex,
)
from django.contrib.postgres.search import SearchVectorField
from django.db.models import JSONField, Manager
from django.utils import timezone
from django.utils.translation import gettext as _
from munigeo.models import Municipality
from munigeo.utils import get_default_srid

from services.utils import check_valid_concrete_field, get_translated

from .department import Department
from .keyword import Keyword

PROJECTION_SRID = get_default_srid()
PROVIDER_TYPES = (
    (1, "SELF_PRODUCED"),
    (2, "MUNICIPALITY"),
    (3, "ASSOCIATION"),
    (4, "PRIVATE_COMPANY"),
    (5, "OTHER_PRODUCTION_METHOD"),
    (6, "PURCHASED_SERVICE"),
    (7, "UNKNOWN_PRODUCTION_METHOD"),
    (8, "CONTRACT_SCHOOL"),
    (9, "SUPPORTED_OPERATIONS"),
    (10, "PAYMENT_COMMITMENT"),
    (11, "VOUCHER_SERVICE"),
)

ORGANIZER_TYPES = (
    (0, "ASSOCIATION"),
    (1, "FOUNDATION"),
    (2, "GOVERNMENT"),
    (3, "GOVERNMENTAL_COMPANY"),
    (4, "JOINT_MUNICIPAL_AUTHORITY"),
    (5, "MUNICIPAL_ENTERPRISE_GROUP"),
    (6, "MUNICIPALITY"),
    (7, "MUNICIPALLY_OWNED_COMPANY"),
    (8, "ORGANIZATION"),
    (9, "OTHER_REGIONAL_COOPERATION_ORGANIZATION"),
    (10, "PRIVATE_ENTERPRISE"),
    (11, "UNKNOWN"),
)

_unit_related_fields = set()


def get_unit_related_fields():
    global _unit_related_fields
    if len(_unit_related_fields) > 0:
        return _unit_related_fields
    unit_model = apps.get_model(app_label="services", model_name="Unit")
    for f in unit_model._meta.get_fields():
        if f.is_relation:
            _unit_related_fields.add(f.name)
    return _unit_related_fields


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(_("Active"), default=True)
    deleted_at = models.DateTimeField(_("Deleted at"), blank=True, null=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()


class UnitSearchManager(Manager):
    def get_queryset(self):
        qs = (
            super(UnitSearchManager, self)
            .get_queryset()
            .prefetch_related("accessibility_shortcomings")
        )
        if self.only_fields:
            fields = [
                f for f in self.only_fields if check_valid_concrete_field(Unit, f)
            ]
            qs = qs.only(*fields)
        if not self.include_fields:
            return qs
        unit_related_fields = get_unit_related_fields()
        for f in self.include_fields:
            if f in unit_related_fields:
                qs = qs.prefetch_related(f)
        return qs


class Unit(SoftDeleteModel):
    id = models.IntegerField(primary_key=True)

    public = models.BooleanField(null=False, default=True)

    location = models.PointField(null=True, srid=PROJECTION_SRID)  # lat, lng?
    geometry = models.GeometryField(srid=PROJECTION_SRID, null=True)
    geometry_3d = models.GeometryField(srid=PROJECTION_SRID, null=True, dim=3)

    department = models.ForeignKey(Department, null=True, on_delete=models.CASCADE)
    root_department = models.ForeignKey(
        Department, null=True, related_name="descendant_units", on_delete=models.CASCADE
    )

    organizer_type = models.PositiveSmallIntegerField(
        choices=ORGANIZER_TYPES, null=True
    )
    organizer_name = models.CharField(max_length=150, null=True)
    organizer_business_id = models.CharField(max_length=10, null=True)

    provider_type = models.PositiveSmallIntegerField(choices=PROVIDER_TYPES, null=True)
    picture_url = models.URLField(max_length=250, null=True)
    picture_entrance_url = models.URLField(max_length=500, null=True)
    streetview_entrance_url = models.URLField(max_length=500, null=True)

    description = models.TextField(null=True)
    short_description = models.TextField(null=True)
    name = models.CharField(max_length=200, db_index=True)
    street_address = models.CharField(max_length=100, null=True)

    www = models.URLField(max_length=400, null=True)
    address_postal_full = models.CharField(max_length=100, null=True)
    call_charge_info = models.CharField(max_length=500, null=True)
    displayed_service_owner = models.CharField(max_length=120, null=True)
    displayed_service_owner_type = models.CharField(max_length=100, null=True)

    picture_caption = models.TextField(null=True)

    phone = models.CharField(max_length=120, null=True)
    fax = models.CharField(max_length=50, null=True)
    email = models.EmailField(max_length=100, null=True)
    accessibility_phone = models.CharField(max_length=50, null=True)
    accessibility_email = models.EmailField(max_length=100, null=True)
    accessibility_www = models.URLField(max_length=400, null=True)

    created_time = models.DateTimeField(
        null=True
    )  # ASK API: are these UTC? no Z in output

    municipality = models.ForeignKey(
        Municipality, null=True, db_index=True, on_delete=models.CASCADE
    )
    address_zip = models.CharField(max_length=10, null=True)

    data_source = models.CharField(max_length=50, null=True)
    extensions = HStoreField(null=True)

    last_modified_time = models.DateTimeField(
        db_index=True, help_text="Time of last modification"
    )

    service_nodes = models.ManyToManyField("ServiceNode", related_name="units")
    services = models.ManyToManyField(
        "Service", related_name="units", through="UnitServiceDetails"
    )
    keywords = models.ManyToManyField(Keyword)

    connection_hash = models.CharField(
        max_length=40,
        null=True,
        help_text="Automatically generated hash of connection info",
    )
    accessibility_property_hash = models.CharField(
        max_length=40,
        null=True,
        help_text="Automatically generated hash of accessibility property info",
    )
    identifier_hash = models.CharField(
        max_length=40,
        null=True,
        help_text="Automatically generated hash of other identifiers",
    )
    service_details_hash = models.CharField(max_length=40, null=True)

    accessibility_viewpoints = JSONField(default=dict, null=True)

    # Cached fields for better performance
    root_service_nodes = models.CharField(max_length=50, null=True)

    objects = Manager()
    search_objects = UnitSearchManager()
    extra = models.JSONField(null=True)
    related_units = models.ManyToManyField("self", blank=True)
    # Note, TranslatedModel do not support ArrayField.
    service_names_fi = ArrayField(models.CharField(max_length=200), default=list)
    service_names_sv = ArrayField(models.CharField(max_length=200), default=list)
    service_names_en = ArrayField(models.CharField(max_length=200), default=list)

    search_column_fi = SearchVectorField(null=True)
    search_column_sv = SearchVectorField(null=True)
    search_column_en = SearchVectorField(null=True)

    syllables_fi = ArrayField(models.CharField(max_length=16), default=list)

    class Meta:
        ordering = ["-pk"]
        indexes = (
            GinIndex(fields=["search_column_fi"]),
            GinIndex(fields=["search_column_sv"]),
            GinIndex(fields=["search_column_en"]),
        )

    def __str__(self):
        return "%s (%s)" % (get_translated(self, "name"), self.id)

    def get_root_service_nodes(self):
        from .service_node import ServiceNode

        tree_ids = self.service_nodes.all().values_list("tree_id", flat=True).distinct()
        qs = ServiceNode.objects.filter(level=0).filter(tree_id__in=list(tree_ids))
        service_node_list = qs.values_list("id", flat=True).distinct()
        return sorted(service_node_list)

    def service_names(self):
        return "\n".join((service.name for service in self.services.all()))

    def service_keywords(self):
        return "\n".join(
            (
                "\n".join((keyword.name for keyword in service.keywords.all()))
                for service in self.services.all()
            )
        )

    def highlight_names(self):
        unit_connection_model = apps.get_model(
            app_label="services", model_name="UnitConnection"
        )
        return "\n".join(
            (
                connection.name
                for connection in self.connections.filter(
                    section_type=unit_connection_model.HIGHLIGHT_TYPE
                )
            )
        )

    @classmethod
    def get_syllable_fi_columns(cls):
        """
        Defines the columns that will be used when populating
        finnish syllables to syllables_fi column. The content
        will be tokenized to lexems(to_tsvector) and added to
        the search_column.
        """
        return ["name_fi", "service_names_fi"]

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
                ("service_names_fi", "finnish", "B"),
                ("extra", None, "C"),
                ("address_zip", None, "D"),
            ]
        elif lang == "sv":
            return [
                ("name_sv", "swedish", "A"),
                ("service_names_sv", "swedish", "B"),
                ("extra", None, "C"),
                ("address_zip", None, "D"),
            ]
        elif lang == "en":
            return [
                ("name_en", "english", "A"),
                ("service_names_en", "english", "B"),
                ("extra", None, "C"),
                ("address_zip", None, "D"),
            ]
        else:
            return []

    def soft_delete(self):
        self.public = False
        super().soft_delete()
