# Generated by Django 4.0.4 on 2022-05-23 08:44

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mobility_data", "0012_add_table_datasource"),
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
                    ("PAZ", "PaymentZone"),
                    ("SLZ", "SpeedLimitZone"),
                    ("SPG", "ScooterParking"),
                    ("SSL", "ScooterSpeedLimit"),
                    ("SNP", "ScooterNoParking"),
                    ("APT", "AccessoryPublicToilet"),
                    ("ABH", "AccessoryBench"),
                    ("ATE", "AccessoryTable"),
                    ("AFG", "AccessoryFurnitureGroup"),
                    ("BSS", "BikeServiceStation"),
                ],
                max_length=3,
                null=True,
            ),
        ),
    ]
