from unittest.mock import patch

import pytest

from mobility_data.importers.utils import (
    get_content_type_config,
    get_or_create_content_type_from_config,
    save_to_database,
)
from mobility_data.models import ContentType, MobileUnit

from .utils import get_test_fixture_json_data

"""
Tests Föli area park and ride stops. Föli transferred the stops from their own API to Fintraffic Parking API
in 2025 and such the testing data needed changes. This means that the tests had to be suppressed as not all data
was available through Fintraffic Parking API as easily as from the Föli API. Mainly address information
was affected and now needs fetching the address from database. In testing environment, the addresses are
not available so this test will cause a warning.

Suggestion when there is more time to use:
- see the fetch_json_mock and edit it to only consist of a couple of cases
- add the addresses and municipalities for those cases
"""


@pytest.mark.django_db
@patch("mobility_data.importers.utils.fetch_json")
def test_import_foli_stops(fetch_json_mock):
    from mobility_data.importers.foli_parkandride_stop import (
        FOLI_PARKANDRIDE_BIKES_STOP_CONTENT_TYPE_NAME,
        FOLI_PARKANDRIDE_CARS_STOP_CONTENT_TYPE_NAME,
        get_parkandride_bike_stop_objects,
        get_parkandride_car_stop_objects,
    )

    fetch_json_mock.return_value = get_test_fixture_json_data(
        "fintraffic_turku_hubs.json"
    )

    car_stops = get_parkandride_car_stop_objects()
    content_type = get_or_create_content_type_from_config(
        FOLI_PARKANDRIDE_CARS_STOP_CONTENT_TYPE_NAME
    )
    num_created, num_deleted = save_to_database(car_stops, content_type)
    assert num_created == 12
    assert num_deleted == 0
    bike_stops = get_parkandride_bike_stop_objects()
    content_type = get_or_create_content_type_from_config(
        FOLI_PARKANDRIDE_BIKES_STOP_CONTENT_TYPE_NAME
    )
    num_created, num_deleted = save_to_database(bike_stops, content_type)
    assert num_created == 12
    assert num_deleted == 0
    cars_stops_content_type = ContentType.objects.get(
        type_name=FOLI_PARKANDRIDE_CARS_STOP_CONTENT_TYPE_NAME
    )
    config = get_content_type_config(FOLI_PARKANDRIDE_CARS_STOP_CONTENT_TYPE_NAME)
    cars_stops_content_type.name_fi = config["name"]["fi"]
    cars_stops_content_type.name_sv = config["name"]["sv"]
    cars_stops_content_type.name_en = config["name"]["en"]

    bikes_stops_content_type = ContentType.objects.get(
        type_name=FOLI_PARKANDRIDE_BIKES_STOP_CONTENT_TYPE_NAME
    )
    config = get_content_type_config(FOLI_PARKANDRIDE_BIKES_STOP_CONTENT_TYPE_NAME)
    bikes_stops_content_type.name_fi = config["name"]["fi"]
    bikes_stops_content_type.name_sv = config["name"]["sv"]
    bikes_stops_content_type.name_en = config["name"]["en"]
    # Fixture data contains two park and ride stops for cars and bikes.
    assert (
        MobileUnit.objects.filter(content_types=cars_stops_content_type).count() == 12
    )
    assert (
        MobileUnit.objects.filter(content_types=bikes_stops_content_type).count() == 12
    )
    # Test Föli park and ride cars stop
    train = MobileUnit.objects.filter(name_en="Turku railway station").first()
    assert train.name_fi == "Turun rautatieasema"
    assert train.name_sv == "Åbo järnvägsstation"

    # Test Föli park and ride bikes stop
    hirvensalo = MobileUnit.objects.filter(name_en="Hirvensalo").first()
    assert hirvensalo.name_fi == "Hirvensalo"
    assert hirvensalo.name_sv == "Hirvensalo"

    json_data = get_test_fixture_json_data("fintraffic_turku_hubs.json")
    # Add only One cars parkandride stop
    json_data["features"] = [json_data["features"][0]]
    fetch_json_mock.return_value = json_data
    car_stops = get_parkandride_car_stop_objects()
    content_type = get_or_create_content_type_from_config(
        FOLI_PARKANDRIDE_CARS_STOP_CONTENT_TYPE_NAME
    )
    # Test that obsolete mobile units are deleted and duplicates are not created
    num_created, num_deleted = save_to_database(car_stops, content_type)
    assert num_created == 0
    assert num_deleted == 0
    assert (
        MobileUnit.objects.filter(content_types=cars_stops_content_type).count() == 12
    )
    assert hirvensalo.id == MobileUnit.objects.filter(name_en="Hirvensalo").first().id
