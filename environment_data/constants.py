import types

AIR_QUALITY = "AQ"
WEATHER_OBSERVATION = "WO"
DATA_TYPES_FULL_NAME = {
    AIR_QUALITY: "Air Quality",
    WEATHER_OBSERVATION: "Weather Observation",
}
DATA_TYPE_CHOICES = (
    (AIR_QUALITY, DATA_TYPES_FULL_NAME[AIR_QUALITY]),
    (WEATHER_OBSERVATION, DATA_TYPES_FULL_NAME[WEATHER_OBSERVATION]),
)

DATA_TYPES = types.SimpleNamespace()
DATA_TYPES.AIR_QUALITY = AIR_QUALITY
DATA_TYPES.WEATHER_OBSERVATION = WEATHER_OBSERVATION

VALID_DATA_TYPE_CHOICES = ", ".join(
    [item[0] + f" ({item[1]})" for item in DATA_TYPES_FULL_NAME.items()]
)
DATA_TYPES_LIST = [AIR_QUALITY, WEATHER_OBSERVATION]