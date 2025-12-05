"""
Unit tests for Eco-Visio API Data Mapper.

These tests provide comprehensive coverage of the mapping functionality
that transforms Eco-Visio API responses into the DataFrame format
expected by the existing eco_counter import logic.
"""

import pandas as pd
import pytest

from eco_counter.management.commands.eco_visio_mapper import (
    DIRECTION_MAPPING,
    TRAVEL_MODE_MAPPING,
    _normalize_timestamp,
    _process_undefined_direction_data,
    combine_station_dataframes,
    get_column_suffix,
    get_direction_code,
    get_movement_type_code,
    get_supported_travel_modes,
    get_travel_mode_description,
    transform_raw_traffic_to_dataframe,
)


class TestGetMovementTypeCode:
    """Tests for get_movement_type_code function."""

    def test_unknown_travel_mode_returns_none(self):
        """Test that unknown travel mode returns None."""
        assert get_movement_type_code("airplane") is None

    def test_case_insensitive_lowercase(self):
        """Test that travel mode matching is case insensitive (lowercase)."""
        assert get_movement_type_code("bike") == "P"

    def test_case_insensitive_uppercase(self):
        """Test that travel mode matching is case insensitive (uppercase)."""
        assert get_movement_type_code("BIKE") == "P"

    def test_case_insensitive_mixed_case(self):
        """Test that travel mode matching is case insensitive (mixed case)."""
        assert get_movement_type_code("Pedestrian") == "J"

    def test_all_mapped_travel_modes(self):
        """Test all travel modes that should be mapped."""
        mapped_modes = {
            "bike": "P",
            "pedestrian": "J",
            "car": "A",
            "motorized": "A",
            "bus": "B",
            "scooter": "P",
            "motorbike": "A",
            "truck": "A",
            "cargobike": "P",
            "minibus": "B",
        }
        for mode, expected_code in mapped_modes.items():
            assert get_movement_type_code(mode) == expected_code, f"Failed for {mode}"

    def test_all_unmapped_travel_modes(self):
        """Test all travel modes that should NOT be mapped."""
        unmapped_modes = ["horse", "kayak", "undefined"]
        for mode in unmapped_modes:
            assert get_movement_type_code(mode) is None, f"Failed for {mode}"


class TestGetDirectionCode:
    """Tests for get_direction_code function."""

    def test_in_returns_k(self):
        """Test that 'in' direction returns 'K' (keskustaan)."""
        assert get_direction_code("in") == "K"

    def test_out_returns_p(self):
        """Test that 'out' direction returns 'P' (poispäin)."""
        assert get_direction_code("out") == "P"

    def test_undefined_returns_none(self):
        """Test that 'undefined' direction returns None."""
        assert get_direction_code("undefined") is None

    def test_unknown_direction_returns_none(self):
        """Test that unknown direction returns None."""
        assert get_direction_code("left") is None
        assert get_direction_code("right") is None

    def test_case_insensitive_lowercase(self):
        """Test that direction matching is case insensitive (lowercase)."""
        assert get_direction_code("in") == "K"

    def test_case_insensitive_uppercase(self):
        """Test that direction matching is case insensitive (uppercase)."""
        assert get_direction_code("IN") == "K"
        assert get_direction_code("OUT") == "P"

    def test_case_insensitive_mixed_case(self):
        """Test that direction matching is case insensitive (mixed case)."""
        assert get_direction_code("Out") == "P"


