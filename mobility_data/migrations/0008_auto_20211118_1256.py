# Generated by Django 3.2.7 on 2021-11-18 10:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mobility_data", "0007_auto_20211112_1320"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="contenttype",
            options={"ordering": ["id"]},
        ),
        migrations.AlterModelOptions(
            name="grouptype",
            options={"ordering": ["id"]},
        ),
        migrations.AlterModelOptions(
            name="mobileunit",
            options={"ordering": ["-created_time"]},
        ),
        migrations.AlterModelOptions(
            name="mobileunitgroup",
            options={"ordering": ["-created_time"]},
        ),
        migrations.AlterField(
            model_name="contenttype",
            name="type_name",
            field=models.CharField(
                choices=[
                    ("CGS", "ChargingStation"),
                    ("GFS", "GasFillingStation"),
                    ("CRU", "CultureRouteUnit"),
                    ("CRG", "CultureRouteGeometry"),
                ],
                max_length=3,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="mobileunit",
            name="mobile_unit_group",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="mobile_units",
                to="mobility_data.mobileunitgroup",
            ),
        ),
    ]
