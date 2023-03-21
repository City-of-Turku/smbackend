from django.conf import settings
from django.contrib.gis.gdal import SpatialReference

from mobility_data.models.mobile_unit import MobileUnit
from services.models import Service, ServiceNode, Unit

LANGUAGES = {k: v.lower() for k, v in settings.LANGUAGES}
DEFAULT_SRS = SpatialReference(4326)
SEARCHABLE_MODEL_TYPE_NAMES = (
    "Unit",
    "Service",
    "ServiceNode",
    "AdministrativeDivision",
    "Address",
    "MobileUnit",
)
HYPHENATE_MODELS = [Unit, Service, ServiceNode, MobileUnit]
QUERY_PARAM_TYPE_NAMES = [m.lower() for m in SEARCHABLE_MODEL_TYPE_NAMES]
# None will slice to the end of list, e.g. no limit.
DEFAULT_MODEL_LIMIT_VALUE = None
# The limit value for the search query that search the search_view. "NULL" = no limit
DEFAULT_SEARCH_SQL_LIMIT_VALUE = "NULL"
DEFAULT_TRIGRAM_THRESHOLD = 0.15
