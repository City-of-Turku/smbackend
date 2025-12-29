from datetime import datetime, timedelta
from unittest.mock import call, MagicMock, patch

import pandas as pd
import pytest

from eco_counter.constants import ECO_COUNTER, INDEX_COLUMN_NAME
from eco_counter.management.commands import import_counter_data
from eco_counter.management.commands.import_counter_data import (
    EcoVisioAPIError,
    get_eco_visio_csv_data,
    TIMEZONE,
)
from eco_counter.models import Station


class FixedDatetime(datetime):
    """Deterministic datetime replacement for tests."""

    @classmethod
    def now(cls, tz=None):
        return cls(2024, 1, 5, tzinfo=tz)


@pytest.mark.django_db
@patch("eco_counter.management.commands.import_counter_data.get_eco_visio_api_keys")
@patch("eco_counter.management.commands.import_counter_data.get_supported_travel_modes")
@patch("eco_counter.management.commands.import_counter_data.combine_station_dataframes")
@patch(
    "eco_counter.management.commands.import_counter_data.transform_raw_traffic_to_dataframe"
)
@patch("eco_counter.management.commands.import_counter_data.EcoVisioAPIClient")
def test_get_eco_visio_csv_data_returns_sorted_combined(
    eco_client_mock,
    transform_mock,
    combine_mock,
    travel_modes_mock,
    api_keys_mock,
    monkeypatch,
):
    api_keys_mock.return_value = ["test-key"]
    travel_modes = ["bike"]
    travel_modes_mock.return_value = travel_modes
    start_time = TIMEZONE.localize(datetime(2024, 1, 1, 0, 0))
    monkeypatch.setattr(import_counter_data, "datetime", FixedDatetime)

    station1 = Station.objects.create(
        name="Station 1",
        location="POINT(0 0)",
        csv_data_source=ECO_COUNTER,
        station_id="101",
    )
    station2 = Station.objects.create(
        name="Station 2",
        location="POINT(1 1)",
        csv_data_source=ECO_COUNTER,
        station_id="102",
    )

    client_instance = MagicMock()
    eco_client_mock.return_value.__enter__.return_value = client_instance
    client_instance.get_all_sites.return_value = [{"id": 101}, {"id": 102}]
    raw_traffic_1 = [{"series": "s1"}]
    raw_traffic_2 = [{"series": "s2"}]
    client_instance.get_raw_traffic.side_effect = [raw_traffic_1, raw_traffic_2]

    df1 = pd.DataFrame({"startTime": ["2024-01-02T00:00"], "Station 1 PK": [1]})
    df2 = pd.DataFrame({"startTime": ["2024-01-01T00:00"], "Station 2 PK": [2]})
    transform_mock.side_effect = [df1, df2]

    # Return unsorted data to verify get_eco_visio_csv_data sorts the result.
    combine_mock.return_value = pd.DataFrame(
        [
            {"startTime": "2024-01-02T00:00", "Station 1 PK": 1},
            {"startTime": "2024-01-01T00:00", "Station 2 PK": 2},
        ]
    )

    result = get_eco_visio_csv_data(start_time)

    expected_end_date = FixedDatetime.now(TIMEZONE).date() + timedelta(days=1)
    client_instance.get_raw_traffic.assert_has_calls(
        [
            call(
                site_id=101,
                start_date=start_time.date(),
                end_date=expected_end_date,
                travel_modes=travel_modes,
                gap_filling=True,
            ),
            call(
                site_id=102,
                start_date=start_time.date(),
                end_date=expected_end_date,
                travel_modes=travel_modes,
                gap_filling=True,
            ),
        ]
    )
    transform_mock.assert_has_calls(
        [
            call(raw_traffic_1, station1.name),
            call(raw_traffic_2, station2.name),
        ]
    )
    passed_dataframes = combine_mock.call_args[0][0]
    assert len(passed_dataframes) == 2
    assert list(result[INDEX_COLUMN_NAME]) == [
        "2024-01-01T00:00",
        "2024-01-02T00:00",
    ]
    assert INDEX_COLUMN_NAME in result.columns
    assert {"Station 1 PK", "Station 2 PK"}.issubset(set(result.columns))


