from datetime import datetime, timedelta

import pytest
import pytz
from django.contrib.gis.geos import GEOSGeometry, LineString
from munigeo.models import (
    AdministrativeDivision,
    AdministrativeDivisionGeometry,
    AdministrativeDivisionType,
)
from rest_framework.test import APIClient

from maintenance.management.commands.constants import (
    AURAUS,
    INFRAROAD,
    KUNTEC,
    LIUKKAUDENTORJUNTA,
)
from maintenance.models import DEFAULT_SRID, GeometryHistory, UnitMaintenanceGeometry
from mobility_data.tests.conftest import TURKU_WKT
from services.models import Unit

UTC_TIMEZONE = pytz.timezone("UTC")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
@pytest.fixture
def geometry_historys():
    now = datetime.now(UTC_TIMEZONE)
    geometry = LineString((0, 0), (0, 50), (50, 50), (50, 0), (0, 0), sird=DEFAULT_SRID)
    GeometryHistory.objects.create(
        timestamp=now,
        geometry=geometry,
        coordinates=geometry.coords,
        provider=INFRAROAD,
        events=[AURAUS],
    )
    GeometryHistory.objects.create(
        timestamp=now - timedelta(days=1),
        geometry=geometry,
        coordinates=geometry.coords,
        provider=INFRAROAD,
        events=[AURAUS],
    )
    GeometryHistory.objects.create(
        timestamp=now - timedelta(days=2),
        geometry=geometry,
        coordinates=geometry.coords,
        provider=INFRAROAD,
        events=[LIUKKAUDENTORJUNTA],
    )
    GeometryHistory.objects.create(
        timestamp=now - timedelta(days=1),
        geometry=geometry,
        coordinates=geometry.coords,
        provider=KUNTEC,
        events=[AURAUS],
    )
    GeometryHistory.objects.create(
        timestamp=now - timedelta(days=2),
        geometry=geometry,
        coordinates=geometry.coords,
        provider=KUNTEC,
        events=[AURAUS, LIUKKAUDENTORJUNTA],
    )
    return GeometryHistory.objects.all()


@pytest.mark.django_db
@pytest.fixture
def administrative_division_type():
    adm_div_type = AdministrativeDivisionType.objects.create(
        id=1, type="muni", name="Municipality"
    )
    return adm_div_type


@pytest.mark.django_db
@pytest.fixture
def administrative_division(administrative_division_type):
    adm_div = AdministrativeDivision.objects.get_or_create(
        id=1, name="Turku", origin_id=853, type_id=1
    )
    return adm_div


@pytest.mark.django_db
@pytest.fixture
def administrative_division_geometry(administrative_division):
    turku_multipoly = GEOSGeometry(TURKU_WKT, srid=3067)
    adm_div_geom = AdministrativeDivisionGeometry.objects.create(
        id=1, division_id=1, boundary=turku_multipoly
    )
    return adm_div_geom


@pytest.fixture
def unit_maintenance_geometry():
    geometry = GEOSGeometry("LINESTRING(0 0, 1 1, 2 2)")
    return UnitMaintenanceGeometry.objects.create(geometry_id=863, geometry=geometry)


@pytest.fixture
def unit():
    now = datetime.now(UTC_TIMEZONE)
    return Unit.objects.create(
        id=801, name="Oriketo-Räntämäki -kuntorata", last_modified_time=now
    )
