# Generated by Django 4.0.7 on 2022-08-31 08:58

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("eco_counter", "0007_add_fields_for_bus_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="importstate",
            name="rows_imported",
        ),
    ]