@pytest.mark.django_db
@patch("eco_counter.management.commands.import_counter_data.get_eco_visio_api_keys")
@patch("eco_counter.management.commands.import_counter_data.get_supported_travel_modes")
@patch("eco_counter.management.commands.import_counter_data.combine_station_dataframes")
@patch(
    "eco_counter.management.commands.import_counter_data.transform_raw_traffic_to_dataframe"
)
@patch("eco_counter.management.commands.import_counter_data.EcoVisioAPIClient")
def test_get_eco_visio_csv_data_skips_invalid_and_errors(
    eco_client_mock,
    transform_mock,
    combine_mock,
    travel_modes_mock,
    api_keys_mock,
    monkeypatch,
):
    api_keys_mock.return_value = ["test-key"]
    travel_modes_mock.return_value = ["bike"]
    # Use a start_time before FixedDatetime.now() (2024-01-05)
    start_time = TIMEZONE.localize(datetime(2024, 1, 1, 0, 0))
    monkeypatch.setattr(import_counter_data, "datetime", FixedDatetime)

    Station.objects.create(
        name="Invalid Station",
        location="POINT(0 0)",
        csv_data_source=ECO_COUNTER,
        station_id="invalid-id",
    )
    Station.objects.create(
        name="Valid Station",
        location="POINT(1 1)",
        csv_data_source=ECO_COUNTER,
        station_id="200",
    )

    client_instance = MagicMock()
    eco_client_mock.return_value.__enter__.return_value = client_instance
    client_instance.get_all_sites.return_value = [{"id": 200}]
    client_instance.get_raw_traffic.side_effect = EcoVisioAPIError("API failure")
    combine_mock.return_value = pd.DataFrame(columns=["startTime"])

    result = get_eco_visio_csv_data(start_time)

    expected_end_date = FixedDatetime.now(TIMEZONE).date() + timedelta(days=1)
    client_instance.get_raw_traffic.assert_called_once_with(
        site_id=200,
        start_date=start_time.date(),
        end_date=expected_end_date,
        travel_modes=["bike"],
        gap_filling=True,
    )
    transform_mock.assert_not_called()
    combine_mock.assert_called_once_with([])
    assert result.empty
    assert list(result.columns) == ["startTime"]


@pytest.mark.django_db
@patch("eco_counter.management.commands.import_counter_data.get_eco_visio_api_keys")
@patch("eco_counter.management.commands.import_counter_data.get_supported_travel_modes")
@patch("eco_counter.management.commands.import_counter_data.combine_station_dataframes")
@patch(
    "eco_counter.management.commands.import_counter_data.transform_raw_traffic_to_dataframe"
)
@patch("eco_counter.management.commands.import_counter_data.EcoVisioAPIClient")
def test_get_eco_visio_csv_data_per_station_start_date(
    eco_client_mock,
    transform_mock,
    combine_mock,
    travel_modes_mock,
    api_keys_mock,
    monkeypatch,
):
    api_keys_mock.return_value = ["test-key"]
    travel_modes_mock.return_value = ["bike"]
    global_start_time = TIMEZONE.localize(datetime(2024, 1, 1, 0, 0))
    monkeypatch.setattr(import_counter_data, "datetime", FixedDatetime)

    # Station 1: has firstData mid-month (should round down to 1st)
    Station.objects.create(
        name="Station 1",
        location="POINT(0 0)",
        csv_data_source=ECO_COUNTER,
        station_id="101",
        data_from_date=datetime(2023, 5, 15).date(),
    )
    # Station 2: no firstData (should use global start)
    Station.objects.create(
        name="Station 2",
        location="POINT(1 1)",
        csv_data_source=ECO_COUNTER,
        station_id="102",
        data_from_date=None,
    )

    client_instance = MagicMock()
    eco_client_mock.return_value.__enter__.return_value = client_instance
    client_instance.get_all_sites.return_value = [{"id": 101}, {"id": 102}]

    # We don't care about the actual data returned for this test
    client_instance.get_raw_traffic.return_value = []
    transform_mock.return_value = pd.DataFrame()
    combine_mock.return_value = pd.DataFrame(columns=["startTime"])

    get_eco_visio_csv_data(global_start_time)

    expected_end_date = FixedDatetime.now(TIMEZONE).date() + timedelta(days=1)
    client_instance.get_raw_traffic.assert_has_calls(
        [
            call(
                site_id=101,
                start_date=datetime(2023, 5, 1).date(),  # Rounded down
                end_date=expected_end_date,
                travel_modes=["bike"],
                gap_filling=True,
            ),
            call(
                site_id=102,
                start_date=global_start_time.date(),  # Fallback to global
                end_date=expected_end_date,
                travel_modes=["bike"],
                gap_filling=True,
            ),
        ],
        any_order=False,
    )
