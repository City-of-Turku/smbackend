# Generated by Django 4.0.7 on 2022-12-08 07:51

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("mobility_data", "0033_remove_contenttype_type_name"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="grouptype",
            name="type_name",
        ),
    ]
