# Generated by Django 3.2.7 on 2021-11-01 12:06

import uuid

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ContentType",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=64, null=True)),
                (
                    "class_name",
                    models.CharField(
                        max_length=64,
                        null=True,
                        verbose_name="Name of the content class",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        null=True,
                        verbose_name="Optional description of the content type.",
                    ),
                ),
                (
                    "type_name",
                    models.CharField(
                        choices=[
                            ("CGS", "ChargingStation"),
                            ("GFS", "GasFillingStation"),
                        ],
                        max_length=3,
                        null=True,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="GroupType",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=64, null=True)),
                (
                    "class_name",
                    models.CharField(
                        max_length=64,
                        null=True,
                        verbose_name="Name of the content class",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        null=True,
                        verbose_name="Optional description of the content type.",
                    ),
                ),
                (
                    "type_name",
                    models.CharField(
                        choices=[("EGP", "ExampleGroup")], max_length=3, null=True
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="MobileUnitGroup",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_time", models.DateTimeField(auto_now_add=True)),
                ("name", models.CharField(max_length=64, null=True)),
                ("description", models.TextField(null=True)),
                (
                    "group_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="unit_groups",
                        to="mobility_data.grouptype",
                    ),
                ),
            ],
            options={
                "ordering": ["created_time"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="MobileUnit",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_time", models.DateTimeField(auto_now_add=True)),
                ("name", models.CharField(max_length=64, null=True)),
                ("description", models.TextField(null=True)),
                (
                    "geometry",
                    django.contrib.gis.db.models.fields.GeometryField(
                        null=True, srid=3067
                    ),
                ),
                ("address", models.CharField(max_length=100, null=True)),
                ("unit_id", models.IntegerField(null=True)),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="units",
                        to="mobility_data.contenttype",
                    ),
                ),
                (
                    "unit_group",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="units",
                        to="mobility_data.mobileunitgroup",
                    ),
                ),
            ],
            options={
                "ordering": ["created_time"],
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="GasFillingStationContent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("lng_cng", models.CharField(max_length=8, null=True)),
                ("operator", models.CharField(max_length=32, null=True)),
                (
                    "mobile_unit",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gas_filling_station_content",
                        to="mobility_data.mobileunit",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ChargingStationContent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("url", models.URLField(null=True)),
                ("charger_type", models.CharField(max_length=32, null=True)),
                (
                    "mobile_unit",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="charging_station_content",
                        to="mobility_data.mobileunit",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