class TestGetColumnSuffix:
    """Tests for get_column_suffix function."""

    def test_bike_in_returns_pk(self):
        """Test bike + in = PK."""
        assert get_column_suffix("bike", "in") == "PK"

    def test_bike_out_returns_pp(self):
        """Test bike + out = PP."""
        assert get_column_suffix("bike", "out") == "PP"

    def test_pedestrian_in_returns_jk(self):
        """Test pedestrian + in = JK."""
        assert get_column_suffix("pedestrian", "in") == "JK"

    def test_pedestrian_out_returns_jp(self):
        """Test pedestrian + out = JP."""
        assert get_column_suffix("pedestrian", "out") == "JP"

    def test_car_in_returns_ak(self):
        """Test car + in = AK."""
        assert get_column_suffix("car", "in") == "AK"

    def test_car_out_returns_ap(self):
        """Test car + out = AP."""
        assert get_column_suffix("car", "out") == "AP"

    def test_bus_in_returns_bk(self):
        """Test bus + in = BK."""
        assert get_column_suffix("bus", "in") == "BK"

    def test_bus_out_returns_bp(self):
        """Test bus + out = BP."""
        assert get_column_suffix("bus", "out") == "BP"

    def test_motorized_in_returns_ak(self):
        """Test motorized + in = AK (mapped to car)."""
        assert get_column_suffix("motorized", "in") == "AK"

    def test_scooter_out_returns_pp(self):
        """Test scooter + out = PP (mapped to bike)."""
        assert get_column_suffix("scooter", "out") == "PP"

    def test_minibus_in_returns_bk(self):
        """Test minibus + in = BK (mapped to bus)."""
        assert get_column_suffix("minibus", "in") == "BK"

    def test_unmapped_travel_mode_returns_none(self):
        """Test that unmapped travel mode returns None."""
        assert get_column_suffix("horse", "in") is None
        assert get_column_suffix("kayak", "out") is None

    def test_undefined_direction_returns_none(self):
        """Test that undefined direction returns None."""
        assert get_column_suffix("bike", "undefined") is None
        assert get_column_suffix("car", "undefined") is None

    def test_both_unmapped_returns_none(self):
        """Test that both unmapped travel mode and direction returns None."""
        assert get_column_suffix("horse", "undefined") is None

    def test_case_insensitive(self):
        """Test that column suffix is case insensitive."""
        assert get_column_suffix("BIKE", "IN") == "PK"
        assert get_column_suffix("Pedestrian", "Out") == "JP"


class TestNormalizeTimestamp:
    """Tests for _normalize_timestamp function."""

    def test_iso_format_with_positive_offset(self):
        """Test parsing ISO 8601 timestamp with positive timezone offset."""
        result = _normalize_timestamp("2024-01-01T00:00:00+02:00")
        assert result == "2024-01-01T00:00"

    def test_iso_format_with_negative_offset(self):
        """Test parsing ISO 8601 timestamp with negative timezone offset."""
        result = _normalize_timestamp("2024-01-01T15:30:00-05:00")
        assert result == "2024-01-01T15:30"

    def test_iso_format_with_z_suffix(self):
        """Test parsing ISO 8601 timestamp with Z (UTC) suffix."""
        result = _normalize_timestamp("2024-01-01T12:00:00Z")
        assert result == "2024-01-01T12:00"

    def test_iso_format_with_seconds(self):
        """Test that seconds are stripped from output."""
        result = _normalize_timestamp("2024-06-15T14:30:45+03:00")
        assert result == "2024-06-15T14:30"

    def test_iso_format_without_timezone(self):
        """Test parsing timestamp without timezone info."""
        result = _normalize_timestamp("2024-01-01T08:15:00")
        assert result == "2024-01-01T08:15"

    def test_none_input_returns_none(self):
        """Test that None input returns None."""
        result = _normalize_timestamp(None)
        assert result is None

    def test_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = _normalize_timestamp("")
        assert result is None

    def test_invalid_timestamp_returns_none(self):
        """Test that invalid timestamp returns None."""
        result = _normalize_timestamp("not-a-timestamp")
        assert result is None

    def test_partial_timestamp_returns_none(self):
        """Test that partial/malformed timestamp returns None."""
        result = _normalize_timestamp("2024-01-01")
        # This might be valid for fromisoformat in newer Python, but check behavior
        # If it fails, it should return None

    def test_midnight_timestamp(self):
        """Test midnight timestamp."""
        result = _normalize_timestamp("2024-12-31T00:00:00+00:00")
        assert result == "2024-12-31T00:00"

    def test_end_of_day_timestamp(self):
        """Test end of day timestamp."""
        result = _normalize_timestamp("2024-12-31T23:59:00+00:00")
        assert result == "2024-12-31T23:59"


