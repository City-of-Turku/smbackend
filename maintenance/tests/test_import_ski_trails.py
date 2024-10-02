from unittest.mock import patch

import pytest
from django.contrib.gis.geos import LineString

from maintenance.models import UnitMaintenanceGeometry
from maintenance.tests.utils import get_test_fixture_data_layer


@pytest.mark.django_db(transaction=True)
@patch("maintenance.management.commands.utils.get_data_layer")
def test_import_skitrails(
    get_data_layer_mock,
):
    from maintenance.management.commands.import_ski_trails import save_trails

    get_data_layer_mock.return_value = get_test_fixture_data_layer("ski_trails.geojson")
    num_created, num_updated = save_trails(get_data_layer_mock.return_value)
    assert num_created == 1
    assert num_updated == 0
    assert UnitMaintenanceGeometry.objects.count() == 1
    umg = UnitMaintenanceGeometry.objects.first()
    assert umg.geometry_id == 863
    assert umg.geometry.srid == 4326
    assert len(umg.geometry) == 31
    assert isinstance(umg.geometry, LineString) is True
    # Test geometry update
    get_data_layer_mock.return_value = get_test_fixture_data_layer(
        "ski_trails_geometry_change.geojson"
    )
    num_created, num_updated = save_trails(get_data_layer_mock.return_value)
    assert num_created == 0
    assert num_updated == 1
    assert UnitMaintenanceGeometry.objects.count() == 1
    umg_updated = UnitMaintenanceGeometry.objects.first()
    assert umg.id == umg_updated.id
    assert umg_updated.geometry_id == 863
    assert umg_updated.geometry.srid == 4326
    assert len(umg_updated.geometry) == 30
    assert isinstance(umg_updated.geometry, LineString) is True
