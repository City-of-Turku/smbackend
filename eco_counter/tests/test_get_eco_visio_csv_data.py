from datetime import datetime, timedelta
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from eco_counter.constants import ECO_COUNTER, INDEX_COLUMN_NAME
from eco_counter.management.commands import import_counter_data
from eco_counter.management.commands.import_counter_data import (
    EcoVisioAPIError,
    TIMEZONE,
    get_eco_visio_csv_data,
)
from eco_counter.models import Station


class FixedDatetime(datetime):
    """Deterministic datetime replacement for tests."""

    @classmethod
    def now(cls, tz=None):
        return cls(2024, 1, 5, tzinfo=tz)


@pytest.mark.django_db
@patch("eco_counter.management.commands.import_counter_data.get_supported_travel_modes")
@patch("eco_counter.management.commands.import_counter_data.combine_station_dataframes")
@patch("eco_counter.management.commands.import_counter_data.transform_raw_traffic_to_dataframe")
@patch("eco_counter.management.commands.import_counter_data.EcoVisioAPIClient")
def test_get_eco_visio_csv_data_returns_sorted_combined(
    eco_client_mock,
    transform_mock,
    combine_mock,
    travel_modes_mock,
    monkeypatch,
):
    travel_modes = ["bike"]
    travel_modes_mock.return_value = travel_modes
    start_time = TIMEZONE.localize(datetime(2024, 1, 1, 0, 0))
    monkeypatch.setattr(import_counter_data, "datetime", FixedDatetime)

    station1 = Station.objects.create(
        name="Station 1", location="POINT(0 0)", csv_data_source=ECO_COUNTER, station_id="101"
    )
    station2 = Station.objects.create(
        name="Station 2", location="POINT(1 1)", csv_data_source=ECO_COUNTER, station_id="102"
    )

    client_instance = MagicMock()
    eco_client_mock.return_value.__enter__.return_value = client_instance
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
@patch("eco_counter.management.commands.import_counter_data.get_supported_travel_modes")
@patch("eco_counter.management.commands.import_counter_data.combine_station_dataframes")
@patch("eco_counter.management.commands.import_counter_data.transform_raw_traffic_to_dataframe")
@patch("eco_counter.management.commands.import_counter_data.EcoVisioAPIClient")
def test_get_eco_visio_csv_data_skips_invalid_and_errors(
    eco_client_mock,
    transform_mock,
    combine_mock,
    travel_modes_mock,
    monkeypatch,
):
    travel_modes_mock.return_value = ["bike"]
    start_time = TIMEZONE.localize(datetime(2024, 2, 1, 0, 0))
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

