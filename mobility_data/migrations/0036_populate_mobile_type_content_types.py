# Generated by Django 4.1.2 on 2023-02-08 07:12

from django.db import migrations


def make_many_to_many_content_types(apps, schema_editor):
    MobileUnit = apps.get_model("mobility_data", "MobileUnit")

    for mobile_unit in MobileUnit.objects.all():
        mobile_unit.content_types.add(mobile_unit.content_type)


class Migration(migrations.Migration):

    dependencies = [
        ("mobility_data", "0035_add_many_to_many_field_content_types_to_mobile_unit"),
    ]

    operations = [
        migrations.RunPython(make_many_to_many_content_types),
    ]
