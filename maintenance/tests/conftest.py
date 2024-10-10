from datetime import datetime, timedelta

import pytest
from django.contrib.gis.geos import GEOSGeometry, LineString
from django.utils import timezone
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
from maintenance.models import (
    DEFAULT_SRID,
    GeometryHistory,
    UnitMaintenance,
    UnitMaintenanceGeometry,
)
from mobility_data.tests.conftest import TURKU_WKT
from services.models import Unit


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def now():
    return datetime.now().replace(tzinfo=timezone.get_default_timezone())


@pytest.mark.django_db
@pytest.fixture
def geometry_historys(now):
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
def unit_maintenance_geometries():
    geometry = GEOSGeometry("LINESTRING(0 0, 1 1, 2 2)")
    UnitMaintenanceGeometry.objects.create(geometry_id=863, geometry=geometry)
    UnitMaintenanceGeometry.objects.create(geometry_id=864, geometry=geometry)
    return UnitMaintenanceGeometry.objects.all()


@pytest.fixture
def units(now):
    Unit.objects.create(
        id=801, name="Oriketo-Räntämäki -kuntorata", last_modified_time=now
    )
    Unit.objects.create(id=784, name="Härkämäen kuntorata", last_modified_time=now)
    Unit.objects.create(id=462, name="Frantsinkenttä", last_modified_time=now)
    Unit.objects.create(
        id=767, name="Pienpelikokoinen hiekkakenttä", last_modified_time=now
    )
    return Unit.objects.all()


@pytest.fixture
def unit_maintenances(now, units):
    UnitMaintenance.objects.create(
        target=UnitMaintenance.SKI_TRAIL,
        unit=units.get(id=801),
        last_imported_time=now,
        maintained_at=now + timedelta(days=1),
    )
    UnitMaintenance.objects.create(
        target=UnitMaintenance.SKI_TRAIL,
        unit=units.get(id=784),
        last_imported_time=now,
        maintained_at=now - timedelta(days=1),
    )
    return UnitMaintenance.objects.all()
