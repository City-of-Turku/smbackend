# Generated by Django 4.0 on 2022-02-08 09:42

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0086_unit_related_units"),
    ]

    operations = [
        migrations.AddField(
            model_name="unit",
            name="service_names_en",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=200), default=list, size=None
            ),
        ),
        migrations.AddField(
            model_name="unit",
            name="service_names_fi",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=200), default=list, size=None
            ),
        ),
        migrations.AddField(
            model_name="unit",
            name="service_names_sv",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=200), default=list, size=None
            ),
        ),
    ]
