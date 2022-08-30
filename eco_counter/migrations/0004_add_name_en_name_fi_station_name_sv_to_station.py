# Generated by Django 4.0.7 on 2022-08-24 05:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("eco_counter", "0003_alter_importstate_current_year_number_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="station",
            name="name_en",
            field=models.CharField(max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="station",
            name="name_fi",
            field=models.CharField(max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="station",
            name="name_sv",
            field=models.CharField(max_length=30, null=True),
        ),
    ]