from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.reverse import reverse

from maintenance.management.commands.constants import (
    AURAUS,
    INFRAROAD,
    KUNTEC,
    LIUKKAUDENTORJUNTA,
    SKI_TRAILS_DATE_FIELD_FORMAT,
    START_DATE_TIME_FORMAT,
)
from maintenance.models import UnitMaintenance


@pytest.mark.django_db
def test_unit_maintenance_geometry_list(api_client, unit_maintenance_geometries):
    url = reverse("maintenance:unit_maintenance_geometry-list")
    response = api_client.get(url)
    assert response.json()["count"] == 2
    unit_maintenance = response.json()["results"][0]
    assert unit_maintenance.keys() == {
        "id",
        "geometry",
        "geometry_id",
        "unit_maintenance",
    }


@pytest.mark.django_db
def test_unit_maintenance_list(api_client, unit_maintenances):
    url = reverse("maintenance:unit_maintenance-list")
    response = api_client.get(url)
    assert response.json()["count"] == 2
    unit_maintenance = response.json()["results"][0]
    assert unit_maintenance.keys() == {
        "id",
        "unit",
        "target",
        "condition",
        "maintained_at",
        "last_imported_time",
        "geometries",
    }


@pytest.mark.django_db
def test_unit_maintenance_list_unit_parameter(api_client, unit_maintenances):
    url = reverse("maintenance:unit_maintenance-list") + "?unit=801"
    response = api_client.get(url)
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["unit"] == 801


@pytest.mark.django_db
def test_unit_maintenance_list_target_parameter(api_client, unit_maintenances):
    url = (
        reverse("maintenance:unit_maintenance-list")
        + f"?target__iexact={UnitMaintenance.SKI_TRAIL}"
    )
    response = api_client.get(url)
    assert response.json()["count"] == 2
    assert response.json()["results"][0]["target"] == UnitMaintenance.SKI_TRAIL
    assert response.json()["results"][1]["target"] == UnitMaintenance.SKI_TRAIL


@pytest.mark.django_db
def test_unit_maintenance_list_maintained_at_parameter(
    api_client, now, unit_maintenances
):
    url = (
        reverse("maintenance:unit_maintenance-list")
        + f"?maintained_at__gte={now.strftime(SKI_TRAILS_DATE_FIELD_FORMAT)}"
    )
    response = api_client.get(url)
    assert response.json()["results"][0]["unit"] == 801
    url = (
        reverse("maintenance:unit_maintenance-list")
        + f"?maintained_at__lte={now.strftime(SKI_TRAILS_DATE_FIELD_FORMAT)}"
    )
    response = api_client.get(url)
    assert response.json()["results"][0]["unit"] == 784


@pytest.mark.django_db
def test_geometry_history_list(api_client, geometry_historys):
    url = reverse("maintenance:geometry_history-list")
    response = api_client.get(url)
    assert response.json()["count"] == 5


@pytest.mark.django_db
def test_geometry_history_list_provider_parameter(api_client, geometry_historys):
    url = reverse("maintenance:geometry_history-list") + f"?provider={KUNTEC}"
    response = api_client.get(url)
    # Fixture data contains 2 KUNTEC GeometryHistroy rows
    assert response.json()["count"] == 2


@pytest.mark.django_db
def test_geometry_history_list_event_parameter(api_client, geometry_historys):
    url = reverse("maintenance:geometry_history-list") + f"?event={AURAUS}"
    response = api_client.get(url)
    # 3 INFRAROAD AURAUS events and 1 KUNTEC
    assert response.json()["count"] == 4


@pytest.mark.django_db
def test_geometry_history_list_event_and_provider_parameter(
    api_client, geometry_historys
):
    url = (
        reverse("maintenance:geometry_history-list")
        + f"?provider={KUNTEC}&event={LIUKKAUDENTORJUNTA}"
    )
    response = api_client.get(url)
    assert response.json()["count"] == 1


@pytest.mark.django_db
def test_geometry_history_list_start_date_time_parameter(api_client, geometry_historys):
    start_date_time = timezone.now() - timedelta(hours=1)
    url = (
        reverse("maintenance:geometry_history-list")
        + f"?start_date_time={start_date_time.strftime(START_DATE_TIME_FORMAT)}"
    )
    response = api_client.get(url)
    assert response.json()["count"] == 1
    geometry_history = response.json()["results"][0]
    assert geometry_history["geometry_type"] == "LineString"
    assert geometry_history["provider"] == INFRAROAD
    start_date_time = timezone.now() - timedelta(days=1, hours=2)
    url = (
        reverse("maintenance:geometry_history-list")
        + f"?start_date_time={start_date_time.strftime(START_DATE_TIME_FORMAT)}"
    )
    response = api_client.get(url)
    assert response.json()["count"] == 3
