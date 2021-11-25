from os import mkdir, listdir, remove
from os.path import isfile, join, exists
import json
import logging
from django.conf import settings
from django.contrib import admin
from django.contrib.gis.geos import LineString
from django.contrib import messages
from .models import (
    BicycleNetwork, 
    BicycleNetworkSource,
    BicycleNetworkPart
)

logger = logging.getLogger("bicycle_network")
SOURCE_DATA_SRID = 3877
CONVERT_TO_SRID = 4326 # if None, No transformations are made and SOURCE_DATA_SRID is used.
UPLOAD_TO = BicycleNetworkSource.UPLOAD_TO
PATH = f"{settings.MEDIA_ROOT}/{UPLOAD_TO}/"
# path where the filtered .geojson files will be stored
FILTERED_PATH = f"{PATH}/filtered/"
# List of properties to include and the type for typecasting   
INCLUDE_PROPERTIES = [
  ("toiminnall", int),
  ("liikennevi", int),
  ("teksti", str),
  ("tienim2", str),
  ("TKU_toiminnall_pp", int),
]

def delete_uploaded_files():
    """
    Deletes all files in PATH.
    """
    [remove(PATH+f) for f in listdir(PATH) if isfile(join(PATH, f))]

def delete_filtered_file(name):
    try:
        remove(f"{FILTERED_PATH}{name}.geojson")
        return True
    except FileNotFoundError:
        return False

def filter_geojson(input_geojson):
    """
    Filters the input_geojson, preservs only properties set in the
    INCLUDE_PROPERTIES. If CONVERT_TO_SRID is set, transforms geometry
    to given srid. 
    """
    out_geojson = {}
    try:
        out_geojson["type"] = input_geojson["type"]
        out_geojson["name"] = input_geojson["name"]
        if not CONVERT_TO_SRID:
            out_geojson["crs"] = input_geojson["crs"]
        out_geojson["features"] = {}
        features = []
        for feature_data in input_geojson["features"]:
            feature = {}
            feature["type"] = "Feature"
            properties_data = feature_data["properties"]    
            properties = {}
            # Include the properties set in INCLUDE_PROPERTIES     
            for prop_name, type_class in INCLUDE_PROPERTIES:
                prop = properties_data.get(prop_name,None)
                if prop:
                    properties[prop_name] = type_class(prop)
                else:
                    properties[prop_name] = None                    
            feature["properties"] = properties

            if CONVERT_TO_SRID:
                try:
                    coords = feature_data["geometry"]["coordinates"]
                    ls = LineString(coords, srid=SOURCE_DATA_SRID)                
                    ls.transform(CONVERT_TO_SRID)
                    feature_data["geometry"]["coordinates"] = ls.coords
                except TypeError as err:                    
                    logger.warning(err)
                    # If transformation is not possible, we execlude the feature
                    # thus it would have errorneous data.
                    continue
            
            feature["geometry"] = feature_data["geometry"]
            features.append(feature)            
    except KeyError:
        # In case a KeyError, which is probably caused by a faulty input geojson
        # file. We retrun False to indicate the error.
        return False, None
    out_geojson["features"] = features
    return True, out_geojson


def save_network_to_db(input_geojson, network_name):
    # BicycleNetwork.objects.all().delete()
    # return
    # Completly delete the network and it's parts before storing it,
    # to ensure the data stored will be up to date. By deleting the 
    # bicycle network the parts referencing to it will also be deleted.
    BicycleNetwork.objects.filter(name=network_name).delete()
    network = BicycleNetwork.objects.create(name=network_name)
    features = input_geojson["features"]
    # Every feature in the input_geojson will be stored as a BicycleNetworkPart.
    for feature in features:
        part = BicycleNetworkPart.objects.create(bicycle_network=network)
        for prop_name, _ in INCLUDE_PROPERTIES:
            setattr(part, prop_name, feature["properties"][prop_name])
        coords = feature["geometry"]["coordinates"] 
        srid=CONVERT_TO_SRID if CONVERT_TO_SRID else SOURCE_DATA_SRID             
        part.geometry = LineString(coords, srid=srid)         
        part.save()


def process_file_obj(file_obj, name):  
    """
    This function is called when continue&save or save&quit is pressed in the
    admin. It Opens the file, calls the filter function and finally stores
    the filtered data to the db and file.
    """
    with open(file_obj.path, "r") as file:
        try:
            input_geojson = json.loads(file.read())
        except json.decoder.JSONDecodeError:
            return False

    success, filtered_geojson = filter_geojson(input_geojson)
    if not success:
        return False
    
    if not exists(FILTERED_PATH):
        mkdir(FILTERED_PATH)
    
    save_network_to_db(filtered_geojson, name)
    
    with open(FILTERED_PATH+name+".geojson", "w") as file:
        json.dump(filtered_geojson, file, ensure_ascii=False)
    return True


class BicycleNetworkSourceAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        # Limit number of instances to One as BicycleNetworkSource is a 
        # singleton class.
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def response_change(self, request, obj):
        # Delete actions sent in request.POST
        delete_actions = [
            "main_network-clear",
            "local_network-clear",
            "quality_lanes-clear"
        ]
        if "_save" or "_continue" in request.POST:   
            success = True
            #If the bicycle_network name does not exist in the request and the 
            #uploaded file exist process the file obj. 
            if "main_network" not in request.POST and isfile(obj.main_network.path):
                success = process_file_obj(obj.main_network, BicycleNetworkSource.MAIN_NETWORK_NAME)
            if "local_network" not in request.POST and isfile(obj.local_network.path):
                success = process_file_obj(obj.local_network, BicycleNetworkSource.LOCAL_NETWORK_NAME)
            if "quality_lanes" not in request.POST and isfile(obj.quality_lanes.path):
                success = process_file_obj(obj.quality_lanes, BicycleNetworkSource.QUALITY_LANES_NAME)
            
            for action in request.POST:
                # Check for delete actions.
                if action in delete_actions:
                    # get the attribute name from action.
                    attr_name = f"{(action.upper())[:-6]}_NAME"
                    name = getattr(BicycleNetworkSource, attr_name)
                    result = delete_filtered_file(name)
                    if not result:
                        messages.error(request, "File not found.")
                    BicycleNetwork.objects.filter(name=name).delete() 
       
            delete_uploaded_files()
            if not success:
                messages.error(request, "Invalid Input GEOJSON.")

        return super().response_change(request, obj)


admin.site.register(BicycleNetworkSource, BicycleNetworkSourceAdmin)
