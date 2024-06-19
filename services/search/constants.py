from django.conf import settings
from django.contrib.gis.gdal import SpatialReference

from mobility_data.models.content_type import ContentType

LANGUAGES = {k: v.lower() for k, v in settings.LANGUAGES}
DEFAULT_SRS = SpatialReference(4326)
SEARCHABLE_MODEL_TYPE_NAMES = (
    "Unit",
    "Service",
    "ServiceNode",
    "AdministrativeDivision",
    "Address",
    "MobileUnit",
    "ContentType",
)
QUERY_PARAM_TYPE_NAMES = [m.lower() for m in SEARCHABLE_MODEL_TYPE_NAMES]
# None will slice to the end of list, i.e., no limit.
DEFAULT_MODEL_LIMIT_VALUE = None
# The limit value for the search query that search the search_view. "NULL" = no limit
DEFAULT_SEARCH_SQL_LIMIT_VALUE = "NULL"
DEFAULT_TRIGRAM_THRESHOLD = 0.15
DEFAULT_RANK_THRESHOLD = 1

HYPHENATE_ADDRESSES_MODIFIED_WITHIN_DAYS = 7
EXCLUDE_CONTENT_TYPE_NAMES = [
    "FoliStop",
    "StreetAreaInformation",
    "TicketMachineSign",
    "TaxiStandSign",
    "SingleTrackRailwayLevelCrossingSign",
    "RailwayLevelCrossingWithBoomsSign",
    "RailwayLevelCrossingWithoutBoomsSign" "ParkingLotSign",
    "PaidParkingSig",
    "ObligationToUseParkingDiscSign",
    "ParkingForbiddenAreaSign",
    "ParkingForbiddenSign",
    "LongDistanceBusStopSign",
    "LocalTrafficBusStopSign",
    "ParkingTerminalSign",
    "CrossWalkSign",
    "RouteForDisabledSign",
    "DisabledParkingSign",
]
EXCLUDE_CONTENT_TYPES = ContentType.objects.filter(
    type_name__in=EXCLUDE_CONTENT_TYPE_NAMES
)
