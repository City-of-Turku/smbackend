# Generated by Django 4.0.7 on 2022-08-25 08:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("eco_counter", "0005_add_csv_data_source_to_importstate_and_station"),
    ]

    operations = [
        migrations.AlterField(
            model_name="importstate",
            name="csv_data_source",
            field=models.CharField(
                choices=[("TC", "TrafficCounter"), ("EC", "EcoCounter")],
                default="EC",
                max_length=2,
            ),
        ),
        migrations.AlterField(
            model_name="importstate",
            name="current_year_number",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (2015, 2015),
                    (2016, 2016),
                    (2017, 2017),
                    (2018, 2018),
                    (2019, 2019),
                    (2020, 2020),
                    (2021, 2021),
                    (2022, 2022),
                ],
                default=2015,
            ),
        ),
        migrations.AlterField(
            model_name="station",
            name="csv_data_source",
            field=models.CharField(
                choices=[("TC", "TrafficCounter"), ("EC", "EcoCounter")],
                default="EC",
                max_length=2,
            ),
        ),
        migrations.AlterField(
            model_name="year",
            name="year_number",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (2015, 2015),
                    (2016, 2016),
                    (2017, 2017),
                    (2018, 2018),
                    (2019, 2019),
                    (2020, 2020),
                    (2021, 2021),
                    (2022, 2022),
                ],
                default=2022,
            ),
        ),
    ]
