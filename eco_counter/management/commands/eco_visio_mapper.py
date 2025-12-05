"""
Eco-Visio API Data Mapper

This module provides data mapping functionality to transform Eco-Visio API
responses into the DataFrame format expected by the existing eco_counter import logic.

The existing system uses Finnish abbreviations for movement types and directions:
- Movement types: A (auto/car), P (pyörä/bike), J (jalankulkija/pedestrian), B (bussi/bus)
- Directions: K (keskustaan/towards center), P (poispäin/away from center)

The Eco-Visio API uses:
- Travel modes: bike, pedestrian, car, motorized, bus, etc.
- Directions: in, out, undefined
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger("eco_counter")


# Mapping from Eco-Visio travel modes to existing movement type codes
TRAVEL_MODE_MAPPING = {
    "bike": "P",  # Pyörä (bicycle)
    "pedestrian": "J",  # Jalankulkija (pedestrian)
    "car": "A",  # Auto (car)
    "motorized": "A",  # Also maps to Auto
    "bus": "B",  # Bussi (bus)
    # Additional modes that might be encountered
    "horse": None,  # Not mapped
    "kayak": None,  # Not mapped
    "scooter": "P",  # Map to bicycle category
    "motorbike": "A",  # Map to car/motorized category
    "truck": "A",  # Map to car/motorized category
    "cargobike": "P",  # Map to bicycle category
    "minibus": "B",  # Map to bus category
    "undefined": None,  # Not mapped
}

# Mapping from Eco-Visio directions to existing direction codes
DIRECTION_MAPPING = {
    "in": "K",  # Keskustaan (towards center)
    "out": "P",  # Poispäin (away from center)
    "undefined": None,  # Will be handled specially
}


def get_movement_type_code(travel_mode: str) -> Optional[str]:
    """
    Convert Eco-Visio travel mode to existing movement type code.

    Args:
        travel_mode: Eco-Visio travel mode (bike, pedestrian, car, etc.)

    Returns:
        Movement type code (A, P, J, B) or None if not mappable
    """
    return TRAVEL_MODE_MAPPING.get(travel_mode.lower())


def get_direction_code(direction: str) -> Optional[str]:
    """
    Convert Eco-Visio direction to existing direction code.

    Args:
        direction: Eco-Visio direction (in, out, undefined)

    Returns:
        Direction code (K, P) or None if undefined
    """
    return DIRECTION_MAPPING.get(direction.lower())


def get_column_suffix(travel_mode: str, direction: str) -> Optional[str]:
    """
    Get the column suffix for a given travel mode and direction combination.

    Args:
        travel_mode: Eco-Visio travel mode
        direction: Eco-Visio direction

    Returns:
        Column suffix (e.g., "AK", "PP", "JK") or None if not mappable

    Examples:
        >>> get_column_suffix("bike", "in")
        "PK"
        >>> get_column_suffix("pedestrian", "out")
        "JP"
        >>> get_column_suffix("car", "in")
        "AK"
    """
    movement_code = get_movement_type_code(travel_mode)
    direction_code = get_direction_code(direction)

    if movement_code is None:
        logger.debug(f"Travel mode '{travel_mode}' not mapped to any movement type")
        return None

    if direction_code is None:
        logger.debug(
            f"Direction '{direction}' not mapped. "
            f"For undefined directions, data will be split equally between K and P."
        )
        return None

    return f"{movement_code}{direction_code}"


def transform_raw_traffic_to_dataframe(
    raw_traffic_data: List[Dict],
    station_name: str,
) -> pd.DataFrame:
    """
    Transform Eco-Visio raw traffic API response to DataFrame format.

    The output DataFrame has:
    - 'startTime' column with timestamps in format '%Y-%m-%dT%H:%M'
    - Columns for each station/type combination (e.g., "Station AK", "Station PP")

    Args:
        raw_traffic_data: List of traffic series from Eco-Visio API
            Each series has: travelMode, direction, data (list of timestamp/counts)
        station_name: Name of the station to use in column names

    Returns:
        DataFrame with startTime and station columns

    Example API response format:
        [
            {
                "travelMode": "bike",
                "direction": "in",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+02:00", "granularity": "PT15M", "counts": 5},
                    ...
                ]
            },
            ...
        ]
    """
    if not raw_traffic_data:
        logger.warning(f"No traffic data to transform for station '{station_name}'")
        return pd.DataFrame(columns=["startTime"])

    # Collect all data points organized by timestamp
    timestamp_data: Dict[str, Dict[str, float]] = {}
    columns_seen = set()

    for series in raw_traffic_data:
        travel_mode = series.get("travelMode", "undefined")
        direction = series.get("direction", "undefined")
        data_points = series.get("data", [])

        column_suffix = get_column_suffix(travel_mode, direction)

        if column_suffix is None and direction == "undefined":
            # For undefined direction, split counts between K and P
            _process_undefined_direction_data(
                data_points,
                station_name,
                travel_mode,
                timestamp_data,
                columns_seen,
            )
        elif column_suffix is not None:
            column_name = f"{station_name} {column_suffix}"
            columns_seen.add(column_name)

            for point in data_points:
                timestamp = _normalize_timestamp(point.get("timestamp"))
                if timestamp is None:
                    continue

                counts = point.get("counts", 0) or 0

                if timestamp not in timestamp_data:
                    timestamp_data[timestamp] = {}

                # Add to existing count if already present (for aggregation)
                current_value = timestamp_data[timestamp].get(column_name, 0)
                timestamp_data[timestamp][column_name] = current_value + counts
        else:
            logger.debug(
                f"Skipping unmapped travel mode '{travel_mode}' with direction '{direction}'"
            )

    # Build DataFrame
    if not timestamp_data:
        logger.warning(f"No valid data points found for station '{station_name}'")
        return pd.DataFrame(columns=["startTime"])

    # Sort timestamps and build rows
    sorted_timestamps = sorted(timestamp_data.keys())
    rows = []

    for ts in sorted_timestamps:
        row = {"startTime": ts}
        row.update(timestamp_data[ts])
        rows.append(row)

    df = pd.DataFrame(rows)

    # Ensure all expected columns exist, fill with 0 if missing
    for col in columns_seen:
        if col not in df.columns:
            df[col] = 0

    logger.info(
        f"Transformed {len(df)} rows with columns {list(df.columns)} "
        f"for station '{station_name}'"
    )

    # Fill NaN values with 0
    df = df.fillna(0)

    return df


def _process_undefined_direction_data(
    data_points: List[Dict],
    station_name: str,
    travel_mode: str,
    timestamp_data: Dict[str, Dict[str, float]],
    columns_seen: set,
) -> None:
    """
    Process data with undefined direction by splitting counts equally between K and P.

    Args:
        data_points: List of data points from API
        station_name: Name of the station
        travel_mode: Eco-Visio travel mode
        timestamp_data: Dict to store timestamp -> column -> value mapping
        columns_seen: Set to track seen column names
    """
    movement_code = get_movement_type_code(travel_mode)
    if movement_code is None:
        return

    column_k = f"{station_name} {movement_code}K"
    column_p = f"{station_name} {movement_code}P"
    columns_seen.add(column_k)
    columns_seen.add(column_p)

    for point in data_points:
        timestamp = _normalize_timestamp(point.get("timestamp"))
        if timestamp is None:
            continue

        counts = point.get("counts", 0) or 0
        # Split counts equally between directions
        split_count = counts / 2.0

        if timestamp not in timestamp_data:
            timestamp_data[timestamp] = {}

        # Add to existing values
        current_k = timestamp_data[timestamp].get(column_k, 0)
        current_p = timestamp_data[timestamp].get(column_p, 0)
        timestamp_data[timestamp][column_k] = current_k + split_count
        timestamp_data[timestamp][column_p] = current_p + split_count


def _normalize_timestamp(timestamp_str: Optional[str]) -> Optional[str]:
    """
    Normalize timestamp to the format expected by save_observations().

    The expected format is: '%Y-%m-%dT%H:%M'

    Args:
        timestamp_str: ISO 8601 timestamp string from API

    Returns:
        Normalized timestamp string or None if invalid
    """
    if not timestamp_str:
        return None

    try:
        # Parse ISO 8601 timestamp (handles timezone)
        # Example: "2024-01-01T00:00:00+02:00" -> "2024-01-01T00:00"
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        # Convert to local time representation (strip timezone for consistency)
        return dt.strftime("%Y-%m-%dT%H:%M")
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
        return None


def combine_station_dataframes(dataframes: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Combine multiple station DataFrames into a single DataFrame.

    All DataFrames should have 'startTime' as a column. The resulting DataFrame
    will have all timestamps from all inputs and all station columns.

    Args:
        dataframes: List of DataFrames from transform_raw_traffic_to_dataframe()

    Returns:
        Combined DataFrame with all stations' data
    """
    if not dataframes:
        return pd.DataFrame(columns=["startTime"])

    # Filter out empty dataframes
    valid_dfs = [df for df in dataframes if not df.empty and "startTime" in df.columns]

    if not valid_dfs:
        return pd.DataFrame(columns=["startTime"])

    if len(valid_dfs) == 1:
        return valid_dfs[0]

    # Merge all dataframes on startTime
    result = valid_dfs[0]
    for df in valid_dfs[1:]:
        result = pd.merge(result, df, on="startTime", how="outer")

    # Sort by timestamp
    result = result.sort_values("startTime").reset_index(drop=True)

    # Fill NaN values with 0
    result = result.fillna(0)

    logger.info(
        f"Combined {len(valid_dfs)} station DataFrames into {len(result)} rows "
        f"with {len(result.columns)} columns"
    )

    return result


def get_supported_travel_modes() -> List[str]:
    """
    Get list of travel modes that are supported for mapping.

    Returns:
        List of supported travel mode strings
    """
    return [mode for mode, code in TRAVEL_MODE_MAPPING.items() if code is not None]


def get_travel_mode_description(travel_mode: str) -> str:
    """
    Get human-readable description of a travel mode mapping.

    Args:
        travel_mode: Eco-Visio travel mode

    Returns:
        Description string
    """
    code = TRAVEL_MODE_MAPPING.get(travel_mode.lower())
    if code is None:
        return f"{travel_mode} -> (not mapped)"

    code_names = {
        "A": "Auto (car)",
        "P": "Pyörä (bicycle)",
        "J": "Jalankulkija (pedestrian)",
        "B": "Bussi (bus)",
    }
    return f"{travel_mode} -> {code} ({code_names.get(code, 'unknown')})"