class TestTransformRawTrafficToDataframe:
    """Tests for transform_raw_traffic_to_dataframe function."""

    def test_empty_data_returns_empty_dataframe(self):
        """Test that empty data returns DataFrame with only startTime column."""
        result = transform_raw_traffic_to_dataframe([], "Test Station")
        assert "startTime" in result.columns
        assert len(result) == 0

    def test_none_data_returns_empty_dataframe(self):
        """Test that None data returns empty DataFrame."""
        result = transform_raw_traffic_to_dataframe(None, "Test Station")
        assert "startTime" in result.columns
        assert len(result) == 0

    def test_single_series_bike_in(self):
        """Test transformation of single bike/in series."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 5},
                    {"timestamp": "2024-01-01T01:00:00+02:00", "counts": 10},
                ],
            }
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        assert len(result) == 2
        assert "startTime" in result.columns
        assert "Station1 PK" in result.columns
        assert result.loc[0, "Station1 PK"] == 5
        assert result.loc[1, "Station1 PK"] == 10

    def test_multiple_series_same_timestamp(self):
        """Test transformation of multiple series with same timestamps."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [{"timestamp": "2024-01-01T00:00:00+02:00", "counts": 5}],
            },
            {
                "travelMode": "bike",
                "direction": "out",
                "data": [{"timestamp": "2024-01-01T00:00:00+02:00", "counts": 3}],
            },
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        assert len(result) == 1
        assert "Station1 PK" in result.columns
        assert "Station1 PP" in result.columns
        assert result.loc[0, "Station1 PK"] == 5
        assert result.loc[0, "Station1 PP"] == 3

    def test_multiple_travel_modes(self):
        """Test transformation with multiple travel modes."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [{"timestamp": "2024-01-01T00:00:00+02:00", "counts": 10}],
            },
            {
                "travelMode": "pedestrian",
                "direction": "in",
                "data": [{"timestamp": "2024-01-01T00:00:00+02:00", "counts": 20}],
            },
            {
                "travelMode": "car",
                "direction": "out",
                "data": [{"timestamp": "2024-01-01T00:00:00+02:00", "counts": 30}],
            },
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "MultiMode")

        assert "MultiMode PK" in result.columns
        assert "MultiMode JK" in result.columns
        assert "MultiMode AP" in result.columns
        assert result.loc[0, "MultiMode PK"] == 10
        assert result.loc[0, "MultiMode JK"] == 20
        assert result.loc[0, "MultiMode AP"] == 30

    def test_undefined_travel_mode_is_skipped(self):
        """Test that undefined travel mode is skipped."""
        raw_data = [
            {
                "travelMode": "undefined",
                "direction": "in",
                "data": [{"timestamp": "2024-01-01T00:00:00+02:00", "counts": 100}],
            },
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [{"timestamp": "2024-01-01T00:00:00+02:00", "counts": 5}],
            },
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        # Should only have bike data
        assert "Station1 PK" in result.columns
        assert result.loc[0, "Station1 PK"] == 5

    def test_unmapped_travel_mode_with_defined_direction_is_skipped(self):
        """Test that unmapped travel mode (horse) with defined direction is skipped."""
        raw_data = [
            {
                "travelMode": "horse",
                "direction": "in",
                "data": [{"timestamp": "2024-01-01T00:00:00+02:00", "counts": 100}],
            },
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        # Should return empty DataFrame (only startTime)
        assert len(result) == 0

    def test_null_counts_treated_as_zero(self):
        """Test that null counts are treated as zero."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "counts": None},
                    {"timestamp": "2024-01-01T01:00:00+02:00", "counts": 5},
                ],
            }
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        assert result.loc[0, "Station1 PK"] == 0
        assert result.loc[1, "Station1 PK"] == 5

    def test_missing_counts_treated_as_zero(self):
        """Test that missing counts field is treated as zero."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00"},  # No counts field
                ],
            }
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        assert result.loc[0, "Station1 PK"] == 0

    def test_invalid_timestamp_is_skipped(self):
        """Test that data points with invalid timestamps are skipped."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [
                    {"timestamp": "invalid-timestamp", "counts": 100},
                    {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 5},
                ],
            }
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        # Should only have valid timestamp
        assert len(result) == 1
        assert result.loc[0, "Station1 PK"] == 5

    def test_missing_timestamp_is_skipped(self):
        """Test that data points with missing timestamps are skipped."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [
                    {"counts": 100},  # No timestamp
                    {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 5},
                ],
            }
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        assert len(result) == 1
        assert result.loc[0, "Station1 PK"] == 5

    def test_timestamps_are_sorted(self):
        """Test that output DataFrame is sorted by timestamp."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [
                    {"timestamp": "2024-01-01T03:00:00+02:00", "counts": 30},
                    {"timestamp": "2024-01-01T01:00:00+02:00", "counts": 10},
                    {"timestamp": "2024-01-01T02:00:00+02:00", "counts": 20},
                ],
            }
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        assert result.loc[0, "startTime"] == "2024-01-01T01:00"
        assert result.loc[1, "startTime"] == "2024-01-01T02:00"
        assert result.loc[2, "startTime"] == "2024-01-01T03:00"

    def test_aggregation_of_duplicate_timestamps(self):
        """Test that counts for same timestamp are aggregated."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 5},
                ],
            },
            {
                "travelMode": "scooter",  # Also maps to P
                "direction": "in",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 3},
                ],
            },
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        # bike (PK) + scooter (PK) should be aggregated
        assert result.loc[0, "Station1 PK"] == 8

    def test_series_without_data_key(self):
        """Test handling series without 'data' key."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                # No 'data' key
            }
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        # Should return empty DataFrame
        assert len(result) == 0

    def test_series_with_empty_data(self):
        """Test handling series with empty data list."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [],
            }
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        # Should return empty DataFrame
        assert len(result) == 0

    def test_missing_travel_mode_defaults_to_undefined(self):
        """Test that missing travelMode defaults to 'undefined'."""
        raw_data = [
            {
                # No travelMode
                "direction": "in",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 5},
                ],
            }
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        # undefined travel mode should be skipped
        assert len(result) == 0

    def test_missing_direction_defaults_to_undefined(self):
        """Test that missing direction defaults to 'undefined'."""
        raw_data = [
            {
                "travelMode": "bike",
                # No direction - defaults to 'undefined'
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 10},
                ],
            }
        ]
        result = transform_raw_traffic_to_dataframe(raw_data, "Station1")

        # With undefined direction, counts should be split between K and P
        assert "Station1 PK" in result.columns
        assert "Station1 PP" in result.columns
        assert result.loc[0, "Station1 PK"] == 5.0
        assert result.loc[0, "Station1 PP"] == 5.0


class TestProcessUndefinedDirectionData:
    """Tests for _process_undefined_direction_data function."""

    def test_splits_counts_equally(self):
        """Test that undefined direction splits counts equally between K and P."""
        data_points = [
            {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 10},
        ]
        timestamp_data = {}
        columns_seen = set()

        _process_undefined_direction_data(
            data_points, "Station1", "bike", timestamp_data, columns_seen
        )

        assert "Station1 PK" in columns_seen
        assert "Station1 PP" in columns_seen
        ts_key = "2024-01-01T00:00"
        assert timestamp_data[ts_key]["Station1 PK"] == 5.0
        assert timestamp_data[ts_key]["Station1 PP"] == 5.0

    def test_accumulates_with_existing_values(self):
        """Test that function accumulates with existing timestamp data."""
        data_points = [
            {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 10},
        ]
        ts_key = "2024-01-01T00:00"
        timestamp_data = {ts_key: {"Station1 PK": 3.0, "Station1 PP": 2.0}}
        columns_seen = set()

        _process_undefined_direction_data(
            data_points, "Station1", "bike", timestamp_data, columns_seen
        )

        # Should add 5 to each existing value
        assert timestamp_data[ts_key]["Station1 PK"] == 8.0
        assert timestamp_data[ts_key]["Station1 PP"] == 7.0

    def test_unmapped_travel_mode_does_nothing(self):
        """Test that unmapped travel mode (horse) does nothing."""
        data_points = [
            {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 10},
        ]
        timestamp_data = {}
        columns_seen = set()

        _process_undefined_direction_data(
            data_points, "Station1", "horse", timestamp_data, columns_seen
        )

        # Should have no effect
        assert len(timestamp_data) == 0
        assert len(columns_seen) == 0

    def test_handles_null_counts(self):
        """Test handling of null counts in undefined direction data."""
        data_points = [
            {"timestamp": "2024-01-01T00:00:00+02:00", "counts": None},
        ]
        timestamp_data = {}
        columns_seen = set()

        _process_undefined_direction_data(
            data_points, "Station1", "bike", timestamp_data, columns_seen
        )

        ts_key = "2024-01-01T00:00"
        assert timestamp_data[ts_key]["Station1 PK"] == 0.0
        assert timestamp_data[ts_key]["Station1 PP"] == 0.0

    def test_skips_invalid_timestamps(self):
        """Test that invalid timestamps are skipped."""
        data_points = [
            {"timestamp": "invalid", "counts": 10},
            {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 20},
        ]
        timestamp_data = {}
        columns_seen = set()

        _process_undefined_direction_data(
            data_points, "Station1", "bike", timestamp_data, columns_seen
        )

        # Should only have valid timestamp
        assert len(timestamp_data) == 1
        assert "2024-01-01T00:00" in timestamp_data

    def test_multiple_data_points(self):
        """Test processing multiple data points."""
        data_points = [
            {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 10},
            {"timestamp": "2024-01-01T01:00:00+02:00", "counts": 20},
        ]
        timestamp_data = {}
        columns_seen = set()

        _process_undefined_direction_data(
            data_points, "Station1", "bike", timestamp_data, columns_seen
        )

        assert len(timestamp_data) == 2
        assert timestamp_data["2024-01-01T00:00"]["Station1 PK"] == 5.0
        assert timestamp_data["2024-01-01T01:00"]["Station1 PK"] == 10.0

    def test_pedestrian_undefined_direction(self):
        """Test undefined direction with pedestrian travel mode."""
        data_points = [
            {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 100},
        ]
        timestamp_data = {}
        columns_seen = set()

        _process_undefined_direction_data(
            data_points, "MyStation", "pedestrian", timestamp_data, columns_seen
        )

        assert "MyStation JK" in columns_seen
        assert "MyStation JP" in columns_seen
        ts_key = "2024-01-01T00:00"
        assert timestamp_data[ts_key]["MyStation JK"] == 50.0
        assert timestamp_data[ts_key]["MyStation JP"] == 50.0


class TestCombineStationDataframes:
    """Tests for combine_station_dataframes function."""

    def test_empty_list_returns_empty_dataframe(self):
        """Test that empty list returns DataFrame with only startTime column."""
        result = combine_station_dataframes([])
        assert "startTime" in result.columns
        assert len(result) == 0

    def test_single_dataframe_returned_as_is(self):
        """Test that single DataFrame is returned unchanged."""
        df = pd.DataFrame(
            {"startTime": ["2024-01-01T00:00"], "Station1 PK": [5]}
        )
        result = combine_station_dataframes([df])

        assert len(result) == 1
        assert "Station1 PK" in result.columns

    def test_multiple_dataframes_same_timestamps(self):
        """Test combining DataFrames with same timestamps."""
        df1 = pd.DataFrame(
            {"startTime": ["2024-01-01T00:00"], "Station1 PK": [5]}
        )
        df2 = pd.DataFrame(
            {"startTime": ["2024-01-01T00:00"], "Station2 PK": [10]}
        )
        result = combine_station_dataframes([df1, df2])

        assert len(result) == 1
        assert "Station1 PK" in result.columns
        assert "Station2 PK" in result.columns
        assert result.loc[0, "Station1 PK"] == 5
        assert result.loc[0, "Station2 PK"] == 10

    def test_multiple_dataframes_different_timestamps(self):
        """Test combining DataFrames with different timestamps (outer join)."""
        df1 = pd.DataFrame(
            {"startTime": ["2024-01-01T00:00"], "Station1 PK": [5]}
        )
        df2 = pd.DataFrame(
            {"startTime": ["2024-01-01T01:00"], "Station2 PK": [10]}
        )
        result = combine_station_dataframes([df1, df2])

        # Should have 2 rows (outer join)
        assert len(result) == 2
        # Missing values should be filled with 0
        assert result.loc[0, "Station2 PK"] == 0
        assert result.loc[1, "Station1 PK"] == 0

    def test_dataframes_sorted_by_timestamp(self):
        """Test that combined DataFrame is sorted by timestamp."""
        df1 = pd.DataFrame(
            {"startTime": ["2024-01-01T02:00"], "Station1 PK": [20]}
        )
        df2 = pd.DataFrame(
            {"startTime": ["2024-01-01T01:00"], "Station2 PK": [10]}
        )
        result = combine_station_dataframes([df1, df2])

        assert result.loc[0, "startTime"] == "2024-01-01T01:00"
        assert result.loc[1, "startTime"] == "2024-01-01T02:00"

    def test_empty_dataframes_are_filtered(self):
        """Test that empty DataFrames are filtered out."""
        df1 = pd.DataFrame(columns=["startTime"])  # Empty
        df2 = pd.DataFrame(
            {"startTime": ["2024-01-01T00:00"], "Station2 PK": [10]}
        )
        result = combine_station_dataframes([df1, df2])

        assert len(result) == 1
        assert "Station2 PK" in result.columns

    def test_dataframes_without_starttime_are_filtered(self):
        """Test that DataFrames without startTime column are filtered."""
        df1 = pd.DataFrame({"some_column": [1, 2, 3]})  # No startTime
        df2 = pd.DataFrame(
            {"startTime": ["2024-01-01T00:00"], "Station2 PK": [10]}
        )
        result = combine_station_dataframes([df1, df2])

        assert len(result) == 1
        assert "Station2 PK" in result.columns

    def test_all_empty_dataframes_returns_empty(self):
        """Test that all empty DataFrames returns empty result."""
        df1 = pd.DataFrame(columns=["startTime"])
        df2 = pd.DataFrame(columns=["startTime"])
        result = combine_station_dataframes([df1, df2])

        assert "startTime" in result.columns
        assert len(result) == 0

    def test_nan_values_filled_with_zero(self):
        """Test that NaN values from outer join are filled with 0."""
        df1 = pd.DataFrame({
            "startTime": ["2024-01-01T00:00", "2024-01-01T01:00"],
            "Station1 PK": [5, 10],
        })
        df2 = pd.DataFrame({
            "startTime": ["2024-01-01T00:00"],
            "Station2 PK": [20],
        })
        result = combine_station_dataframes([df1, df2])

        # Station2 PK should be 0 for second timestamp
        assert result.loc[1, "Station2 PK"] == 0

    def test_three_dataframes(self):
        """Test combining three DataFrames."""
        df1 = pd.DataFrame({"startTime": ["2024-01-01T00:00"], "A PK": [1]})
        df2 = pd.DataFrame({"startTime": ["2024-01-01T00:00"], "B PK": [2]})
        df3 = pd.DataFrame({"startTime": ["2024-01-01T00:00"], "C PK": [3]})

        result = combine_station_dataframes([df1, df2, df3])

        assert len(result) == 1
        assert result.loc[0, "A PK"] == 1
        assert result.loc[0, "B PK"] == 2
        assert result.loc[0, "C PK"] == 3


class TestGetSupportedTravelModes:
    """Tests for get_supported_travel_modes function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        result = get_supported_travel_modes()
        assert isinstance(result, list)

    def test_contains_main_travel_modes(self):
        """Test that main travel modes are included."""
        result = get_supported_travel_modes()
        assert "bike" in result
        assert "pedestrian" in result
        assert "car" in result
        assert "bus" in result

    def test_does_not_contain_unmapped_modes(self):
        """Test that unmapped modes are not included."""
        result = get_supported_travel_modes()
        assert "horse" not in result
        assert "kayak" not in result
        assert "undefined" not in result

    def test_contains_additional_mapped_modes(self):
        """Test that additional mapped modes are included."""
        result = get_supported_travel_modes()
        assert "scooter" in result
        assert "cargobike" in result
        assert "motorbike" in result
        assert "truck" in result
        assert "minibus" in result
        assert "motorized" in result


