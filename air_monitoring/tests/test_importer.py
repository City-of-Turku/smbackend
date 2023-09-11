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
from air_monitoring.management.commands.import_air_monitoring_data import clear_cache
from air_monitoring.models import (
    Day,
    DayData,
    Hour,
    HourData,
    ImportState,
    Measurement,
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
    from air_monitoring.management.commands.import_air_monitoring_data import (
        save_measurements,
        save_parameter_types,
        save_stations,
    )

    options = {"initial_import": True}
    import_state = ImportState.load()
    assert import_state.year_number == START_YEAR
    assert import_state.month_number == 1
    clear_cache()
    stations = get_stations()
    save_stations(stations, options["initial_import"])
    num_stations = Station.objects.all().count()
    assert num_stations == 2
    kaarina_station = Station.objects.get(name=KAARINA_STATION)

    # Always start at the beginning of the month as the incremental
    # importer imports data monthly
    start_time = dateutil.parser.parse("2021-11-01T00:00:00Z")
    end_time = dateutil.parser.parse("2021-12-4T23:45:00Z")
    columns = []
    for station_name in STATION_NAMES:
        for parameter in OBSERVABLE_PARAMETERS:
            columns.append(f"{station_name} {parameter}")
    df = get_test_dataframe(columns, start_time, end_time)
    save_parameter_types(df, options["initial_import"])
    num_parameters = Parameter.objects.all().count()
    assert num_parameters == len(OBSERVABLE_PARAMETERS)
    aqindex_parameter = Parameter.objects.get(name=AQINDEX_PT1H_AVG)
    assert Parameter.objects.filter(name=PM10_PT1H_AVG).exists() is True
    save_measurements(df, options["initial_import"])
    import_state = ImportState.load()
    assert import_state.year_number == 2021
    assert import_state.month_number == 12
    # Test year data
    year = Year.objects.get(year_number=2021)
    year_data = YearData.objects.get(station=kaarina_station, year=year)
    measurement = year_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 3.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG
    assert year_data.measurements.all().count() == num_parameters
    assert Year.objects.all().count() == 1
    assert YearData.objects.all().count() == Station.objects.all().count()
    # Test month data
    november = Month.objects.get(year=year, month_number=11)
    month_data = MonthData.objects.get(station=kaarina_station, month=november)
    measurement = month_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 3.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG
    assert Month.objects.all().count() == 2
    assert MonthData.objects.all().count() == 4
    assert month_data.measurements.all().count() == num_parameters

    # Test week data
    week_46 = Week.objects.get(week_number=46, years=year)
    week_data = WeekData.objects.get(station=kaarina_station, week=week_46)
    measurement = week_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 3.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG
    assert Week.objects.all().count() == 5
    assert WeekData.objects.all().count() == 10
    assert week_data.measurements.all().count() == num_parameters

    # Test day
    day = Day.objects.get(date=dateutil.parser.parse("2021-11-02T00:00:00Z"))
    day_data = DayData.objects.get(station=kaarina_station, day=day)
    measurement = day_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 3.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG
    assert Day.objects.all().count() == 34
    assert DayData.objects.all().count() == 34 * num_stations
    assert day_data.measurements.all().count() == num_parameters

    # Test hours
    assert Hour.objects.all().count() == 34 * 24
    assert HourData.objects.all().count() == 34 * 24 * num_stations
    hour = Hour.objects.get(day=day, hour_number=0)
    hour_data = HourData.objects.get(station=kaarina_station, hour=hour)
    measurement = hour_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 2.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG
    assert hour_data.measurements.all().count() == num_parameters

    hour = Hour.objects.get(day=day, hour_number=1)
    hour_data = HourData.objects.get(station=kaarina_station, hour=hour)
    measurement = hour_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 4.0
    assert measurement.parameter.name == AQINDEX_PT1H_AVG

    # Test measurements
    num_measurements = (
        YearData.objects.all().count()
        + MonthData.objects.all().count()
        + WeekData.objects.all().count()
        + DayData.objects.all().count()
        + HourData.objects.all().count()
    ) * num_parameters
    assert Measurement.objects.all().count() == num_measurements
    # Test incremental import
    clear_cache()
    options = {"initial_import": False}
    start_time = dateutil.parser.parse("2021-12-01T00:00:00Z")
    end_time = dateutil.parser.parse("2021-12-15T23:45:00Z")
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
    year_data = YearData.objects.get(station=kaarina_station, year=year)
    measurement = year_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 3.0
    assert Year.objects.count() == 1
    assert Month.objects.count() == 2
    assert Week.objects.count() == 7
    assert Day.objects.count() == 30 + 15
    assert Hour.objects.count() == (30 + 15) * 24
    num_measurements = (
        YearData.objects.all().count()
        + MonthData.objects.all().count()
        + WeekData.objects.all().count()
        + DayData.objects.all().count()
        + HourData.objects.all().count()
    ) * num_parameters
    assert Measurement.objects.all().count() == num_measurements
    # Test incremental import when year changes
    clear_cache()
    start_time = dateutil.parser.parse("2021-12-01T00:00:00Z")
    end_time = dateutil.parser.parse("2022-01-15T23:45:00Z")
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
    year = Year.objects.get(year_number=2022)
    year_data = YearData.objects.get(station=kaarina_station, year=year)
    measurement = year_data.measurements.get(parameter=aqindex_parameter)
    assert round(measurement.value, 1) == 3.0
    assert Year.objects.all().count() == 2
    assert YearData.objects.all().count() == Year.objects.all().count() * num_stations
    assert Year.objects.get(year_number=2022)
    assert Month.objects.all().count() == 3
    assert MonthData.objects.all().count() == Month.objects.all().count() * num_stations
    assert Week.objects.all().count() == 12
    assert WeekData.objects.all().count() == Week.objects.all().count() * num_stations
    assert Day.objects.all().count() == 30 + 31 + 15
    assert DayData.objects.all().count() == Day.objects.all().count() * num_stations
    assert Hour.objects.all().count() == Day.objects.all().count() * 24
    assert (
        HourData.objects.all().count() == Day.objects.all().count() * 24 * num_stations
    )
    # Test measurements after incremental imports
    num_measurements = (
        YearData.objects.all().count()
        + MonthData.objects.all().count()
        + WeekData.objects.all().count()
        + DayData.objects.all().count()
        + HourData.objects.all().count()
    ) * num_parameters
    assert Measurement.objects.all().count() == num_measurements
    import_state = ImportState.load()
    assert import_state.year_number == 2022
    assert import_state.month_number == 1

    # Test initial import
    clear_cache()
    options = {"initial_import": True}
    stations = get_stations()
    save_stations(stations, options["initial_import"])
    assert Station.objects.all().count() == 2
    columns = []
    for station_name in STATION_NAMES:
        for parameter in OBSERVABLE_PARAMETERS[0:2]:
            columns.append(f"{station_name} {parameter}")
    start_time = dateutil.parser.parse("2023-01-01T00:00:00Z")
    end_time = dateutil.parser.parse("2023-01-10T23:45:00Z")
    df = get_test_dataframe(columns, start_time, end_time)
    save_parameter_types(df, options["initial_import"])
    assert Parameter.objects.all().count() == len(OBSERVABLE_PARAMETERS[0:2])
    save_measurements(df, options["initial_import"])
    assert Year.objects.count() == 1
    assert Month.objects.count() == 1
    assert (
        Week.objects.count() == 3
    )  # 1.12.2023 is a Sunday, so three different weeks in 10 days
    assert Day.objects.count() == 10
    assert Hour.objects.count() == 10 * 24
    num_measurements = (
        YearData.objects.all().count()
        + MonthData.objects.all().count()
        + WeekData.objects.all().count()
        + DayData.objects.all().count()
        + HourData.objects.all().count()
    ) * Parameter.objects.all().count()
    assert Measurement.objects.all().count() == num_measurements
    import_state = ImportState.load()
    assert import_state.year_number == 2023
    assert import_state.month_number == 1
    # Test initial import also stations
    clear_cache()
    options = {"initial_import_also_stations": True}
    stations = get_stations()[0:1]
    save_stations(stations, options["initial_import_also_stations"])
    assert Station.objects.all().count() == 1
