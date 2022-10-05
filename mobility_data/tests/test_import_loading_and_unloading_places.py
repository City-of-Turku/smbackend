import pytest
from munigeo.models import Municipality

from mobility_data.models import ContentType, MobileUnit

from .utils import import_command


@pytest.mark.django_db
@pytest.mark.django_db
def test_import(municipality):
    import_command(
        "import_loading_and_unloading_places",
        test_mode="loading_and_unloading_places.geojson",
    )
    assert ContentType.objects.all().count() == 1
    assert MobileUnit.objects.all().count() == 3
    try:
        turku_muni = Municipality.objects.get(name="Turku")
    except Municipality.DoesNotExist:
        assert turku_muni
    niuskalankatu = MobileUnit.objects.get(name="Mäntykoti Räntämäki")
    assert niuskalankatu.name_sv == "Räntämäki äldreboende"
    assert niuskalankatu.name_en == "Räntämäki nursing home"
    assert niuskalankatu.address_fi == "Niuskalankatu 7"
    assert niuskalankatu.address_sv == "Niuskalagatan 7"
    assert niuskalankatu.address_en == "Niuskalankatu 7"
    assert niuskalankatu.address_zip == "20380"
    assert niuskalankatu.municipality == turku_muni
