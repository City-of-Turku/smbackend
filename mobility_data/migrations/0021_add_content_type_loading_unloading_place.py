# Generated by Django 4.0.7 on 2022-10-04 10:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mobility_data", "0020_add_content_type_disabled_parking"),
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
                    ("GMA", "GuestMarina"),
                    ("BOK", "BoatParking"),
                    ("MAR", "Marina"),
                    ("NSP", "NoStaffParking"),
                    ("DSP", "DisabledParking"),
                    ("BER", "Berth"),
                    ("LUP", "LoadingUnloadingPlace"),
                ],
                max_length=3,
                null=True,
            ),
        ),
    ]