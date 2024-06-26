def lerp(a, b, w):
    "Linear interpolate between a and b. w is the weight, value between 0-1"
    "i.e. w=.25 returns .25*a + .75*b"
    return (w * a) + ((1 - w) * b)


def generate_coords(start_lon, start_lat, end_lon, end_lat, num_coords):
    """
    Generates a line of coordinates from (start_lon, start_lat) to (end_lon, end_lat).
    Number of coordinates that will be generated is defined by the num_coords param.
    The coordinates are generated by linear interpolating between the start and end.
    """
    coords = []
    for i in range(num_coords):
        lerp_value = i / num_coords
        lon = lerp(start_lon, end_lon, lerp_value)
        lat = lerp(start_lat, end_lat, lerp_value)
        coords.append((lon, lat))
    return coords
