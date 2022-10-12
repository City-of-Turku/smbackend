import logging
import zoneinfo
from datetime import datetime, timedelta

import numpy as np
import requests
from django.conf import settings
from munigeo.models import AdministrativeDivision, AdministrativeDivisionGeometry

from street_maintenance.models import DEFAULT_SRID, MaintenanceUnit

from .constants import (
    AUTORI_CONTRACTS_URL,
    AUTORI_DATE_TIME_FORMAT,
    AUTORI_EVENTS_URL,
    AUTORI_ROUTES_URL,
    AUTORI_TOKEN_URL,
    AUTORI_VEHICLES_URL,
    INFRAROAD_UNITS_URL,
)

logger = logging.getLogger("street_maintenance")


def get_turku_boundary():
    division_turku = AdministrativeDivision.objects.get(name="Raisio")
    turku_boundary = AdministrativeDivisionGeometry.objects.get(
        division=division_turku
    ).boundary
    turku_boundary.transform(DEFAULT_SRID)
    return turku_boundary


def create_infraroad_maintenance_units():
    response = requests.get(INFRAROAD_UNITS_URL)
    assert (
        response.status_code == 200
    ), "Fetching Maintenance Unit {} status code: {}".format(
        INFRAROAD_UNITS_URL, response.status_code
    )
    for unit in response.json():
        # The names of the unit is derived from the events.
        names = [n for n in unit["last_location"]["events"]]
        MaintenanceUnit.objects.create(
            unit_id=unit["id"], names=names, provider=MaintenanceUnit.INFRAROAD
        )
    logger.info(
        f"Imported {MaintenanceUnit.objects.filter(provider=MaintenanceUnit.INFRAROAD).count()}"
        + " Infraroad mainetance Units."
    )


def get_autori_contract(access_token):
    response = requests.get(
        AUTORI_CONTRACTS_URL, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert (
        response.status_code == 200
    ), "Fetcing Autori Contract {} failed, status code: {}".format(
        AUTORI_CONTRACTS_URL, response.status_code
    )
    return response.json()[0].get("id", None)


def get_autori_event_types(access_token):
    response = requests.get(
        AUTORI_EVENTS_URL, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert (
        response.status_code == 200
    ), " Fetching Autori event types {} failed, status code: {}".format(
        AUTORI_EVENTS_URL, response.status_code
    )
    return response.json()


def create_dict_from_autori_events(list_of_events):
    events = {}
    for event in list_of_events:
        events[event["id"]] = event["operationName"]
    return events


def create_autori_maintenance_units(access_token):
    response = requests.get(
        AUTORI_VEHICLES_URL, headers={"Authorization": f"Bearer {access_token}"}
    )
    assert (
        response.status_code == 200
    ), " Fetching Autori vehicles {} failed, status code: {}".format(
        AUTORI_VEHICLES_URL, response.status_code
    )
    for unit in response.json():
        names = [unit["vehicleTypeName"]]
        MaintenanceUnit.objects.create(
            unit_id=unit["id"], names=names, provider=MaintenanceUnit.AUTORI
        )
    logger.info(
        f"Imported {MaintenanceUnit.objects.filter(provider=MaintenanceUnit.AUTORI).count()}"
        + " Autori(YIT) mainetance Units."
    )


def get_autori_routes(access_token, contract, history_size):
    now = datetime.now()
    end = now.replace(tzinfo=zoneinfo.ZoneInfo("Europe/Helsinki")).strftime(
        AUTORI_DATE_TIME_FORMAT
    )
    start = (
        (now - timedelta(days=history_size))
        .replace(tzinfo=zoneinfo.ZoneInfo("Europe/Helsinki"))
        .strftime(AUTORI_DATE_TIME_FORMAT)
    )

    params = {
        "contract": contract,
        "start": start,
        "end": end,
    }
    response = requests.get(
        AUTORI_ROUTES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
    )
    assert (
        response.status_code == 200
    ), "Fetching Autori routes {}, failed, status code: {}".format(
        AUTORI_ROUTES_URL, response.status_code
    )
    return response.json()


def get_autori_access_token():

    test_data = {
        "grant_type": "client_credentials",
        "scope": settings.AUTORI_SCOPE,
        "client_id": settings.AUTORI_CLIENT_ID,
        "client_secret": settings.AUTORI_CLIENT_SECRET,
    }
    response = requests.post(AUTORI_TOKEN_URL, data=test_data)
    assert (
        response.status_code == 200
    ), "Fetchin oauth2 token from Autori {} failed, status code: {}".format(
        AUTORI_TOKEN_URL, response.status_code
    )
    access_token = response.json().get("access_token", None)
    return access_token


def is_nested_coordinates(coordinates):
    return bool(np.array(coordinates).ndim > 1)
