from unittest.mock import patch

import pytest

from maintenance.models import UnitMaintenance

from .utils import get_ski_trails_maintenance_history_mock_data


@pytest.mark.django_db(transaction=True)
@patch("maintenance.management.commands.utils.get_json_data")
def test_import_ski_trails_maintenance_history(
    get_json_data_mock, unit_maintenance_geometries, units
):
    from maintenance.management.commands.import_ski_trails_maintenance_history import (
        save_maintenance_history,
    )

    json_data = get_ski_trails_maintenance_history_mock_data()
    get_json_data_mock.return_value = json_data
    save_maintenance_history(get_json_data_mock.return_value)
    # Note, the mock data contains features with invalid date, missing date, invalid location_id, these are discarded
    assert len(json_data["features"]) == 4
    # Only one feature has valid date and location_id (863)
    # Features with missing date, invalid date format, or invalid location_id are skipped
    assert UnitMaintenance.objects.count() == 1
    um = UnitMaintenance.objects.first()

    # Verify geometry is linked
    unit_maintenance_geometry = unit_maintenance_geometries.get(geometry_id=863)
    assert unit_maintenance_geometry.unit_maintenance == um
    assert um.geometries.count() == 1
    assert um.geometries.first().geometry_id == 863

    # geometry_id 863 -> unit_id 100863
    assert um.unit.id == 100863
    assert um.unit.name == "Oriketo-Räntämäki"
    assert um.target == UnitMaintenance.SKI_TRAIL
    # Condition should be USABLE since mock data has 'conditioned': 1
    assert um.condition == UnitMaintenance.USABLE
    assert um.maintained_at is not None
