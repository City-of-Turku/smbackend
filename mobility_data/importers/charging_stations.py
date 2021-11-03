import logging
from django.contrib.gis.geos import Point, Polygon
from django import db
from django.conf import settings
from .utils import (
    get_or_create_content_type,
    delete_mobile_units, 
    fetch_json, 
    GEOMETRY_URL
)
from mobility_data.models import (
    MobileUnit,
    ContentType,
    )
logger = logging.getLogger("mobility_data")

CHARGING_STATIONS_URL = "https://services1.arcgis.com/rhs5fjYxdOG1Et61/ArcGIS/rest/services/ChargingStations/FeatureServer/0/query?f=json&where=1%20%3D%201%20OR%201%20%3D%201&returnGeometry=true&spatialRel=esriSpatialRelIntersects&outFields=LOCATION_ID%2CNAME%2CADDRESS%2CURL%2COBJECTID%2CTYPE"


class ChargingStation:

    def __init__(self, elem, srid=settings.DEFAULT_SRID):
        self.is_active = True
        geometry = elem.get("geometry", None)
        attributes = elem.get("attributes", None)      
        x = geometry.get("x",0)
        y = geometry.get("y",0) 
        self.point = Point(x, y, srid=srid)
        self.name = attributes.get("NAME", "")
        self.address = attributes.get("ADDRESS", "")
        temp_str = self.address.split(",")[1].strip()        
        self.zip_code = temp_str.split(" ")[0]
        self.city = temp_str.split(" ")[1]
        self.url = attributes.get("URL", "")
        self.charger_type = attributes.get("TYPE", "")        
        self.url = attributes.get("URL", "")
        # address fields for service unit model
        self.street_address = self.address.split(",")[0]            
        self.address_postal_full = "{}{}".\
            format(self.address.split(",")[0], self.address.split(",")[1])

def get_filtered_charging_station_objects(json_data=None): 
    """
    Returns a list of ChargingStation objects that are filtered by location.
    """   
    geometry_data = fetch_json(GEOMETRY_URL) 
    # Polygon used the detect if point intersects. i.e. is in the boundries.
    polygon = Polygon(geometry_data["features"][0]["geometry"]["coordinates"][0])  
    if not json_data:
        json_data = fetch_json(CHARGING_STATIONS_URL)
    srid = json_data["spatialReference"]["wkid"]
    objects = [ChargingStation(data, srid=srid) for data in json_data["features"]]
    filtered_objects = []
    # Filter objects
    for object in objects:    
        if polygon.intersects(object.point):
            filtered_objects.append(object)
    logger.info("Filtered: {} charging stations by location to: {}."\
        .format(len(json_data["features"]), len(filtered_objects)))        
    return filtered_objects


@db.transaction.atomic    
def save_to_database(objects, delete_tables=True):
    if delete_tables:
        delete_mobile_units(ContentType.CHARGING_STATION)
    description = "Charging stations in province of SouthWest Finland."  
    name="Charging Station" 
    content_type, _ = get_or_create_content_type(
        ContentType.CHARGING_STATION, name, description)
    
    for object in objects:
        is_active = object.is_active 
        name = object.name
        address = object.address
        extra = {}
        extra["charger_type"] = object.charger_type  
        extra["url"] = object.url
        extra["mobile_unit"] = MobileUnit.objects.create(
            is_active=is_active,
            name=name,
            address=address,
            geometry=object.point,
            extra=extra,
            content_type=content_type
        )
    logger.info("Saved charging stations to database.")