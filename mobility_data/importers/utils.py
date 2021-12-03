import requests
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from munigeo.models import (
    Address,
    Street,
    AdministrativeDivisionGeometry, 
    AdministrativeDivision,
)
from mobility_data.models import ContentType

GEOMETRY_ID = 11 #  11 Varsinaissuomi 
GEOMETRY_URL = "https://tie.digitraffic.fi/api/v3/data/traffic-messages/area-geometries?id={id}&lastUpdated=false".format(id=GEOMETRY_ID)
LANGUAGES = ["fi", "sv", "en"]

def fetch_json(url):
    response = requests.get(url)
    assert response.status_code == 200, "Fetching {} status code: {}".\
            format(url, response.status_code)
    return response.json()

def delete_mobile_units(type_name):
    ContentType.objects.filter(type_name=type_name).delete()

def get_or_create_content_type(type_name, name, description):
    content_type, created = ContentType.objects.get_or_create(
        type_name=type_name,
        name=name,
        description=description
    )
    return content_type, created

def get_closest_street_name(point):
    """
    Returns the name of the street that is closest to point.
    """
    address = Address.objects.annotate(distance=Distance("location", point)).order_by("distance").first()
    try:
        street = Street.objects.get(id=address.street_id)
        return street.name
    except Street.DoesNotExist:
        return None

def get_street_name_translations(name):
    """
    Return a dict with street names of all given languages.
    Note, there are no english names for streets and if translation
    does not exist return "fi" as default name. If street is not found
    return the name of the street for all languages.
    """
    names = {}
    default_attr_name = "name_fi"
    try:
        street = Street.objects.get(name=name)
        for lang in LANGUAGES:
            attr_name = "name_"+lang
            name = getattr(street, attr_name)
            if name != None:
                names[lang] = name
            else:
                names[lang] = getattr(street, default_attr_name)
        return names
    except Street.DoesNotExist:
        for lang in LANGUAGES:
            names[lang] = name
        return names   

def get_municipality_name(point):
    """
    Returns the string name of the municipality in which the point
    is located.
    """
    try:
        # resolve in which division to point is.
        division = AdministrativeDivisionGeometry.objects.get(boundary__contains=point)
    except AdministrativeDivisionGeometry.DoesNotExist:
        return None
    # Get the division and return its name.
    return AdministrativeDivision.objects.get(id=division.division_id).name

def set_translated_field(obj, field_name, data):
    """
    Sets the value of all languages for given field_name.   
    :param obj: the object to which the fields will be set
    :param field_name:  name of the field to be set.
    :param data: dictionary where the key is the language and the value is the value 
    to be set for the field with the given langauge. 
    """
    for lang in LANGUAGES:
        if lang in data:
            obj_key = "{}_{}".format(field_name, lang)
            setattr(obj, obj_key, data[lang])
