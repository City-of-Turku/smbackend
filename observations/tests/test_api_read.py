import pytest
from rest_framework.reverse import reverse
from utils import match_observable_property_object_to_dict


@pytest.mark.django_db
def test__get_observable_properties_for_unit(api_client, observable_property):
    services = observable_property.services.all()
    assert len(services) > 0
    units = set((unit for service in services for unit in service.units.all()))
    assert len(units) > 0
    for unit in units:
        url = (
            reverse("unit-detail", kwargs={"pk": unit.pk})
            + "?include=observable_properties"
        )
        response = api_client.get(url)
        assert "observable_properties" in response.data
        observable_properties = response.data["observable_properties"]
        matching_properties = [
            p for p in observable_properties if p["id"] == observable_property.id
        ]

        assert len(matching_properties) == 1
        prop = matching_properties[0]
        match_observable_property_object_to_dict(observable_property, prop)
        if prop["observation_type"] == "categorical":
            assert "allowed_values" in prop
            assert len(prop["allowed_values"]) > 0
            for v in prop["allowed_values"]:
                assert "identifier" in v
                assert "name" in v
                assert "description" in v


@pytest.mark.django_db
def test__get_observable_properties_for_service(api_client, observable_property):
    services = observable_property.services.all()
    assert len(services) > 0

    for service in services:
        url = (
            reverse("service-detail", kwargs={"pk": service.pk})
            + "?include=observable_properties"
        )
        response = api_client.get(url)
        assert "observable_properties" in response.data

        observable_properties = response.data["observable_properties"]

        assert isinstance(observable_properties, list)
        matching_properties = [
            p for p in observable_properties if p["id"] == observable_property.id
        ]

        assert len(matching_properties) == 1
        returned_property = matching_properties[0]
        assert "name" in returned_property
        assert "measurement_unit" in returned_property
        assert "observation_type" in returned_property
        match_observable_property_object_to_dict(observable_property, returned_property)


@pytest.mark.django_db
def test__observable_not_expired(
    api_client, service, observable_property, unit_latest_observation
):
    url = reverse("unit-list") + "?service={}&include=observations".format(service.pk)
    response = api_client.get(url)
    assert len(response.data.get("results")[0].get("observations")) == 1


@pytest.mark.django_db
def test__observable_expired(
    api_client, service, observable_property, unit_latest_observation_expired
):
    url = reverse("unit-list") + "?service={}&include=observations".format(service.pk)
    response = api_client.get(url)
    assert len(response.data.get("results")[0].get("observations")) == 0


@pytest.mark.django_db
def test__observable_expired_and_not_expired(
    api_client,
    service,
    observable_property,
    unit_latest_observation_both_expired_and_not_expirable,
):
    url = reverse("unit-list") + "?service={}&include=observations".format(service.pk)
    response = api_client.get(url)
    unit_data = response.data.get("results")[0]
    observations = unit_data.get("observations")
    assert len(observations) == 1
    observation = observations[0]
    assert observation["property"] == "notice"
    assert observation["value"]["fi"] == "Description"
    assert (
        observation["id"]
        == unit_latest_observation_both_expired_and_not_expirable[
            "not_expirable"
        ].observation.id
    )


# @pytest.mark.django_db
# def test__get_units_with_observations_sorted_by_latest_first(
#    api_client, categorical_observations):
#     response = api_client.get(
#         reverse('unit-list') + '?include=observations&observation_count=5')