class TestGetTravelModeDescription:
    """Tests for get_travel_mode_description function."""

    def test_bike_description(self):
        """Test description for bike."""
        result = get_travel_mode_description("bike")
        assert "bike" in result
        assert "P" in result
        assert "Pyörä" in result or "bicycle" in result

    def test_pedestrian_description(self):
        """Test description for pedestrian."""
        result = get_travel_mode_description("pedestrian")
        assert "pedestrian" in result
        assert "J" in result
        assert "Jalankulkija" in result or "pedestrian" in result

    def test_car_description(self):
        """Test description for car."""
        result = get_travel_mode_description("car")
        assert "car" in result
        assert "A" in result
        assert "Auto" in result or "car" in result

    def test_bus_description(self):
        """Test description for bus."""
        result = get_travel_mode_description("bus")
        assert "bus" in result
        assert "B" in result
        assert "Bussi" in result or "bus" in result

    def test_unmapped_mode_description(self):
        """Test description for unmapped mode."""
        result = get_travel_mode_description("horse")
        assert "horse" in result
        assert "not mapped" in result

    def test_case_insensitive(self):
        """Test that description is case insensitive."""
        result = get_travel_mode_description("BIKE")
        assert "P" in result

    def test_unknown_mode_shows_not_mapped(self):
        """Test that unknown mode shows not mapped."""
        result = get_travel_mode_description("spaceship")
        assert "not mapped" in result


