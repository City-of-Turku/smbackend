# Generated by Django 3.2.7 on 2021-11-01 12:40

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mobility_data", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="mobileunit",
            name="extra",
            field=models.JSONField(null=True),
        ),
    ]
