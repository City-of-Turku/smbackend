from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.gdal import SpatialReference
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Q
from munigeo import api as munigeo_api
from rest_framework import viewsets
from rest_framework.exceptions import ParseError

from services.api_pagination import Pagination
from services.utils import strtobool

from ..models import BicycleNetwork, BicycleNetworkPart
from .serializers import (
    BicycleNetworkPartCoordsSerializer,
    BicycleNetworkPartSerializer,
    BicycleNetworkSerializer,
)


class LargeResultsSetPagination(Pagination):
    """
    Custom pagination class to allow all results in one page.
    """

    max_page_size = 15_000


class BicycleNetworkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BicycleNetwork.objects.all()
    serializer_class = BicycleNetworkSerializer


class BicycleNetworkPartViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BicycleNetworkPart.objects.all()
    serializer_class = BicycleNetworkPartSerializer
    pagination_class = LargeResultsSetPagination

    def list(self, request):
        queryset = BicycleNetworkPart.objects.all()
        filters = self.request.query_params
        latlon = False
        only_coords = False
        if "id" in filters:
            queryset = queryset.filter(bicycle_network__id=filters.get("id", None))

        if "name" in filters:
            queryset = queryset.filter(bicycle_network__name=filters.get("name", None))
        if "latlon" in filters:
            try:
                latlon = strtobool(filters["latlon"])
            except ValueError:
                raise ParseError("'latlon' needs to be a boolean")

        if "only_coords" in filters:
            try:
                only_coords = strtobool(filters["only_coords"])
            except ValueError:
                raise ParseError("'only_coords' needs to be a boolean")

        # Return elements that are inside radius (distance) of location (lat,lon)
        if "lat" in filters and "lon" in filters:
            try:
                lat = float(filters["lat"])
                lon = float(filters["lon"])
            except ValueError:
                raise ParseError("'lat' and 'lon' need to be floating point numbers")
            point = Point(lon, lat, srid=4326)
            if "distance" in filters:
                try:
                    distance = float(filters["distance"])
                    if not distance > 0:
                        raise ValueError()
                except ValueError:
                    raise ParseError("'distance' needs to be a floating point number")
                queryset = queryset.filter(
                    geometry__distance_lte=(point, D(m=distance))
                )
            queryset = queryset.annotate(distance=Distance("geometry", point)).order_by(
                "distance"
            )
        # Return elements that are inside bbox
        if "bbox" in filters:
            val = filters.get("bbox", None)
            if val:
                ref = SpatialReference(filters.get("bbox_srid", 4326))
                bbox_geometry_filter = munigeo_api.build_bbox_filter(
                    ref, val, "geometry"
                )
                queryset = queryset.filter(Q(**bbox_geometry_filter))

        page = self.paginate_queryset(queryset)
        if only_coords:
            serializer = BicycleNetworkPartCoordsSerializer(
                page, many=True, context={"latlon": latlon}
            )
        else:
            serializer = BicycleNetworkPartSerializer(
                page, many=True, context={"latlon": latlon}
            )
        return self.get_paginated_response(serializer.data)
