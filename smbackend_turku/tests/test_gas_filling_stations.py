import logging
from datetime import datetime
from unittest.mock import patch

import pytest
import pytz

from mobility_data.tests.utils import get_test_fixture_json_data
from services.models import Service, ServiceNode, Unit
from smbackend_turku.importers.stations import import_gas_filling_stations
from smbackend_turku.importers.utils import get_external_source_config
from smbackend_turku.tests.utils import create_municipalities


@pytest.mark.django_db
@patch("mobility_data.importers.gas_filling_station.get_json_data")
def test_gas_filling_stations_import(get_json_data_mock):

    logger = logging.getLogger(__name__)
    # For reasons unknown this mock does not work,
    # The return value of the actual function call is used.
    get_json_data_mock.return_value = get_test_fixture_json_data(
        "gas_filling_stations.json"
    )
    config = get_external_source_config("gas_filling_stations")
    utc_timezone = pytz.timezone("UTC")
    # create root servicenode to which the imported service_node will connect
    root_service_node = ServiceNode.objects.create(
        id=42, name="Vapaa-aika", last_modified_time=datetime.now(utc_timezone)
    )
    # Municipality must be created in order to update_service_node_count()
    # to execute without errors
    create_municipalities()
    import_gas_filling_stations(
        logger=logger,
        config=config,
    )
    service = Service.objects.get(name=config["service"]["name"]["fi"])
    assert service.id == config["service"]["id"]
    service_node = ServiceNode.objects.get(name=config["service_node"]["name"]["fi"])
    assert service_node.id == config["service_node"]["id"]
    assert service_node.parent.id == root_service_node.id
    # See line 20, commented as the mock does not work.
    assert Unit.objects.all().count() == 2
    assert Unit.objects.all()[1].id == config["units_offset"]
    assert Unit.objects.get(name="Raisio Kuninkoja")
    unit = Unit.objects.get(name="Turku Satama")
    assert pytest.approx(unit.location.x, 0.0000000001) == 236760.1062021295
    assert unit.extra["operator"] == "Gasum"
    assert unit.service_nodes.all().count() == 1
    assert unit.services.all().count() == 1
    assert unit.services.first().name == config["service"]["name"]["fi"]
    assert unit.service_nodes.first().name == config["service_node"]["name"]["fi"]
