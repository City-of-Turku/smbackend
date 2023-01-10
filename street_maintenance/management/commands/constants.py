from django.conf import settings

KUNTEC_KEY = settings.KUNTEC_KEY
INFRAROAD = "INFRAROAD"
AUTORI = "AUTORI"
KUNTEC = "KUNTEC"
DESTIA = "DESTIA"
PROVIDER_CHOICES = (
    (INFRAROAD, "Infraroad"),
    (AUTORI, "Autori"),
    (KUNTEC, "Kuntec"),
    (DESTIA, "Destia"),
)
PROVIDERS = [INFRAROAD, AUTORI, KUNTEC, DESTIA]

UNITS = "UNITS"
WORKS = "WORKS"
EVENTS = "EVENTS"
ROUTES = "ROUTES"
VEHICLES = "VEHICLES"
CONTRACTS = "CONTRACTS"
TOKEN = "TOKEN"


URLS = {
    KUNTEC: {
        WORKS: "https://mapon.com/api/v1/route/list.json?key={key}&from={start}"
        "&till={end}&include=polyline&unit_id={unit_id}",
        UNITS: f"https://mapon.com/api/v1/unit/list.json?key={KUNTEC_KEY}&include=io_din",
    },
    AUTORI: {
        EVENTS: settings.AUTORI_EVENTS_URL,
        ROUTES: settings.AUTORI_ROUTES_URL,
        VEHICLES: settings.AUTORI_VEHICLES_URL,
        CONTRACTS: settings.AUTORI_CONTRACTS_URL,
        TOKEN: settings.AUTORI_TOKEN_URL,
    },
    INFRAROAD: {
        WORKS: "https://infraroad.fluentprogress.fi/KuntoInfraroad/v1/snowplow/{id}?history={history_size}",
        UNITS: "https://infraroad.fluentprogress.fi/KuntoInfraroad/v1/snowplow/query?since=72hours",
    },
    DESTIA: {
        WORKS: "https://destia.fluentprogress.fi/KuntoDestia/turku/v1/snowplow/{id}?history={history_size}",
        UNITS: "https://destia.fluentprogress.fi/KuntoDestia/turku/v1/snowplow/query?since=72hours",
    },
}


# Events are categorized into main groups:
AURAUS = "auraus"
LIUKKAUDENTORJUNTA = "liukkaudentorjunta"
PUHTAANAPITO = "puhtaanapito"
HIEKANPOISTO = "hiekanpoisto"
# MUUT is set to None as the events are not currently displayed.
MUUT = None