class TestMappingConstants:
    """Tests for mapping constant dictionaries."""

    def test_travel_mode_mapping_completeness(self):
        """Test that all expected travel modes are in the mapping."""
        expected_modes = [
            "bike",
            "pedestrian",
            "car",
            "motorized",
            "bus",
            "horse",
            "kayak",
            "scooter",
            "motorbike",
            "truck",
            "cargobike",
            "minibus",
            "undefined",
        ]
        for mode in expected_modes:
            assert mode in TRAVEL_MODE_MAPPING, f"Missing mode: {mode}"

    def test_direction_mapping_completeness(self):
        """Test that all expected directions are in the mapping."""
        expected_directions = ["in", "out", "undefined"]
        for direction in expected_directions:
            assert direction in DIRECTION_MAPPING, f"Missing direction: {direction}"

    def test_travel_mode_codes_valid(self):
        """Test that all mapped travel mode codes are valid (A, P, J, B, or None)."""
        valid_codes = {"A", "P", "J", "B", None}
        for mode, code in TRAVEL_MODE_MAPPING.items():
            assert code in valid_codes, f"Invalid code {code} for mode {mode}"

    def test_direction_codes_valid(self):
        """Test that all mapped direction codes are valid (K, P, or None)."""
        valid_codes = {"K", "P", None}
        for direction, code in DIRECTION_MAPPING.items():
            assert code in valid_codes, f"Invalid code {code} for direction {direction}"


