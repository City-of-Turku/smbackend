import logging
import xml.etree.ElementTree as Et
from datetime import datetime, timedelta

import pandas as pd
from dateutil.relativedelta import relativedelta

from environment_data.constants import REQUEST_SESSION

from .air_quality_constants import OBSERVABLE_PARAMETERS, REQUEST_PARAMS, START_YEAR
from .constants import DATA_URL, NAMESPACES, TIME_FORMAT

logger = logging.getLogger(__name__)


def get_dataframe(stations, from_year=START_YEAR, from_month=1, initial_import=False):
    current_date_time = datetime.now()
    if from_year and from_month:
        from_date_time = datetime.strptime(f"{from_year}-01-01T00:00:00Z", TIME_FORMAT)
    column_data = {}
    for station in stations:
        logger.info(f"Fetching data for station {station['name']}")
        for parameter in OBSERVABLE_PARAMETERS:
            data = {}
            start_date_time = from_date_time
            while start_date_time.year <= current_date_time.year:
                params = REQUEST_PARAMS
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

                response = REQUEST_SESSION.get(DATA_URL, params=params)
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
