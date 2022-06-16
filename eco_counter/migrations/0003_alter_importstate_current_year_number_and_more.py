# Generated by Django 4.0 on 2022-01-24 08:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("eco_counter", "0002_auto_20211013_1018"),
    ]

    operations = [
        migrations.AlterField(
            model_name="importstate",
            name="current_year_number",
            field=models.PositiveSmallIntegerField(
                choices=[(2020, 2020), (2021, 2021), (2022, 2022)], default=2020
            ),
        ),
        migrations.AlterField(
            model_name="year",
            name="year_number",
            field=models.PositiveSmallIntegerField(
                choices=[(2020, 2020), (2021, 2021), (2022, 2022)], default=2022
            ),
        ),
    ]
