import pytest
from django.contrib.gis.geos import Point
from django.core import management

from eco_counter import tasks as eco_tasks
from eco_counter.constants import ECO_COUNTER
from eco_counter.management.commands import utils
from eco_counter.models import Station


@pytest.mark.django_db
def test_save_stations_deletes_missing_ec_stations(monkeypatch):
    # Ensure EC station refresh persists updates (GIS fields included).
    Station.objects.create(
        name="Station to update",
        location=Point(1, 1, srid=3067),
        csv_data_source=ECO_COUNTER,
        station_id="123",
    )
    Station.objects.create(
        name="Obsolete station",
        location=Point(2, 2, srid=3067),
        csv_data_source=ECO_COUNTER,
        station_id="999",
    )

    new_location = Point(10, 10, srid=3067)
    monkeypatch.setattr(
        utils,
        "get_eco_visio_stations",
        lambda: [
            {
                "station_id": "123",
                "name": "Updated station",
                "location": new_location,
                "geometry": None,
                "data_from_date": None,
                "data_until_date": None,
            }
        ],
    )

    utils.save_stations(ECO_COUNTER)

    assert not Station.objects.filter(station_id="999").exists()
    updated = Station.objects.get(station_id="123")
    assert updated.name == "Updated station"
    assert updated.location.equals(new_location)


@pytest.mark.django_db
def test_save_stations_keeps_missing_ec_stations(monkeypatch):
    Station.objects.create(
        name="Station to update",
        location=Point(1, 1, srid=3067),
        csv_data_source=ECO_COUNTER,
        station_id="123",
    )
    Station.objects.create(
        name="Obsolete station",
        location=Point(2, 2, srid=3067),
        csv_data_source=ECO_COUNTER,
        station_id="999",
    )

    new_location = Point(10, 10, srid=3067)
    monkeypatch.setattr(
        utils,
        "get_eco_visio_stations",
        lambda: [
            {
                "station_id": "123",
                "name": "Updated station",
                "location": new_location,
                "geometry": None,
                "data_from_date": None,
                "data_until_date": None,
            }
        ],
    )

    utils.save_stations(ECO_COUNTER, delete_missing=False)

    assert Station.objects.filter(station_id="999").exists()
    updated = Station.objects.get(station_id="123")
    assert updated.name == "Updated station"
    assert updated.location.equals(new_location)


@pytest.mark.django_db
def test_refresh_command_calls_save_stations_keep_missing(monkeypatch):
    from eco_counter.management.commands import refresh_eco_visio_stations

    called = {}

    def fake_save_stations(csv_data_source, delete_missing=True):
        called["csv_data_source"] = csv_data_source
        called["delete_missing"] = delete_missing

    monkeypatch.setattr(refresh_eco_visio_stations, "save_stations", fake_save_stations)

    management.call_command("refresh_eco_visio_stations")

    assert called["csv_data_source"] == ECO_COUNTER
    assert called["delete_missing"] is False


def test_refresh_task_calls_management_command(monkeypatch):
    called = {}

    def fake_call_command(command_name, *args, **kwargs):
        called["command_name"] = command_name

    monkeypatch.setattr(eco_tasks.management, "call_command", fake_call_command)

    eco_tasks.refresh_eco_visio_stations.run()

    assert called["command_name"] == "refresh_eco_visio_stations"
