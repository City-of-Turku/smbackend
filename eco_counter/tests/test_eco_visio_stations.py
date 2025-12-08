"""
Unit tests for Eco-Visio station import helpers.
"""

from django.conf import settings

from eco_counter.management.commands import utils


class DummyEcoVisioClient:
    """Minimal Eco-Visio client stub for testing."""

    def __init__(self, sites, include_recorder):
        self.sites = sites
        self.include_recorder = include_recorder

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def get_all_sites(self, include=None):
        self.include_recorder["include"] = include
        return self.sites


class TestGetEcoVisioStations:
    """Tests for get_eco_visio_stations."""

    def test_maps_fields_and_filters_to_region(self, monkeypatch):
        """Valid site is transformed with geometry, dates, and correct SRID."""
        include_recorder = {}
        sites = [
            {
                "id": 123,
                "name": "Test Station",
                "location": {"lat": 60.45, "lon": 22.27},
                "segments": {
                    "type": "LineString",
                    "coordinates": [[22.27, 60.45], [22.28, 60.46]],
                },
                "firstData": "2024-01-01T00:00:00Z",
                "lastData": "2024-06-01T12:00:00Z",
            }
        ]
        monkeypatch.setattr(
            utils,
            "EcoVisioAPIClient",
            lambda: DummyEcoVisioClient(sites, include_recorder),
        )
        monkeypatch.setattr(
            utils,
            "locates_in_south_western_finland",
            lambda point: True,
        )

        stations = utils.get_eco_visio_stations()

        assert include_recorder["include"] == ["segments"]
        assert len(stations) == 1
        station = stations[0]
        assert station["station_id"] == "123"
        assert station["name"] == "Test Station"
        assert station["location"].srid == settings.DEFAULT_SRID
        assert station["geometry"] is not None
        assert station["geometry"].srid == settings.DEFAULT_SRID
        assert station["data_from_date"].isoformat() == "2024-01-01"
        assert station["data_until_date"].isoformat() == "2024-06-01"

    def test_filters_outside_region_and_invalid_coords(self, monkeypatch):
        """Sites outside region or without coordinates are skipped."""
        include_recorder = {}
        sites = [
            {
                "id": 1,
                "name": "Outside",
                "location": {"lat": 60.0, "lon": 22.0},
                "segments": None,
                "firstData": None,
                "lastData": None,
            },
            {
                "id": 2,
                "name": "Missing coords",
                "location": {"lat": None, "lon": None},
            },
        ]
        monkeypatch.setattr(
            utils,
            "EcoVisioAPIClient",
            lambda: DummyEcoVisioClient(sites, include_recorder),
        )
        monkeypatch.setattr(
            utils,
            "locates_in_south_western_finland",
            lambda point: False,
        )

        stations = utils.get_eco_visio_stations()

        assert include_recorder["include"] == ["segments"]
        assert stations == []
