from django.db.models import Q

DIRECTIONS = ("k", "p")
MOVEMENT_TYPES = ("a", "p", "j", "b", "s")
STATION_TYPES = tuple(
    (f"{movement_type}k", f"{movement_type}p", f"{movement_type}t")
    for movement_type in MOVEMENT_TYPES
)
TYPE_DIRS = [field.upper() for fields in STATION_TYPES for field in fields[:2]]
ALL_TYPE_DIRS = [field.upper() for fields in STATION_TYPES for field in fields]
VALUE_FIELDS = [f"value_{field}" for fields in STATION_TYPES for field in fields]
HOUR_VALUE_FIELDS = [f"values_{field}" for fields in STATION_TYPES for field in fields]
DATA_TYPE_CHOICES = [fields[2][0] for fields in STATION_TYPES]
DATA_TYPE_TOTAL_FIELDS = {
    fields[2][0]: f"value_{fields[2]}" for fields in STATION_TYPES
}


def build_nonzero_total_q(prefix="value_"):
    q_exp = Q()
    for _, _, total_field in STATION_TYPES:
        q_exp |= Q(**{f"{prefix}{total_field}__gt": 0})
    return q_exp
