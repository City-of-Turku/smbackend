from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.geos import GEOSGeometry, LineString, Point
from rest_framework import serializers

from services.models import Unit

from ...models import GroupType, MobileUnit, MobileUnitGroup
from . import ContentTypeSerializer


class GeometrySerializer(serializers.Serializer):

    x = serializers.FloatField()
    y = serializers.FloatField()

    class Meta:
        fields = "__all__"


class GrouptTypeBasicInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupType
        fields = ["id", "name", "type_name"]


class MobileUnitGroupBasicInfoSerializer(serializers.ModelSerializer):

    group_type = GrouptTypeBasicInfoSerializer(many=False, read_only=True)

    class Meta:
        model = MobileUnitGroup
        fields = ["id", "name", "group_type"]


class MobileUnitSerializer(serializers.ModelSerializer):

    content_type = ContentTypeSerializer(many=False, read_only=True)
    mobile_unit_group = MobileUnitGroupBasicInfoSerializer(many=False, read_only=True)
    geometry_coords = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MobileUnit
        fields = [
            "id",
            "name",
            "name_fi",
            "name_sv",
            "name_en",
            "address",
            "address_fi",
            "address_sv",
            "address_en",
            "description",
            "description_fi",
            "description_sv",
            "description_en",
            "content_type",
            "mobile_unit_group",
            "is_active",
            "created_time",
            "geometry",
            "geometry_coords",
            "extra",
        ]

    def to_representation(self, obj):
        representation = super().to_representation(obj)
        # If mobile_unit has a unit_id we serialize the data from the services_unit table.
        unit_id = obj.unit_id
        if unit_id:
            unit = Unit.objects.get(id=unit_id)
            for field in self.fields:
                if hasattr(unit, field):
                    representation[field] = getattr(unit, field)
            if unit.location:
                representation["geometry"] = unit.location.wkt
        return representation

    def get_geometry_coords(self, obj):
        # If stored to Unit table, retrieve geometry from there.
        if obj.unit_id:
            geometry = Unit.objects.get(id=obj.unit_id).location
        else:
            geometry = obj.geometry
        if isinstance(geometry, GEOSGeometry):
            srid = self.context["srid"]
            if srid:
                try:
                    geometry.transform(srid)
                except GDALException:
                    return "Invalid SRID given as parameter for transformation."
        if isinstance(geometry, Point):
            pos = {}
            if self.context["latlon"] is True:
                pos["lat"] = geometry.y
                pos["lon"] = geometry.x
            else:
                pos["lon"] = geometry.x
                pos["lat"] = geometry.y
            return pos

        elif isinstance(geometry, LineString):
            if self.context["latlon"] is True:
                # Return LineString coordinates in (lat,lon) format
                coords = []
                for coord in geometry.coords:
                    # swap lon,lat -> lat lon
                    e = (coord[1], coord[0])
                    coords.append(e)
                return coords
            else:
                return geometry.coords
        else:
            return ""
