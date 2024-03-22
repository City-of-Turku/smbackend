# Generated by Django 4.1.10 on 2024-01-25 11:58

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("eco_counter", "0019_station_data_from_date_station_data_until_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="sensor_types",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=2), default=list, size=None
            ),
        ),
    ]