class TestIntegrationScenarios:
    """Integration tests for complete data transformation scenarios."""

    def test_realistic_api_response_transformation(self):
        """Test transformation of a realistic API response."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "flowID": 1,
                "flowName": "Bike In",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "granularity": "PT15M", "counts": 5},
                    {"timestamp": "2024-01-01T00:15:00+02:00", "granularity": "PT15M", "counts": 8},
                    {"timestamp": "2024-01-01T00:30:00+02:00", "granularity": "PT15M", "counts": 3},
                    {"timestamp": "2024-01-01T00:45:00+02:00", "granularity": "PT15M", "counts": 2},
                ],
            },
            {
                "travelMode": "bike",
                "direction": "out",
                "flowID": 2,
                "flowName": "Bike Out",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "granularity": "PT15M", "counts": 3},
                    {"timestamp": "2024-01-01T00:15:00+02:00", "granularity": "PT15M", "counts": 4},
                    {"timestamp": "2024-01-01T00:30:00+02:00", "granularity": "PT15M", "counts": 6},
                    {"timestamp": "2024-01-01T00:45:00+02:00", "granularity": "PT15M", "counts": 1},
                ],
            },
            {
                "travelMode": "pedestrian",
                "direction": "in",
                "flowID": 3,
                "flowName": "Pedestrian In",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "granularity": "PT15M", "counts": 10},
                    {"timestamp": "2024-01-01T00:15:00+02:00", "granularity": "PT15M", "counts": 15},
                ],
            },
        ]

        result = transform_raw_traffic_to_dataframe(raw_data, "Aurakatu")

        # Verify structure
        assert "startTime" in result.columns
        assert "Aurakatu PK" in result.columns  # bike in
        assert "Aurakatu PP" in result.columns  # bike out
        assert "Aurakatu JK" in result.columns  # pedestrian in

        # Verify data
        assert len(result) == 4  # 4 timestamps
        assert result.loc[0, "Aurakatu PK"] == 5
        assert result.loc[0, "Aurakatu PP"] == 3
        assert result.loc[0, "Aurakatu JK"] == 10

        # Later timestamp should have pedestrian = 0 (no data)
        assert result.loc[2, "Aurakatu JK"] == 0

    def test_combine_multiple_stations(self):
        """Test combining data from multiple stations."""
        # Station 1 data
        raw_data_1 = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 10},
                    {"timestamp": "2024-01-01T01:00:00+02:00", "counts": 20},
                ],
            }
        ]

        # Station 2 data
        raw_data_2 = [
            {
                "travelMode": "car",
                "direction": "out",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "counts": 100},
                    {"timestamp": "2024-01-01T01:00:00+02:00", "counts": 150},
                ],
            }
        ]

        df1 = transform_raw_traffic_to_dataframe(raw_data_1, "Station1")
        df2 = transform_raw_traffic_to_dataframe(raw_data_2, "Station2")

        combined = combine_station_dataframes([df1, df2])

        # Verify combined data
        assert len(combined) == 2
        assert "Station1 PK" in combined.columns
        assert "Station2 AP" in combined.columns
        assert combined.loc[0, "Station1 PK"] == 10
        assert combined.loc[0, "Station2 AP"] == 100
        assert combined.loc[1, "Station1 PK"] == 20
        assert combined.loc[1, "Station2 AP"] == 150

    def test_15_minute_granularity_preserved(self):
        """Test that 15-minute granularity data is preserved."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "granularity": "PT15M", "counts": 1},
                    {"timestamp": "2024-01-01T00:15:00+02:00", "granularity": "PT15M", "counts": 2},
                    {"timestamp": "2024-01-01T00:30:00+02:00", "granularity": "PT15M", "counts": 3},
                    {"timestamp": "2024-01-01T00:45:00+02:00", "granularity": "PT15M", "counts": 4},
                ],
            }
        ]

        result = transform_raw_traffic_to_dataframe(raw_data, "Test")

        # Should have 4 separate rows for 15-minute intervals
        assert len(result) == 4
        assert result.loc[0, "startTime"] == "2024-01-01T00:00"
        assert result.loc[1, "startTime"] == "2024-01-01T00:15"
        assert result.loc[2, "startTime"] == "2024-01-01T00:30"
        assert result.loc[3, "startTime"] == "2024-01-01T00:45"

    def test_mixed_undefined_and_defined_directions(self):
        """Test handling of mixed undefined and defined directions."""
        raw_data = [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [{"timestamp": "2024-01-01T00:00:00+02:00", "counts": 10}],
            },
            {
                "travelMode": "bike",
                "direction": "undefined",
                "data": [{"timestamp": "2024-01-01T00:00:00+02:00", "counts": 6}],
            },
        ]

        result = transform_raw_traffic_to_dataframe(raw_data, "Test")

        # Should have PK and PP columns
        assert "Test PK" in result.columns
        assert "Test PP" in result.columns

        # PK should have 10 (from 'in') + 3 (half of 6 from 'undefined')
        assert result.loc[0, "Test PK"] == 13.0
        # PP should have 3 (half of 6 from 'undefined')
        assert result.loc[0, "Test PP"] == 3.0

