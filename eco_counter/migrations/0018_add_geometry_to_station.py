# Generated by Django 4.2 on 2023-05-24 06:55

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("eco_counter", "0017_rename_geom_station_location"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="geometry",
            field=django.contrib.gis.db.models.fields.GeometryField(
                null=True, srid=3067
            ),
        ),
    ]
