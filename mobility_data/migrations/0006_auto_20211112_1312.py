# Generated by Django 3.2.7 on 2021-11-12 11:12

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mobility_data", "0005_alter_mobileunit_unit_id"),
    ]

    operations = [
        migrations.RenameField(
            model_name="mobileunit",
            old_name="unit_group",
            new_name="mobile_unit_group",
        ),
        migrations.AlterField(
            model_name="grouptype",
            name="type_name",
            field=models.CharField(
                choices=[("CRE", "CULTURE_ROUTE")], max_length=3, null=True
            ),
        ),
    ]
