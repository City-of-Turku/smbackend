import json

from django.contrib.gis.geos import LineString, Point
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from maintenance.models import (
    GeometryHistory,
    MaintenanceUnit,
    MaintenanceWork,
    SPORT_NAMES_UNIT_EXTRA_KEY,
    UnitMaintenance,
    UnitMaintenanceGeometry,
)


class UnitMaintenanceGeometrySerializer(serializers.ModelSerializer):

    class Meta:
        model = UnitMaintenanceGeometry
        fields = ["id", "geometry", "geometry_id", "unit_maintenance"]

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        # DRF doesn't serialize GeometryField by default, so we need to handle it manually
        # Convert geometry to GeoJSON format
        if instance.geometry:
            # Ensure geometry is in SRID 4326 (GeoJSON standard)
            geom = instance.geometry
            if geom.srid and geom.srid != 4326:
                geom = geom.clone()
                geom.transform(4326)

            # Convert to GeoJSON using Django's built-in geojson property
            try:
                ret["geometry"] = json.loads(geom.geojson)
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error converting geometry to GeoJSON: {e}")
                ret["geometry"] = None
        else:
            ret["geometry"] = None

        # If nested in UnitMaintenanceSerializer
        if (
            self.context.get("request", False)
            and "/maintenance/unit_maintenance/" in self.context.get("request", "").path
        ):
            ret.pop("unit_maintenance", None)
        return ret


class UnitInfoSerializer(serializers.Serializer):
    """Serializer for Unit information nested in UnitMaintenance"""

    id = serializers.IntegerField()
    name = serializers.CharField()
    name_fi = serializers.SerializerMethodField()
    name_sv = serializers.SerializerMethodField()
    name_en = serializers.SerializerMethodField()
    description = serializers.CharField(allow_null=True, required=False)
    street_address = serializers.CharField(allow_null=True, required=False)
    address_zip = serializers.CharField(allow_null=True, required=False)

    def _sport_names(self, obj):
        if not obj.extra:
            return None
        sn = obj.extra.get(SPORT_NAMES_UNIT_EXTRA_KEY)
        return sn if isinstance(sn, dict) else None

    def get_name_fi(self, obj):
        if getattr(obj, "name_fi", None):
            return obj.name_fi
        sn = self._sport_names(obj)
        if sn and sn.get("fi"):
            return sn["fi"]
        return obj.name

    def get_name_sv(self, obj):
        if getattr(obj, "name_sv", None):
            return obj.name_sv
        sn = self._sport_names(obj)
        if sn and sn.get("sv"):
            return sn["sv"]
        return obj.name

    def get_name_en(self, obj):
        if getattr(obj, "name_en", None):
            return obj.name_en
        sn = self._sport_names(obj)
        if sn and sn.get("en"):
            return sn["en"]
        return obj.name


class UnitMaintenanceSerializer(serializers.ModelSerializer):
    geometries = UnitMaintenanceGeometrySerializer(many=True, read_only=True)
    unit = serializers.SerializerMethodField()

    class Meta:
        model = UnitMaintenance
        fields = [
            "id",
            "unit",
            "target",
            "condition",
            "maintained_at",
            "last_imported_time",
            "geometries",
        ]

    def get_unit(self, obj):
        """Return Unit information as an object if unit exists"""
        if obj.unit:
            return UnitInfoSerializer(obj.unit).data
        return None


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
            # Removed for performance issues as it is not currently used
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
