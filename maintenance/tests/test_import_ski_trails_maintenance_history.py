from unittest.mock import patch

import pytest

from maintenance.models import UnitMaintenance

from .utils import get_ski_trails_maintenance_history_mock_data


@pytest.mark.django_db(transaction=True)
@patch("maintenance.management.commands.utils.get_json_data")
def test_import_ski_trails_maintenance_history(
    get_json_data_mock, unit_maintenance_geometry, units
):
    from maintenance.management.commands.import_ski_trails_maintenance_history import (
        save_maintenance_history,
    )

    json_data = get_ski_trails_maintenance_history_mock_data()
    get_json_data_mock.return_value = json_data
    save_maintenance_history(get_json_data_mock.return_value)
    # Note, the mock data contains features with invalid date, missing date, invalid location_id, these are discared
    assert len(json_data["features"]) == 4
    assert UnitMaintenance.objects.count() == 1
    um = UnitMaintenance.objects.first()
    unit_maintenance_geometry.refresh_from_db()
    assert unit_maintenance_geometry.unit_maintenance == um
    assert um.unit == units.get(id=801)
    assert um.target == UnitMaintenance.SKI_TRAIL
