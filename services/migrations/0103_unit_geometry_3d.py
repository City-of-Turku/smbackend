# Generated by Django 4.1.13 on 2024-07-04 06:06

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0102_unit_new_contract_type_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="unit",
            name="geometry_3d",
            field=django.contrib.gis.db.models.fields.GeometryField(
                dim=3, null=True, srid=3067
            ),
        ),
    ]
