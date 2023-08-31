import types

DATA_TYPES = types.SimpleNamespace()
HOUR = "hour"
DAY = "day"
WEEK = "week"
MONTH = "month"
YEAR = "year"
DATA_TYPES.HOUR = HOUR
DATA_TYPES.DAY = DAY
DATA_TYPES.WEEK = WEEK
DATA_TYPES.MONTH = MONTH
DATA_TYPES.YEAR = YEAR
DATETIME_FORMATS = {
    HOUR: "%m-%d",
    DAY: "%m-%d",
    WEEK: "%W",
    MONTH: "%m",
    YEAR: "%Y",
}
