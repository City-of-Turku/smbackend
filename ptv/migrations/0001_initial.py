# Generated by Django 2.2.13 on 2020-08-26 10:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("services", "0077_unit_soft_delete"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnitPTVIdentifier",
            fields=[
                ("id", models.UUIDField(primary_key=True, serialize=False)),
                (
                    "unit",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ptv_id",
                        to="services.Unit",
                    ),
                ),
            ],
        ),
    ]
