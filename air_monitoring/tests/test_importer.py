import logging

import dateutil.parser
import pandas as pd
import pytest
from django.contrib.gis.geos import Point

from air_monitoring.management.commands.constants import (
    AQINDEX_PT1H_AVG,
    OBSERVABLE_PARAMETERS,
    PM10_PT1H_AVG,
    START_YEAR,
)
from air_monitoring.models import (  # ImportState,; Measurement,; HourData,
    Day,
    DayData,
    Hour,
    HourData,
    ImportState,
    Month,
    MonthData,
    Parameter,
    Station,
    Week,
    WeekData,
    Year,
    YearData,
)

logger = logging.getLogger(__name__)


KAARINA_STATION = "Kaarina Kaarina"
NAANTALI_STATION = "Naantali keskusta Asematori"
STATION_NAMES = [KAARINA_STATION, NAANTALI_STATION]


def get_stations():
    stations = []
    for i, name in enumerate(STATION_NAMES):
        station = {"name": name}
        station["geoId"] = i
        station["location"] = Point(0, 0)
        stations.append(station)
    return stations


def get_test_dataframe(
    columns, start_time, end_time, time_stamp_column="index", min_value=2, max_value=4
):
    """
    Generates test Dataframe for a given timespan,
    """
    df = pd.DataFrame()
    timestamps = pd.date_range(start=start_time, end=end_time, freq="1h")
    for col in columns:
        vals = []
        for i in range(len(timestamps)):
            if i % 2 == 0:
                vals.append(min_value)
            else:
                vals.append(max_value)
        df.insert(0, col, vals)

    df.insert(0, time_stamp_column, timestamps)
    df["Date"] = pd.to_datetime(df["index"])
    df = df.drop("index", axis=1)
    df = df.set_index("Date")
    return df


@pytest.mark.django_db
def test_importer():
    from air_monitoring.management.commands.fmi import (
        save_measurements,
        save_parameter_types,
        save_stations,
    )

    options = {"initial_import": True}
    import_state = ImportState.load()
    assert import_state.year_number == START_YEAR
    assert import_state.month_number == 1
    stations = get_stations()
    save_stations(stations, options["initial_import"])
    assert Station.objects.all().count() == 2
    kaarina_station = Station.objects.get(name=KAARINA_STATION)
    start_time = dateutil.parser.parse("2021-01-01T00:00:00Z")
    end_time = dateutil.parser.parse("2021-02-28T23:45:00Z")
    columns = []
    for station_name in STATION_NAMES:
        for parameter in OBSERVABLE_PARAMETERS:
            columns.append(f"{station_name} {parameter}")
    df = get_test_dataframe(columns, start_time, end_time)
    save_parameter_types(df, options["initial_import"])
    assert Parameter.objects.all().count() == len(OBSERVABLE_PARAMETERS)
    aqindex_parameter = Parameter.objects.get(name=AQINDEX_PT1H_AVG)
    assert Parameter.objects.filter(name=PM10_PT1H_AVG).exists() is True
    save_measurements(df, options["initial_import"])
    import_state = ImportState.load()
    assert import_state.year_number == 2021
    assert import_state.month_number == 2
    # Test year data
    year = Year.objects.get(year_number=2021)
    year_data = YearData.objects.get(station=kaarina_station, year=year)
    measurement = year_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 3.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG
    assert Year.objects.all().count() == 1
    assert YearData.objects.all().count() == Station.objects.all().count()

    # Test month data
    august = Month.objects.get(year=year, month_number=2)
    month_data = MonthData.objects.get(station=kaarina_station, month=august)
    measurement = month_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 3.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG

    # Test week data
    week_5 = Week.objects.get(week_number=5, years=year)
    week_data = WeekData.objects.get(station=kaarina_station, week=week_5)
    measurement = week_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 3.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG

    # Test day
    day = Day.objects.get(date=dateutil.parser.parse("2021-02-02T00:00:00Z"))
    day_data = DayData.objects.get(station=kaarina_station, day=day)
    measurement = day_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 3.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG
    # Test hours
    hour = Hour.objects.get(day=day, hour_number=0)
    hour_data = HourData.objects.get(station=kaarina_station, hour=hour)
    measurement = hour_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 2.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG
    hour = Hour.objects.get(day=day, hour_number=1)
    hour_data = HourData.objects.get(station=kaarina_station, hour=hour)
    measurement = hour_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 4.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG

    # Test initial import
    options = {"initial_import": True}
    stations = get_stations()
    save_stations(stations, options["initial_import"])
    assert Station.objects.all().count() == 2
    columns = []
    for station_name in STATION_NAMES:
        for parameter in OBSERVABLE_PARAMETERS[0:2]:
            columns.append(f"{station_name} {parameter}")
    df = get_test_dataframe(columns, start_time, end_time)
    save_parameter_types(df, options["initial_import"])
    assert Parameter.objects.all().count() == len(OBSERVABLE_PARAMETERS[0:2])
    # Test initial import also stations
    options = {"initial_import_also_stations": True}
    stations = get_stations()[0:1]
    save_stations(stations, options["initial_import_also_stations"])
    assert Station.objects.all().count() == 1