# As data providers have different names for their events, they are mapped
# with this dict, so that every event that does the same has the same name.
# The value is a list, as there can be events that belong to multiple main groups.
# e.g., event "Auraus ja hiekanpoisto".
EVENT_MAPPINGS = {
    "käsihiekotus tai käsilumityöt": [AURAUS, LIUKKAUDENTORJUNTA],
    "laiturin ja asema-alueen auraus": [AURAUS],
    "au": [AURAUS],
    "auraus": [AURAUS],
    "auraus ja sohjonpoisto": [AURAUS],
    "lumen poisajo": [AURAUS],
    "lumensiirto": [AURAUS],
    "etuaura": [AURAUS],
    "alusterä": [AURAUS],
    "sivuaura": [AURAUS],
    "höyläys": [AURAUS],
    "suolaus": [LIUKKAUDENTORJUNTA],
    "suolas": [LIUKKAUDENTORJUNTA],
    "suolaus (sirotinlaite)": [LIUKKAUDENTORJUNTA],
    "liuossuolaus": [LIUKKAUDENTORJUNTA],
    # Hiekoitus
    "hi": [LIUKKAUDENTORJUNTA],
    "su": [LIUKKAUDENTORJUNTA],
    "hiekoitus": [LIUKKAUDENTORJUNTA],
    "hiekotus": [LIUKKAUDENTORJUNTA],
    "hiekoitus (sirotinlaite)": [LIUKKAUDENTORJUNTA],
    "linjahiekoitus": [LIUKKAUDENTORJUNTA],
    "pistehiekoitus": [LIUKKAUDENTORJUNTA],
    "paannejään poisto": [LIUKKAUDENTORJUNTA],
    "sirotin": [LIUKKAUDENTORJUNTA],
    "laiturin ja asema-alueen liukkaudentorjunta": [LIUKKAUDENTORJUNTA],
    "liukkauden torjunta": [LIUKKAUDENTORJUNTA],
    # Kadunpesu
    "pe": [PUHTAANAPITO],
    # Harjaus
    "hj": [PUHTAANAPITO],
    # Hiekanpoisto
    "hn": [PUHTAANAPITO],
    "puhtaanapito": [PUHTAANAPITO],
    "harjaus": [PUHTAANAPITO],
    "pesu": [PUHTAANAPITO],
    "harjaus ja sohjonpoisto": [PUHTAANAPITO],
    "pölynsidonta": [PUHTAANAPITO],
    "hiekanpoisto": [HIEKANPOISTO],
    "lakaisu": [HIEKANPOISTO],
    "muu": [MUUT],
    "muut työt": [MUUT],
    "muu työ": [MUUT],
    "lisätyö": [MUUT],
    "viherhoito": [MUUT],
    "kaivot": [MUUT],
    "metsätyöt": [MUUT],
    "rikkakasvien torjunta": [MUUT],
    "paikkaus": [MUUT],
    "lisälaite 1": [MUUT],
    "lisälaite 2": [MUUT],
    "lisälaite 3": [MUUT],
    "pensaiden hoitoleikkaus": [MUUT],
    "puiden hoitoleikkaukset": [MUUT],
    "mittaus- ja tarkastustyöt": [MUUT],
    "siimaleikkurointi tai niittotyö": [MUUT],
    "liikennemerkkien pesu": [MUUT],
    "tiestötarkastus": [MUUT],
    "roskankeräys": [MUUT],
    "tuntityö": [MUUT],
    "pinnan tasaus": [MUUT],
    "lumivallien madaltaminen": [MUUT],
    "aurausviitoitus ja kinostimet": [MUUT],
    "jääkenttien hoito": [MUUT],
    "leikkipaikkojen tarkastus": [MUUT],
    "kenttien hoito": [MUUT],
    "murskeen ajo varastoihin": [MUUT],
    "huoltoteiden kunnossapito": [MUUT],
    "pysäkkikatosten hoito": [MUUT],
    "liikennemerkkien puhdistus": [MUUT],
    "siirtoajo": [MUUT],
}
TIMESTAMP_FORMATS = {
    INFRAROAD: "%Y-%m-%d %H:%M:%S",
    DESTIA: "%Y-%m-%d %H:%M:%S",
    KUNTEC: "%Y-%m-%dT%H:%M:%SZ",
    AUTORI: "%Y-%m-%d %H:%M:%S%z",
}
# GeometryHistory API list start_date_time parameter format.
START_DATE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
# The number of works(point data with timestamp and event) to be fetched for every unit.
INFRAROAD_DEFAULT_WORKS_FETCH_SIZE = 10000
DESTIA_DEFAULT_WORKS_FETCH_SIZE = 10000
# In days, Note if value is increased the fetch size should also be increased.
INFRAROAD_DEFAULT_WORKS_HISTORY_SIZE = 4
DESTIA_DEFAULT_WORKS_HISTORY_SIZE = 4

# Length of Autori history size in days, max value is 31.
AUTORI_DEFAULT_WORKS_HISTORY_SIZE = 4
AUTORI_MAX_WORKS_HISTORY_SIZE = 31

KUNTEC_DEFAULT_WORKS_HISTORY_SIZE = 4
KUNTEC_MAX_WORKS_HISTORY_SIZE = 31
