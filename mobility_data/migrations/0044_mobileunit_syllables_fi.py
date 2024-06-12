# Generated by Django 4.1.13 on 2024-06-12 06:08

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mobility_data", "0043_mobileunit_add_multilingaul_content_type_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="mobileunit",
            name="syllables_fi",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=16), default=list, size=None
            ),
        ),
    ]