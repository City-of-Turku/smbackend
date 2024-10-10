from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField

from maintenance.management.commands.constants import PROVIDER_CHOICES
from services.models import Unit

DEFAULT_SRID = 4326


class UnitMaintenance(models.Model):
    """
    Model for storing maintenance information for service_unit entities.
    """

    UNDEFINED = "UNDEFINED"
    USABLE = "USABLE"
    UNUSABLE = "UNUSABLE"
    CONDITION_CHOICES = [
        (UNDEFINED, "undefined"),
        (USABLE, "usable"),
        (UNUSABLE, "unusable"),
    ]
    SKI_TRAIL = "SKI_TRAIL"
    ICE_TRACK = "ICE_TRACK"
    TARGET_CHOICES = [(SKI_TRAIL, "ski_trail"), (ICE_TRACK, "ice_track")]
    condition = models.CharField(
        max_length=16, choices=CONDITION_CHOICES, default=UNDEFINED
    )
    target = models.CharField(max_length=16, choices=TARGET_CHOICES, default=SKI_TRAIL)
    maintained_at = models.DateTimeField(null=True, blank=True)
    last_imported_time = models.DateTimeField(help_text="Time of last data import")
    unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        related_name="maintenance",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-maintained_at"]


class UnitMaintenanceGeometry(models.Model):
    geometry_id = models.IntegerField(unique=True, blank=True, null=True)
    geometry = models.GeometryField(srid=DEFAULT_SRID, null=True)
    unit_maintenance = models.ForeignKey(
        UnitMaintenance,
        on_delete=models.CASCADE,
        related_name="geometries",
        null=True,
        blank=True,
    )


class MaintenanceUnit(models.Model):

    unit_id = models.CharField(max_length=64, null=True)
    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES, null=True)
    names = ArrayField(models.CharField(max_length=64), default=list)

    def __str__(self):
        return "%s" % (self.unit_id)


class MaintenanceWork(models.Model):
    geometry = models.GeometryField(srid=DEFAULT_SRID, null=True)
    events = ArrayField(models.CharField(max_length=64), default=list)
    original_event_names = ArrayField(models.CharField(max_length=64), default=list)
    timestamp = models.DateTimeField()
    maintenance_unit = models.ForeignKey(
        "MaintenanceUnit",
        on_delete=models.CASCADE,
        related_name="maintenance_work",
        null=True,
    )

    def __str__(self):
        return "%s %s" % (self.timestamp, self.events)

    class Meta:
        ordering = ["-timestamp"]


class GeometryHistory(models.Model):
    timestamp = models.DateTimeField()
    geometry = models.GeometryField(srid=DEFAULT_SRID, null=True)
    coordinates = ArrayField(ArrayField(models.FloatField()), default=list)
    events = ArrayField(models.CharField(max_length=64), default=list)
    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES, null=True)

    def __str__(self):
        return "%s %s" % (self.timestamp, self.events)

    class Meta:
        ordering = ["-timestamp"]
