import json
from unittest.mock import patch

import pytest

from maintenance.models import SPORT_NAMES_UNIT_EXTRA_KEY, UnitMaintenance

from .utils import get_ski_trails_maintenance_history_mock_data


def test_parse_trilingual_name():
    from maintenance.management.commands.utils import parse_trilingual_name

    assert parse_trilingual_name(None) == ("", "", "")
    assert parse_trilingual_name("  ") == ("", "", "")
    assert parse_trilingual_name("Yksi") == ("Yksi", "Yksi", "Yksi")
    assert parse_trilingual_name("fi|sv") == ("fi", "sv", "fi")
    assert parse_trilingual_name("fi|sv|en") == ("fi", "sv", "en")


def test_sanitize_maintenance_condition_note():
    from maintenance.management.commands.utils import (
        sanitize_maintenance_condition_note,
    )

    assert sanitize_maintenance_condition_note(None) is None
    assert sanitize_maintenance_condition_note("") is None
    assert sanitize_maintenance_condition_note("null") is None
    assert sanitize_maintenance_condition_note("NULL") is None
    assert sanitize_maintenance_condition_note(" null ") is None
    assert (
        sanitize_maintenance_condition_note("null<attention>null</attention>") is None
    )
    assert sanitize_maintenance_condition_note("Latu ok") == "Latu ok"
    assert sanitize_maintenance_condition_note("annulloida") == "annulloida"


def test_merge_ski_trail_unit_description_condition_note_json_null():
    from maintenance.management.commands.utils import merge_ski_trail_unit_description

    out = merge_ski_trail_unit_description(
        None, condition_note="null<attention>null</attention>"
    )
    assert json.loads(out)["condition_note"] is None


def test_merge_ski_trail_unit_description_sanitizes_stored_note_without_overwrite():
    from maintenance.management.commands.utils import merge_ski_trail_unit_description

    existing = json.dumps(
        {
            "length": "1",
            "lights": "",
            "condition_note": "null<attention>null</attention>",
        }
    )
    out = merge_ski_trail_unit_description(existing, condition_note=None)
    data = json.loads(out)
    assert data["condition_note"] is None
    assert data["length"] == "1"


@pytest.mark.django_db(transaction=True)
@patch("maintenance.management.commands.utils.get_json_data")
def test_ski_maintenance_does_not_overwrite_trilingual_names(
    get_json_data_mock, unit_maintenance_geometries
):
    """Ski geometry import owns piped names; maintenance must not replace sv/en."""
    from django.utils import timezone

    from maintenance.management.commands.import_ski_trails_maintenance_history import (
        save_maintenance_history,
    )
    from maintenance.management.commands.utils import (
        apply_sport_facility_trilingual_names,
    )
    from services.models import Unit

    unit = Unit(id=100863, last_modified_time=timezone.now())
    apply_sport_facility_trilingual_names(unit, "FiOnly", "SvOnly", "EnOnly")
    unit.save()

    json_data = get_ski_trails_maintenance_history_mock_data()
    get_json_data_mock.return_value = json_data
    save_maintenance_history(get_json_data_mock.return_value)

    unit.refresh_from_db()
    assert unit.name_fi == "FiOnly"
    assert unit.name_sv == "SvOnly"
    assert unit.name_en == "EnOnly"
    assert unit.extra[SPORT_NAMES_UNIT_EXTRA_KEY] == {
        "fi": "FiOnly",
        "sv": "SvOnly",
        "en": "EnOnly",
    }


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
    assert um.unit.name_fi == "Oriketo-Räntämäki"
    assert um.unit.name_sv == "Oriketo-Räntämäki"
    assert um.unit.name_en == "Oriketo-Räntämäki"
    assert um.unit.extra[SPORT_NAMES_UNIT_EXTRA_KEY] == {
        "fi": "Oriketo-Räntämäki",
        "sv": "Oriketo-Räntämäki",
        "en": "Oriketo-Räntämäki",
    }
    desc = json.loads(um.unit.description)
    assert desc == {
        "length": "1,5",
        "lights": "6-22",
        "condition_note": "Latu ok",
    }
    assert um.target == UnitMaintenance.SKI_TRAIL
    # Condition should be USABLE since mock data has 'conditioned': 1
    assert um.condition == UnitMaintenance.USABLE
    assert um.maintained_at is not None
