# Generated by Django 4.0.7 on 2022-09-08 10:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("eco_counter", "0010_alter_max_length_of_station_name_to_64"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="lam_id",
            field=models.PositiveSmallIntegerField(null=True),
        ),
    ]
