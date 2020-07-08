# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-02-14 10:06
from __future__ import unicode_literals

from django.db import migrations
from uuid import UUID

UNITS_TO_REDIRECT = [6215, 5846, 6225]  # Kallio  # Vallila  # Herttoniemi


def add_health_station_redirects(apps, schema_editor):
    UnitAlias = apps.get_model("services", "UnitAlias")
    Unit = apps.get_model("services", "Unit")
    target = None
    try:
        target = Unit.objects.get(pk=56241)  # Kalasataman terveysasema
        if target.organization.uuid != UUID("83e74666-0836-4c1d-948a-4b34a8b90301"):
            return
    except Unit.DoesNotExist:
        return
    for unit_id in UNITS_TO_REDIRECT:
        UnitAlias.objects.get_or_create(second=unit_id, first=target)


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0037_add_ordering_to_ontologymodels"),
    ]

    operations = [
        migrations.RunPython(add_health_station_redirects, migrations.RunPython.noop)
    ]
