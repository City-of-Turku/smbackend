import logging
import xml.etree.ElementTree as Et
from datetime import datetime, timedelta
from functools import lru_cache

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from django.contrib.gis.geos import Point, Polygon
from django.core.management import BaseCommand
from django.db import connection, reset_queries

from air_monitoring.models import (  # ImportState,
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
from mobility_data.importers.constants import (
    SOUTHWEST_FINLAND_BOUNDARY,
    SOUTHWEST_FINLAND_BOUNDARY_SRID,
)

from .constants import (
    DATA_URL,
    NAMESPACES,
    OBSERVABLE_PARAMETERS,
    PARAMS,
    SOURCE_DATA_SRID,
    START_YEAR,
    STATION_URL,
    TIME_FORMAT,
)

logger = logging.getLogger(__name__)


def get_stations():
    response = requests.get(STATION_URL)
    stations = []

    if response.status_code == 200:
        polygon = Polygon(
            SOUTHWEST_FINLAND_BOUNDARY, srid=SOUTHWEST_FINLAND_BOUNDARY_SRID
        )
        root = Et.fromstring(response.content)
        monitoring_facilities = root.findall(
            ".//ef:EnvironmentalMonitoringFacility", NAMESPACES
        )
        for mf in monitoring_facilities:
            belongs_to = mf.find("ef:belongsTo", NAMESPACES)
            title = belongs_to.attrib["{http://www.w3.org/1999/xlink}title"]
            match_str = "Kolmannen osapuolen ilmanlaadun havaintoasema"
            if title in match_str:
                station = {}
                positions = mf.find(".//gml:pos", NAMESPACES).text.split(" ")
                location = Point(
                    float(positions[1]), float(positions[0]), srid=SOURCE_DATA_SRID
                )
                if polygon.covers(location):
                    station["name"] = mf.find("gml:name", NAMESPACES).text
                    station["location"] = location
                    station["geoId"] = mf.find("gml:identifier", NAMESPACES).text
                    stations.append(station)
    else:
        logger.error(
            f"Could not get stations from {STATION_URL}, {response.status_code} {response.content}"
        )

    logger.info(f"Fetched {len(stations)} stations in Southwest Finland.")
    return stations


def get_dataframe(stations, from_year=START_YEAR, from_month=1, initial_import=False):
    current_date_time = datetime.now()
    # current_date_time = datetime.strptime(f"2023-02-01T00:00:00Z", TIME_FORMAT)
    if from_year and from_month:
        from_date_time = datetime.strptime(f"{from_year}-01-01T00:00:00Z", TIME_FORMAT)
    column_data = {}
    for station in stations:
        logger.info(f"Fetching data for station {station['name']}")
        for parameter in OBSERVABLE_PARAMETERS:
            data = {}
            start_date_time = from_date_time
            while start_date_time.year <= current_date_time.year:
                params = PARAMS
                params["geoId"] = f"-{station['geoId']}"
                params["parameters"] = parameter

                if not initial_import and from_year == current_date_time.year:
                    params["startTime"] = f"{from_year}-{from_month}-01T00:00Z"
                else:
                    params["startTime"] = f"{start_date_time.year}-01-01T00:00Z"
                if start_date_time.year == current_date_time.year:

                    params["endTime"] = current_date_time.strftime(TIME_FORMAT)
                else:
                    params["endTime"] = f"{start_date_time.year}-12-31T23:59Z"

                response = requests.get(DATA_URL, params=params)
                logger.info(f"Requested data from: {response.url}")
                if response.status_code == 200:
                    root = Et.fromstring(response.content)
                    observation_series = root.findall(
                        ".//omso:PointTimeSeriesObservation",
                        NAMESPACES,
                    )
                    if len(observation_series) != 1:
                        logger.error(
                            f"Observation series length not 1, it is {len(observation_series)} "
                        )
                        if start_date_time.year < current_date_time.year:
                            timestamp = start_date_time
                            end_timestamp = start_date_time + relativedelta(years=1)
                            while timestamp <= end_timestamp:
                                datetime_str = datetime.strftime(timestamp, TIME_FORMAT)
                                data[datetime_str] = float("nan")
                                timestamp += timedelta(hours=1)
                        start_date_time += relativedelta(years=1)
                        continue

                    measurements = root.findall(".//wml2:MeasurementTVP", NAMESPACES)
                    logger.info(f"Fetched {len(measurements)} measurements.")
                    for measurement in measurements:
                        time = measurement.find("wml2:time", NAMESPACES).text
                        value = float(measurement.find("wml2:value", NAMESPACES).text)
                        data[time] = value
                else:
                    logger.error(
                        f"Could not fetch data from {response.url}, {response.status_code} {response.content}"
                    )

                start_date_time += relativedelta(years=1)
            column_name = f"{station['name']} {params['parameters']}"
            column_data[column_name] = data

    df = pd.DataFrame.from_dict(column_data)
    df["Date"] = pd.to_datetime(df.index, format=TIME_FORMAT)
    df = df.set_index("Date")
    # df.to_csv("fmi.csv")
    return df


def create_row(model, filter):
    results = model.objects.filter(**filter)
    if not results.exists():
        model.objects.create(**filter)


def get_or_create_row(model, filter):
    results = model.objects.filter(**filter)
    if results.exists():
        return results.first(), False
    else:
        return model.objects.create(**filter), True


@lru_cache(maxsize=4069)
def get_or_create_row_cached(model, filter: tuple):
    filter = {key: value for key, value in filter}
    results = model.objects.filter(**filter)
    if results.exists():
        return results.first(), False
    else:
        return model.objects.create(**filter), True


@lru_cache(maxsize=4096)
def get_or_create_hour_row_cached(day, hour_number):
    results = Hour.objects.filter(day=day, hour_number=hour_number)
    if results.exists():
        return results.first(), False
    else:
        return (
            Hour.objects.create(day=day, hour_number=hour_number),
            True,
        )


@lru_cache(maxsize=4096)
def get_or_create_day_row_cached(date, year, month, week):
    results = Day.objects.filter(
        date=date,
        weekday_number=date.weekday(),
        year=year,
        month=month,
        week=week,
    )
    if results.exists():
        return results.first(), False
    else:
        return (
            Day.objects.create(
                date=date,
                weekday_number=date.weekday(),
                year=year,
                month=month,
                week=week,
            ),
            True,
        )


@lru_cache(maxsize=4096)
# Use tuple as it is immutable and is hashable for lru_cache
def get_row_cached(model, filter: tuple):
    filter = {key: value for key, value in filter}
    results = model.objects.filter(**filter)
    if results.exists():
        return results.first()
    else:
        return None


# def get_row(model, filter):
#     results = model.objects.filter(**filter)
#     if results.exists():
#         return results.first()
#     else:
#         return None


@lru_cache(maxsize=64)
def get_year_cached(year_number):
    qs = Year.objects.filter(year_number=year_number)
    if qs.exists():
        return qs.first()
    else:
        return None


@lru_cache(maxsize=128)
def get_year_data_cached(station, year):
    qs = YearData.objects.filter(station=station, year=year)
    if qs.exists():
        return qs.first()
    else:
        return None


@lru_cache(maxsize=256)
def get_month_cached(year, month_number):
    qs = Month.objects.filter(year=year, month_number=month_number)
    if qs.exists():
        return qs.first()
    else:
        return None


@lru_cache(maxsize=256)
def get_month_data_cached(station, month):
    qs = MonthData.objects.filter(station=station, month=month)
    if qs.exists():
        return qs.first()
    else:
        return None


@lru_cache(maxsize=1024)
def get_week_cached(years, week_number):
    qs = Week.objects.filter(years=years, week_number=week_number)
    if qs.exists():
        return qs.first()
    else:
        return None


@lru_cache(maxsize=2048)
def get_day_cached(date):
    qs = Day.objects.filter(date=date)
    if qs.exists():
        return qs.first()
    else:
        return None


def get_measurements(mean_series, station_name):
    values = {}
    for parameter in OBSERVABLE_PARAMETERS:
        key = f"{station_name} {parameter}"
        value = mean_series.get(key, False)
        if value:
            values[parameter] = value
    return values


@lru_cache(maxsize=16)
def get_parameter(name):
    try:
        return Parameter.objects.get(name=name)
    except Parameter.DoesNotExist:
        return None


def get_measurement_objects(measurements):
    measurement_rows = []
    for item in measurements.items():
        parameter = get_parameter(item[0])
        measurement = Measurement(value=item[1], parameter=parameter)
        measurement_rows.append(measurement)
    return measurement_rows


def bulk_create_rows(data_model, model_objs, measurements, datas):
    logger.info(f"Bulk creating {len(model_objs)} {data_model.__name__} rows")
    data_model.objects.bulk_create(model_objs)
    logger.info(f"Bulk creating {len(measurements)} Measurement rows")
    Measurement.objects.bulk_create(measurements)
    for key in datas:
        data = datas[key]
        [data["data"].measurements.add(m) for m in data["measurements"]]


def save_years(df, stations):
    logger.info("Saving years...")
    years = df.groupby(df.index.year)
    for station in stations:
        measurements = []
        year_datas = {}
        year_data_objs = []
        for index, row in years:
            mean_series = row.mean().dropna()
            year, _ = get_or_create_row_cached(Year, (("year_number", index),))
            values = get_measurements(mean_series, station.name)
            year_data = YearData(station=station, year=year)
            year_data_objs.append(year_data)
            ret_mes = get_measurement_objects(values)
            measurements += ret_mes
            year_datas[index] = {"data": year_data, "measurements": ret_mes}
        bulk_create_rows(YearData, year_data_objs, measurements, year_datas)


def save_months(df, stations):
    logger.info("Saving months...")
    months = df.groupby([df.index.year, df.index.month])
    for station in stations:
        measurements = []
        month_datas = {}
        month_data_objs = []
        for index, row in months:
            year_number, month_number = index
            mean_series = row.mean().dropna()
            year = get_year_cached(year_number)
            month, _ = get_or_create_row_cached(
                Month,
                (("year", year), ("month_number", month_number)),
            )
            values = get_measurements(mean_series, station.name)
            month_data = MonthData(station=station, year=year, month=month)
            month_data_objs.append(month_data)
            ret_mes = get_measurement_objects(values)
            measurements += ret_mes
            month_datas[index] = {"data": month_data, "measurements": ret_mes}
        bulk_create_rows(MonthData, month_data_objs, measurements, month_datas)


def save_weeks(df, stations):
    """
    Note, weeks are stored in a different way, as a week can not be assigned
    distinctly to a year or month. So when importing incrementally the week
    or weeks in the dataframe can not be deleted before populating, thus the
    use of get_or_create.
    """
    logger.info("Saving weeks...")
    weeks = df.groupby([df.index.year, df.index.isocalendar().week])
    for station in stations:
        for index, row in weeks:
            year_number, week_number = index
            logger.info(f"Processing week number {week_number} of year {year_number}")
            mean_series = row.mean().dropna()
            year = get_year_cached(year_number)
            week, _ = Week.objects.get_or_create(
                week_number=week_number,
                years__year_number=year_number,
            )
            if week.years.count() == 0:
                week.years.add(year)
            values = get_measurements(mean_series, station.name)
            week_data, _ = WeekData.objects.get_or_create(station=station, week=week)
            for item in values.items():
                parameter = get_parameter(item[0])
                if not week_data.measurements.filter(
                    value=item[1], parameter=parameter
                ):
                    measurement = Measurement.objects.create(
                        value=item[1], parameter=parameter
                    )
                    week_data.measurements.add(measurement)


def save_days(df, stations):
    logger.info("Processing days...")
    days = df.groupby(
        [df.index.year, df.index.month, df.index.isocalendar().week, df.index.day]
    )
    for station in stations:
        measurements = []
        day_datas = {}
        day_data_objs = []
        for index, row in days:
            year_number, month_number, week_number, day_number = index
            date = datetime(year_number, month_number, day_number)
            mean_series = row.mean().dropna()
            year = get_year_cached(year_number)
            month = get_month_cached(year, month_number)
            week = get_week_cached(year, week_number)
            day, _ = get_or_create_day_row_cached(date, year, month, week)
            values = get_measurements(mean_series, station.name)
            day_data = DayData(station=station, day=day)
            day_data_objs.append(day_data)
            ret_mes = get_measurement_objects(values)
            measurements += ret_mes
            day_datas[index] = {"data": day_data, "measurements": ret_mes}
        bulk_create_rows(DayData, day_data_objs, measurements, day_datas)


def save_hours(df, stations):
    logger.info("Processing hours... ")
    hours = df.groupby([df.index.year, df.index.month, df.index.day, df.index.hour])
    for station in stations:
        measurements = []
        hour_datas = {}
        hour_data_objs = []
        for index, row in hours:
            year_number, month_number, day_number, hour_number = index
            mean_series = row.mean().dropna()
            date = datetime(year_number, month_number, day_number)
            day = get_day_cached(date)
            hour, _ = get_or_create_hour_row_cached(day, hour_number)
            values = get_measurements(mean_series, station.name)
            hour_data = HourData(station=station, hour=hour)
            hour_data_objs.append(hour_data)
            ret_mes = get_measurement_objects(values)
            measurements += ret_mes
            hour_datas[index] = {"data": hour_data, "measurements": ret_mes}
        bulk_create_rows(HourData, hour_data_objs, measurements, hour_datas)


def save_current_year(stations, year_number, end_month_number):
    logger.info(f"Saving current year {year_number}")
    year = get_year_cached(year_number)
    for station in stations:
        measurements = {}
        num_months = 0
        for month_number in range(1, end_month_number + 1):
            month = get_month_cached(year, month_number)
            month_data = get_month_data_cached(station, month)
            if not month_data:
                logger.debug(f"Month number {month_number} not found")
                continue
            else:
                num_months += 1
            for measurement in month_data.measurements.all():
                key = measurement.parameter
                measurements[key] = measurements.get(key, 0) + measurement.value
        # get_or_create, if year changed the year needs to be created
        year_data, _ = get_or_create_row_cached(
            YearData,
            (
                ("station", station),
                ("year", year),
            ),
        )
        year_data.measurements.all().delete()
        for parameter in station.parameters.all():
            try:
                value = round(measurements[parameter] / num_months, 2)
            except KeyError:
                continue
            measurement = Measurement.objects.create(value=value, parameter=parameter)
            year_data.measurements.add(measurement)


def clear_cache():
    get_or_create_row_cached.cache_clear()
    get_or_create_hour_row_cached.cache_clear()
    get_or_create_day_row_cached.cache_clear()
    get_row_cached.cache_clear()
    get_year_cached.cache_clear()
    get_year_data_cached.cache_clear()
    get_month_cached.cache_clear()
    get_month_data_cached.cache_clear()
    get_week_cached.cache_clear()
    get_day_cached.cache_clear()
    get_parameter.cache_clear()


def delete_months(months_qs):
    month_datas_qs = MonthData.objects.filter(month__in=months_qs)
    [m.measurements.all().delete() for m in month_datas_qs]
    days_qs = Day.objects.filter(month__in=months_qs)
    day_datas_qs = DayData.objects.filter(day__in=days_qs)
    [m.measurements.all().delete() for m in day_datas_qs]
    hours_qs = Hour.objects.filter(day__in=days_qs)
    hour_datas_qs = HourData.objects.filter(hour__in=hours_qs)
    [m.measurements.all().delete() for m in hour_datas_qs]
    months_qs.delete()
    days_qs.delete()
    hours_qs.delete()


def save_measurements(df, initial_import=False):
    stations = [station for station in Station.objects.all()]
    end_date = df.index[-1]
    start_date = df.index[0]
    if initial_import:
        Year.objects.all().delete()
        Month.objects.all().delete()
        Week.objects.all().delete()
        Day.objects.all().delete()
        Hour.objects.all().delete()
        save_years(df, stations)
        save_months(df, stations)
    else:
        create_row(Year, {"year_number": start_date.year})
        year = get_year_cached(year_number=start_date.year)
        # Handle year change in dataframe
        if df.index[-1].year > df.index[0].year:
            months_qs = Month.objects.filter(
                year=year, month_number__gte=start_date.month, month_number__lte=12
            )
            delete_months(months_qs)
            create_row(Year, {"year_number": end_date.year})
            year = get_year_cached(year_number=end_date.year)
            Month.objects.filter(
                year=year, month_number__gte=1, month_number__lte=end_date.month
            )
            save_months(df, stations)
            save_current_year(stations, start_date.year, 12)
            save_current_year(stations, end_date.year, end_date.month)
        else:
            months_qs = Month.objects.filter(
                year=year,
                month_number__gte=start_date.month,
                month_number__lte=end_date.month,
            )
            delete_months(months_qs)
            save_months(df, stations)
            save_current_year(stations, start_date.year, end_date.month)

    save_weeks(df, stations)
    save_days(df, stations)
    save_hours(df, stations)
    import_state = ImportState.load()
    import_state.year_number = end_date.year
    import_state.month_number = end_date.month
    import_state.save()
    if logger.level <= logging.DEBUG:
        queries_time = sum([float(s["time"]) for s in connection.queries])
        logger.debug(
            f"queries total execution time: {queries_time} Num queries: {len(connection.queries)}"
        )
        reset_queries()
        logger.debug(
            f"get_or_create_row_cached {get_or_create_row_cached.cache_info()}"
        )
        logger.debug(
            f"get_or_create_hour_row_cached {get_or_create_hour_row_cached.cache_info()}"
        )
        logger.debug(
            f"get_or_create_day_row_cached {get_or_create_day_row_cached.cache_info()}"
        )
        logger.debug(f"get_row_cached  {get_row_cached.cache_info()}")
        logger.debug(f"get_year_cached {get_year_cached.cache_info()}")
        logger.debug(f"get_year_cached {get_year_data_cached.cache_info()}")
        logger.debug(f"get_month_cached {get_month_cached.cache_info()}")
        logger.debug(f"get_month_cached {get_month_data_cached.cache_info()}")
        logger.debug(f"get_week_cached {get_week_cached.cache_info()}")
        logger.debug(f"get_day_cached {get_day_cached.cache_info()}")
        logger.debug(f"get_parameter {get_parameter.cache_info()}")


def save_parameter_types(df, initial_import=False):
    if initial_import:
        Parameter.objects.all().delete()
    for station in Station.objects.all():
        for parameter_name in OBSERVABLE_PARAMETERS:
            key = f"{station.name} {parameter_name}"
            if key in df.columns:
                parameter, _ = get_or_create_row(Parameter, {"name": parameter_name})
                station.parameters.add(parameter)


def save_stations(stations, initial_import_stations=False):
    num_created = 0
    if initial_import_stations:
        Station.objects.all().delete()
    object_ids = list(Station.objects.all().values_list("id", flat=True))
    for station in stations:
        obj, created = get_or_create_row(
            Station,
            {
                "name": station["name"],
                "location": station["location"],
                "geo_id": station["geoId"],
            },
        )
        if obj.id in object_ids:
            object_ids.remove(obj.id)
        if created:
            num_created += 1
    Station.objects.filter(id__in=object_ids).delete()
    logger.info(f"Deleted {len(object_ids)} obsolete air monitoring stations")
    num_stations = Station.objects.all().count()
    logger.info(
        f"Created {num_created} air monitoring stations of total {num_stations}."
    )


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--initial-import",
            action="store_true",
            help="Delete all data and reset import state",
        )
        parser.add_argument(
            "--initial-import-with-stations",
            action="store_true",
            help="Delete also all stations",
        )

    def handle(self, *args, **options):
        start_time = datetime.now()
        import_state = ImportState.load()
        initial_import = options.get("initial_import", False)
        initial_import_stations = options.get("initial_import_with_stations", False)
        if initial_import_stations:
            initial_import = True

        if initial_import:
            import_state.year_number = START_YEAR
            import_state.month_number = 1
            import_state.save()

        stations = get_stations()
        save_stations(stations, initial_import_stations)
        df = get_dataframe(
            stations,
            import_state.year_number,
            import_state.month_number,
            initial_import,
        )
        save_parameter_types(df, initial_import)
        save_measurements(df, initial_import)
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Imported observations until:{str(df.index[-1])}")
        logger.info(f"Imported air monitoring data in: {duration}")
