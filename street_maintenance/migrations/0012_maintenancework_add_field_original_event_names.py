# Generated by Django 4.1.2 on 2023-02-16 11:35

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("street_maintenance", "0011_rename_provider_autori_to_yit"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenancework",
            name="original_event_names",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=64), default=list, size=None
            ),
        ),
    ]
