from datetime import datetime
from unittest.mock import patch

import pytest

from maintenance.management.commands.constants import ICE_TRACKS_DATE_FIELD_FORMAT
from maintenance.models import UnitMaintenance

from .utils import get_ice_tracks_maintenance_history_mock_data


@pytest.mark.django_db(transaction=True)
@patch("maintenance.management.commands.utils.get_json_data")
def test_import_ski_trails_maintenance_history(
    get_json_data_mock, unit_maintenance_geometries, units
):
    from maintenance.management.commands.import_ice_tracks_maintenance_history import (
        save_maintenance_history,
        TIMEZONE,
    )

    json_data = get_ice_tracks_maintenance_history_mock_data()
    get_json_data_mock.return_value = json_data
    save_maintenance_history(get_json_data_mock.return_value)
    assert len(json_data["features"]) == 3
    assert UnitMaintenance.objects.count() == 2

    assert (
        UnitMaintenance.objects.filter(condition=UnitMaintenance.UNUSABLE).count() == 1
    )
    assert UnitMaintenance.objects.filter(condition=UnitMaintenance.USABLE).count() == 1

    um1 = UnitMaintenance.objects.filter(condition=UnitMaintenance.USABLE).first()
    assert um1.target == UnitMaintenance.ICE_TRACK
    assert um1.unit.id == 462
    assert um1.maintained_at == TIMEZONE.localize(
        datetime.strptime("2024-10-04 14:30:06", ICE_TRACKS_DATE_FIELD_FORMAT)
    )
    assert (
        um1.geometries.first().geometry.wkt
        == "POINT (22.316604400000024 60.47026100000005)"
    )
    # Test that no duplicates are created and imported instanced are preserved
    save_maintenance_history(get_json_data_mock.return_value)
    assert len(json_data["features"]) == 3
    assert UnitMaintenance.objects.count() == 2
    um2 = UnitMaintenance.objects.filter(condition=UnitMaintenance.USABLE).first()
    assert um1 == um2
