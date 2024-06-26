from django.contrib.gis.geos import LineString, Point
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from street_maintenance.models import GeometryHistory, MaintenanceUnit, MaintenanceWork


class GeometryHistorySerializer(serializers.ModelSerializer):
    geometry_type = serializers.SerializerMethodField()

    class Meta:
        model = GeometryHistory
        fields = [
            "id",
            "geometry_type",
            "events",
            "timestamp",
            "provider",
            # Removed for permormance issues as it is not currently used
            # "geometry",
            "coordinates",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_geometry_type(self, obj):
        return obj.geometry.geom_type


class ActiveEventSerializer(serializers.Serializer):
    events = serializers.CharField(max_length=64)


class MaintenanceUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceUnit
        fields = "__all__"


class MaintenanceWorkSerializer(serializers.ModelSerializer):
    provider = serializers.PrimaryKeyRelatedField(
        many=False, source="maintenance_unit.provider", read_only=True
    )

    class Meta:
        model = MaintenanceWork
        fields = [
            "id",
            "maintenance_unit",
            "provider",
            "geometry",
            "timestamp",
            "events",
            "original_event_names",
        ]

    def to_representation(self, obj):
        representation = super().to_representation(obj)
        if isinstance(obj.geometry, Point):
            representation["lat"] = obj.geometry.y
            representation["lon"] = obj.geometry.x
        elif isinstance(obj.geometry, LineString):
            representation["coords"] = obj.geometry.coords
        return representation
