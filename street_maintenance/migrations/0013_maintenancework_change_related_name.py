# Generated by Django 4.1.2 on 2023-03-10 07:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("street_maintenance", "0012_maintenancework_add_field_original_event_names"),
    ]

    operations = [
        migrations.AlterField(
            model_name="maintenancework",
            name="maintenance_unit",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="maintenance_work",
                to="street_maintenance.maintenanceunit",
            ),
        ),
    ]
