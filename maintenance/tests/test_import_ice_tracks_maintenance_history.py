from datetime import datetime
from unittest.mock import patch

import pytest

from maintenance.management.commands.constants import ICE_TRACKS_DATE_FIELD_FORMAT
from maintenance.models import UnitMaintenance

from .utils import get_ice_tracks_maintenance_history_mock_data


@pytest.mark.django_db(transaction=True)
@patch("maintenance.management.commands.utils.get_json_data")
def test_import_ice_tracks_maintenance_history(
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
    # New logic creates one UnitMaintenance per geometry_id (id field)
    assert UnitMaintenance.objects.count() == 3

    # id 928: conditioned=true -> USABLE
    # id 929: conditioned=false -> UNUSABLE
    # id 930: conditioned=false -> UNUSABLE
    assert (
        UnitMaintenance.objects.filter(condition=UnitMaintenance.UNUSABLE).count() == 2
    )
    assert UnitMaintenance.objects.filter(condition=UnitMaintenance.USABLE).count() == 1

    # Test USABLE ice track (id 928)
    um1 = UnitMaintenance.objects.filter(condition=UnitMaintenance.USABLE).first()
    assert um1.target == UnitMaintenance.ICE_TRACK
    # geometry_id 928 -> unit_id 100928
    assert um1.unit.id == 100928
    assert um1.unit.name == "Frantsinkenttä"
    assert um1.unit.street_address == "Prelaatinpolku 7"
    assert um1.unit.address_zip == "20540"
    assert um1.maintained_at == TIMEZONE.localize(
        datetime.strptime("2024-10-04 14:30:06", ICE_TRACKS_DATE_FIELD_FORMAT)
    )
    assert um1.geometries.count() == 1
    assert (
        um1.geometries.first().geometry.wkt
        == "POINT (22.316604400000024 60.47026100000005)"
    )
    assert um1.geometries.first().geometry_id == 928

    # Test UNUSABLE ice track (id 929)
    um2 = UnitMaintenance.objects.filter(
        condition=UnitMaintenance.UNUSABLE, unit__id=100929
    ).first()
    assert um2 is not None
    assert um2.unit.id == 100929
    assert um2.unit.name == "Purokadun kenttä"
    assert um2.maintained_at is None

    # Test that no duplicates are created and imported instances are preserved
    save_maintenance_history(get_json_data_mock.return_value)
    assert len(json_data["features"]) == 3
    assert UnitMaintenance.objects.count() == 3
    um1_after = UnitMaintenance.objects.filter(condition=UnitMaintenance.USABLE).first()
    assert um1.id == um1_after.id  # Same instance preserved
