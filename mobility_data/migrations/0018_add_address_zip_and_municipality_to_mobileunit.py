# Generated by Django 4.0.6 on 2022-08-15 11:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("munigeo", "0013_add_naturalsort_function"),
        ("mobility_data", "0017_add_content_type_no_staff_parking"),
    ]

    operations = [
        migrations.AddField(
            model_name="mobileunit",
            name="address_zip",
            field=models.CharField(max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="mobileunit",
            name="municipality",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="munigeo.municipality",
            ),
        ),
    ]
