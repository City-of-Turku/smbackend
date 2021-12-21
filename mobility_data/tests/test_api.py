import pytest
from rest_framework.reverse import reverse
from django.conf import settings
from django.contrib.gis.geos import Point
from mobility_data.tests.fixtures import *

@pytest.mark.django_db
def test_content_type(api_client, content_type):
    url = reverse("mobility_data:content_types-list")
    response = api_client.get(url)
    assert response.status_code == 200
    results = response.json()["results"][0]
    assert results["type_name"] == "TTT"
    assert results["name"] == "test"
    assert results["description"] == "test content type"

@pytest.mark.django_db
def test_group_type(api_client, group_type):
    url = reverse("mobility_data:group_types-list")
    response = api_client.get(url)
    assert response.status_code == 200
    results = response.json()["results"][0]
    assert results["type_name"] == "TGT"
    assert results["name"] == "test group"
    assert results["description"] == "test group type"

@pytest.mark.django_db
def test_mobile_unit(api_client, mobile_unit, content_type):
    url = reverse("mobility_data:mobile_units-list")
    response = api_client.get(url)
    assert response.status_code == 200
    results = response.json()["results"][0]
    assert results["name"] == "Test mobileunit"
    assert results["description"] == "Test description"
    assert results["content_type"]["id"] == str(content_type.id)
    assert results["extra"]["test"] == "4242"
    assert results["geometry"] == Point(42.42, 21.21, srid=settings.DEFAULT_SRID)

@pytest.mark.django_db
def test_mobile_unit_group(api_client, mobile_unit_group, group_type):
    url = reverse("mobility_data:mobile_unit_groups-list")
    response = api_client.get(url)
    assert response.status_code == 200
    results = response.json()["results"][0]
    assert results["name"] == "Test mobileunitgroup"
    assert results["description"] == "Test description"
    assert results["group_type"]["id"] == str(group_type.id)