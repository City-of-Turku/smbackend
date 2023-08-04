import logging
import xml.etree.ElementTree as Et
from datetime import datetime
from functools import lru_cache

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta
from django.contrib.gis.geos import Point, Polygon
from django.core.management import BaseCommand

from air_monitoring.models import (  # ImportState,
    Day,
    DayData,
    Hour,
    HourData,
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

logger = logging.getLogger(__name__)

START_YEAR = 2021
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

SRID = 4326
# URL = "https://data.fmi.fi/fmi-apikey/0fe6aa7c-de21-4f68-81d0-ed49c0409295/
# wfs?request=getFeature&storedquery_id=urban::observations::airquality::hourly::timevaluepair
# &geoId=-100823&parameters=AQINDEX_PT1H_avg&parameters=PM10_PT1H_avg&parameters=SO2_PT1H_avg&who=fmi&startTime=2023-01-01T12:20Z&endTime=2023-02-01T12:20Z"
URL = "https://data.fmi.fi/fmi-apikey/0fe6aa7c-de21-4f68-81d0-ed49c0409295/wfs"
AQINDEX_PT1H_AVG = "AQINDEX_PT1H_avg"
PM10_PT1H_AVG = "PM10_PT1H_avg"
SO2_PT1H_AVG = "SO2_PT1H_avg"

OBSERVABLE_PARAMETERS = [AQINDEX_PT1H_AVG, PM10_PT1H_AVG, SO2_PT1H_AVG]
OBSERVABLE_PARAMETERS = [AQINDEX_PT1H_AVG, PM10_PT1H_AVG]


# NOTE, No more than 10000 hours is allowed in on request.
PARAMS = {
    "request": "getFeature",
    "storedquery_id": "urban::observations::airquality::hourly::timevaluepair",
    "geoId": None,
    "parameters": None,
    "who": "fmi",
    "startTime": None,
    "endTime": None,
}
NAMESPACES = {
    "wfs": "http://www.opengis.net/wfs/2.0",
    "om": "http://www.opengis.net/om/2.0",
    "omso": "http://inspire.ec.europa.eu/schemas/omso/3.0",
    "sams": "http://www.opengis.net/samplingSpatial/2.0",
    "wml2": "http://www.opengis.net/waterml/2.0",
    "ef": "http://inspire.ec.europa.eu/schemas/ef/4.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "gml": "http://www.opengis.net/gml/3.2",
}
STATION_URL = (
    "https://data.fmi.fi/fmi-apikey/0fe6aa7c-de21-4f68-81d0-ed49c0409295/"
    "wfs?request=getFeature&storedquery_id=fmi::ef::stations"
)


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
                location = Point(float(positions[1]), float(positions[0]), srid=SRID)
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


def get_dataframe(station, from_year=None, from_month=None):
    stations = get_stations()
    current_date_time = datetime.now()

    if from_year and from_month:
        from_date_time = datetime.strptime(
            f"{from_year}-{from_month}-01T00:00:00Z", TIME_FORMAT
        )
    else:
        from_date_time = datetime(START_YEAR, 1, 1)

    column_data = {}
    for station_index, station in enumerate(stations[0:2]):
        print("-" * 40)
        print(f"--- {station['name']} ----")
        for parameter in OBSERVABLE_PARAMETERS:
            data = {}
            tmp_data = []
            start_date_time = from_date_time
            while start_date_time.year <= current_date_time.year:
                params = PARAMS
                params["geoId"] = f"-{station['geoId']}"
                params["parameters"] = parameter
                params["startTime"] = f"{start_date_time.year}-01-01T00:00Z"
                if start_date_time.year == current_date_time.year:
                    params["endTime"] = current_date_time.strftime(TIME_FORMAT)
                else:
                    params["endTime"] = f"{start_date_time.year}-12-31T23:59Z"

                response = requests.get(URL, params=params)

                print(response.url)
                if response.status_code == 200:
                    root = Et.fromstring(response.content)
                    # members = root.findall(
                    #     "wfs:member", {"wfs": "http://www.opengis.net/wfs/2.0"}
                    # )
                    # feature_of_interest = root.findall(
                    #     ".//om:featureOfInterest",
                    #     {"om": "http://www.opengis.net/om/2.0"},
                    # )
                    observation_series = root.findall(
                        ".//omso:PointTimeSeriesObservation",
                        {"omso": "http://inspire.ec.europa.eu/schemas/omso/3.0"},
                    )
                    print("len observations", len(observation_series))
                    if len(observation_series) != 1:
                        print("Error!, Observation series != 1")
                        start_date_time += relativedelta(years=1)
                        continue

                    for serie in observation_series:
                        # feature = serie.find(
                        #     ".//sams:SF_SpatialSamplingFeature", NAMESPACES
                        # )
                        # time_serie = serie.findall(
                        #     ".//wml2:MeasurementTimeseries", NAMESPACES
                        # )
                        measurements = root.findall(
                            ".//wml2:MeasurementTVP", NAMESPACES
                        )
                        print(len(measurements))
                        for measurement in measurements:
                            time = measurement.find("wml2:time", NAMESPACES).text
                            value = float(
                                measurement.find("wml2:value", NAMESPACES).text
                            )
                            # print(f"time: {time} value: {value}")
                            data[time] = value
                            tmp_data.append(value)
                else:
                    print("Error retrieving data")
                    print("Resp ", response.content)
                start_date_time += relativedelta(years=1)
                print(start_date_time)
            column_name = f"{station['name']} {params['parameters']}"
            column_data[column_name] = data

    start_date_time = datetime(START_YEAR, 1, 1, 0, 0)

    df = pd.DataFrame.from_dict(column_data)
    # df.to_csv("fmi.csv")
    df = df.reset_index()
    df["Date"] = pd.to_datetime(df["index"], format=TIME_FORMAT)
    df = df.drop("index", axis=1)
    df = df.set_index("Date")
    # Fill missing cells with the value 0
    df = df.fillna(0)
    return df


def hashable_dict(d):
    return dict(sorted(d.items()))


def get_or_create_row(model, filter):
    results = model.objects.filter(**filter)
    if results.exists():
        return results.first(), False
    else:
        return model.objects.create(**filter), True


@lru_cache(maxsize=1024)
# Use tuple as it is immutable and is hashable for lru_cache
def get_row_cached(model, filter: tuple):
    filter = {key: value for key, value in filter}
    results = model.objects.filter(**filter)
    if results.exists():
        return results.first()
    else:
        return None


def get_row(model, filter):
    results = model.objects.filter(**filter)
    if results.exists():
        return results.first()
    else:
        return None


def get_measurements(mean_series, station_name):
    values = {}
    for parameter in OBSERVABLE_PARAMETERS:
        key = f"{station_name} {parameter}"
        values[parameter] = mean_series.get(key, 0)
    return values


@lru_cache(maxsize=16)
def get_parameter(name):
    try:
        return Parameter.objects.get(name=name)
    except Parameter.DoesNotExist:
        return None


def save_measurement_values(measurements, dst_obj):
    for item in measurements.items():
        parameter = get_parameter(item[0])
        measurement, _ = get_or_create_row(
            Measurement, {"value": item[1], "parameter": parameter}
        )
        dst_obj.measurements.add(measurement)


def save_years(df, stations):
    logger.info("Saving years...")
    years = df.groupby(df.index.year)
    for index, row in years:
        logger.info(f"Saving year {index}")
        mean_series = row.mean()
        for station in stations:
            year, _ = get_or_create_row(
                Year, {"station": station, "year_number": index}
            )
            measurements = get_measurements(mean_series, station.name)
            year_data, _ = get_or_create_row(
                YearData, {"station": station, "year": year}
            )
            save_measurement_values(measurements, year_data)


def save_months(df, stations):
    logger.info("Saving months...")
    months = df.groupby([df.index.year, df.index.month])
    for index, row in months:
        year_number, month_number = index
        logger.info(f"Saving month {month_number} of year {year_number}")
        mean_series = row.mean()
        for station in stations:
            # year = get_row(Year, hashable_dict({"station": station, "year_number": year_number}))
            year = get_row_cached(
                Year, (("station", station), ("year_number", year_number))
            )
            month, _ = get_or_create_row(
                Month, {"station": station, "year": year, "month_number": month_number}
            )
            measurements = get_measurements(mean_series, station.name)
            month_data, _ = get_or_create_row(
                MonthData, {"station": station, "year": year, "month": month}
            )
            save_measurement_values(measurements, month_data)


def save_weeks(df, stations):
    logger.info("Saving weeks...")
    weeks = df.groupby([df.index.year, df.index.isocalendar().week])
    for index, row in weeks:
        year_number, week_number = index
        logger.info(f"Saving week number {week_number} of year {year_number}")
        mean_series = row.mean()
        for station in stations:
            # year = get_row(Year, {"station": station, "year_number": year_number})
            year = get_row_cached(
                Year, (("station", station), ("year_number", year_number))
            )

            # week = get_or_create_row(Week, {"station": station,"years": year_number, "week_number": week_number})
            week, _ = Week.objects.get_or_create(
                station=station,
                week_number=week_number,
                years__year_number=year_number,
            )
            if week.years.count() == 0:
                week.years.add(year)
            measurements = get_measurements(mean_series, station.name)
            week_data, _ = get_or_create_row(
                WeekData, {"station": station, "week": week}
            )
            save_measurement_values(measurements, week_data)


def save_days(df, stations):
    logger.info("Saving days...")
    days = df.groupby(
        [df.index.year, df.index.month, df.index.isocalendar().week, df.index.day]
    )
    prev_week_number = None
    for index, row in days:
        year_number, month_number, week_number, day_number = index
        date = datetime(year_number, month_number, day_number)
        mean_series = row.mean()
        for station in stations:
            # year = get_row(Year, {"station": station, "year_number": year_number})
            year = get_row_cached(
                Year, (("station", station), ("year_number", year_number))
            )

            # month = get_row(
            #     Month, {"station": station, "year": year, "month_number": month_number}
            # )
            month = get_row_cached(
                Month,
                (("station", station), ("year", year), ("month_number", month_number)),
            )
            # week = get_row(
            #     Week, {"station": station, "years": year, "week_number": week_number}
            # )
            week = get_row_cached(
                Week,
                (("station", station), ("years", year), ("week_number", week_number)),
            )
            day, _ = get_or_create_row(
                Day,
                {
                    "station": station,
                    "date": date,
                    "weekday_number": date.weekday(),
                    "year": year,
                    "month": month,
                    "week": week,
                },
            )
            values = get_measurements(mean_series, station.name)
            day_data, _ = get_or_create_row(DayData, {"station": station, "day": day})
            save_measurement_values(values, day_data)
            if not prev_week_number or prev_week_number != week_number:
                prev_week_number = week_number
                logger.info(f"Saved days for week {week_number} of year {year_number}")


def save_hours(df, stations):
    logger.info("Saving hours...")
    hours = df.groupby([df.index.year, df.index.month, df.index.day, df.index.hour])
    for i_station, station in enumerate(stations):
        # prev_day_number = None
        # prev_month_number = None
        for index, row in hours:
            year_number, month_number, day_number, hour_number = index
            mean_series = row.mean()
            date = datetime(year_number, month_number, day_number)
            day = get_row_cached(Day, (("date", date), ("station", station)))
            hour, _ = get_or_create_row(
                Hour, {"station": station, "day": day, "hour_number": hour_number}
            )
            values = get_measurements(mean_series, station.name)
            hour_data, _ = get_or_create_row(
                HourData, {"station": station, "hour": hour}
            )
            save_measurement_values(values, hour_data)
            if i_station == len(stations) - 1:
                logger.info(
                    f"Saved hour data for day {day_number}, month {month_number} year {year_number}"
                )
            # breakpoint()


def save_measurements(df):

    # import_state =
    # If importstate save current year
    stations = [station for station in Station.objects.all()]
    save_years(df, stations)
    save_months(df, stations)
    save_weeks(df, stations)
    save_days(df, stations)
    save_hours(df, stations)


def save_parameter_types(df):
    for station in Station.objects.all():
        for parameter_name in OBSERVABLE_PARAMETERS:
            key = f"{station.name} {parameter_name}"
            if key in df.columns:
                parameter, _ = get_or_create_row(Parameter, {"name": parameter_name})
                station.parameters.add(parameter)


def save_stations(stations):
    num_created = 0
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
        # Station.objects.get_or_create(
        #     name=station["name"], location=station["location"], geo_id=station["geoId"]
        # )
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

    """
    Algo:
    Fetch one parameter per station,
    as there is limt of how many hours can be fetched, fetch one year.

    """

    def handle(self, *args, **options):
        start_time = datetime.now()

        # Note station on initial import
        stations = get_stations()
        save_stations(stations)
        df = get_dataframe(stations, 2022, 1)
        save_parameter_types(df)
        save_measurements(df)
        end_time = datetime.now()
        duration = end_time - start_time

        logger.info(f"Importing of air monitoring data finnished in: {duration}")

        breakpoint()
