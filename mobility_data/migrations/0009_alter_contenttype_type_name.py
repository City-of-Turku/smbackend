# Generated by Django 3.2.7 on 2021-12-16 06:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mobility_data", "0008_auto_20211118_1256"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contenttype",
            name="type_name",
            field=models.CharField(
                choices=[
                    ("CGS", "ChargingStation"),
                    ("GFS", "GasFillingStation"),
                    ("CRU", "CultureRouteUnit"),
                    ("CRG", "CultureRouteGeometry"),
                    ("BIS", "BicycleStand"),
                ],
                max_length=3,
                null=True,
            ),
        ),
    ]
