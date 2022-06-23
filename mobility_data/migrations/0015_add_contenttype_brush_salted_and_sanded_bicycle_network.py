# Generated by Django 4.0.4 on 2022-06-14 08:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mobility_data", "0014_add_contenttype_share_car_parking_place"),
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
                    ("SCP", "ShareCarParkingPlace"),
                    ("BLB", "BrushSaltedBicycleNetwork"),
                    ("BND", "BrushSandedBicycleNetwork"),
                ],
                max_length=3,
                null=True,
            ),
        ),
    ]