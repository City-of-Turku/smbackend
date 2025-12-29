"""
Unit tests for Eco-Visio station import helpers.
"""

from django.conf import settings

from eco_counter.management.commands import utils


class DummyEcoVisioClient:
    """Minimal Eco-Visio client stub for testing."""

    def __init__(self, sites, include_recorder, api_key=None):
        self.sites = sites
        self.include_recorder = include_recorder
        self.api_key = api_key

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
        monkeypatch.setattr(utils, "get_eco_visio_api_keys", lambda: ["test_api_key"])
        monkeypatch.setattr(
            utils,
            "EcoVisioAPIClient",
            lambda api_key: DummyEcoVisioClient(sites, include_recorder, api_key),
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
        monkeypatch.setattr(utils, "get_eco_visio_api_keys", lambda: ["test_api_key"])
        monkeypatch.setattr(
            utils,
            "EcoVisioAPIClient",
            lambda api_key: DummyEcoVisioClient(sites, include_recorder, api_key),
        )
        monkeypatch.setattr(
            utils,
            "locates_in_south_western_finland",
            lambda point: False,
        )

        stations = utils.get_eco_visio_stations()

        assert include_recorder["include"] == ["segments"]
        assert stations == []

    def test_deduplicates_overlapping_sites_across_keys(self, monkeypatch):
        """Stations with the same ID provided by multiple keys are only imported once."""
        monkeypatch.setattr(utils, "get_eco_visio_api_keys", lambda: ["key1", "key2"])

        # key1 returns site 123 and site 456
        # key2 returns site 123 (duplicate) and site 789
        sites_key1 = [
            {
                "id": 123,
                "name": "Station 123",
                "location": {"lat": 60.45, "lon": 22.27},
            },
            {
                "id": 456,
                "name": "Station 456",
                "location": {"lat": 60.46, "lon": 22.28},
            },
        ]
        sites_key2 = [
            {
                "id": 123,
                "name": "Station 123 Dup",
                "location": {"lat": 60.45, "lon": 22.27},
            },
            {
                "id": 789,
                "name": "Station 789",
                "location": {"lat": 60.47, "lon": 22.29},
            },
        ]

        # Record which keys were used
        keys_used = []

        def mock_client_init(api_key):
            keys_used.append(api_key)
            sites = sites_key1 if api_key == "key1" else sites_key2
            return DummyEcoVisioClient(sites, {}, api_key)

        monkeypatch.setattr(utils, "EcoVisioAPIClient", mock_client_init)
        monkeypatch.setattr(
            utils, "locates_in_south_western_finland", lambda point: True
        )

        stations = utils.get_eco_visio_stations()

        assert len(keys_used) == 2
        assert "key1" in keys_used
        assert "key2" in keys_used

        # Should have 3 unique stations (123, 456, 789)
        assert len(stations) == 3
        station_ids = [s["station_id"] for s in stations]
        assert "123" in station_ids
        assert "456" in station_ids
        assert "789" in station_ids

        # Verify first occurrence was kept (from key1)
        station_123 = next(s for s in stations if s["station_id"] == "123")
        assert station_123["name"] == "Station 123"
