# Generated by Django 4.2 on 2023-05-15 12:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("eco_counter", "0013_alter_importstate_current_month_and_year_to_nullables"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="station",
            name="lam_id",
        ),
        migrations.AddField(
            model_name="station",
            name="station_id",
            field=models.CharField(max_length=16, null=True),
        ),
    ]
