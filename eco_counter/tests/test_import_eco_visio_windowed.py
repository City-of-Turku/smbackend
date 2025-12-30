from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from django.utils.timezone import make_aware

from eco_counter.constants import ECO_COUNTER
from eco_counter.management.commands.import_counter_data import (
    import_eco_visio_windowed,
)
from eco_counter.models import ImportState, MonthData, Station, YearData


@pytest.mark.django_db
@patch("eco_counter.management.commands.import_counter_data.get_supported_travel_modes")
@patch("eco_counter.management.commands.import_counter_data.EcoVisioAPIClient")
@patch("eco_counter.management.commands.import_counter_data.get_eco_visio_api_keys")
@patch(
    "eco_counter.management.commands.import_counter_data.transform_raw_traffic_to_dataframe"
)
def test_import_eco_visio_windowed_resumable(
    mock_transform, mock_get_keys, mock_client_class, mock_travel_modes, stations
):
    # Setup
    mock_get_keys.return_value = ["test-key"]
    mock_travel_modes.return_value = ["bike"]

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.__enter__.return_value = mock_client
    mock_client.get_all_sites.return_value = [{"id": "1", "name": "Station 1"}]
    mock_client.get_raw_traffic.return_value = [{"some": "data"}]

    # Mock dataframe function that returns data based on requested range
    def mock_get_traffic(site_id, start_date, end_date, **kwargs):
        # Return a single row at the start of the requested range
        return [
            {"startTime": start_date.strftime("%Y-%m-%dT%H:%M"), "Station 1 AK": 10}
        ]

    mock_client.get_raw_traffic.side_effect = mock_get_traffic

    # The transform mock should just return what it's given as a dataframe
    def mock_transform_func(raw_data, station_name):
        return pd.DataFrame(raw_data)

    mock_transform.side_effect = mock_transform_func

    # Create station
    station = Station.objects.filter(csv_data_source=ECO_COUNTER).first()
    station.station_id = "1"
    station.save()

    # Initial state: start from 2024-01-01
    import_state = ImportState.objects.create(
        csv_data_source=ECO_COUNTER,
        current_year_number=2024,
        current_month_number=1,
        current_day_number=1,
    )

    # We want to test that it processes months and updates state.
    # To avoid infinite loop in test, we'll mock datetime.now to be close to start_time
    with patch(
        "eco_counter.management.commands.import_counter_data.datetime"
    ) as mock_datetime:
        # Set "now" to Feb 15th 2024
        mock_datetime.now.return_value = make_aware(datetime(2024, 2, 15))
        # Allow datetime(...) calls inside the importer to keep working (e.g. Day/Hour rollups)
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        mock_datetime.combine = datetime.combine
        mock_datetime.min = datetime.min

        import_eco_visio_windowed(import_state)

    # Check that it processed Jan and Feb, and set state to end of last processed window (Feb 16th)
    import_state.refresh_from_db()
    assert import_state.current_year_number == 2024
    assert import_state.current_month_number == 2
    assert import_state.current_day_number == 16

    # Verify rollups were created for Jan and Feb
    assert MonthData.objects.filter(station=station, month__month_number=1).exists()
    assert MonthData.objects.filter(station=station, month__month_number=2).exists()
    assert YearData.objects.filter(station=station, year__year_number=2024).exists()

    # Verify api calls
    # Should have called get_raw_traffic for Jan and Feb
    assert mock_client.get_raw_traffic.call_count == 2
