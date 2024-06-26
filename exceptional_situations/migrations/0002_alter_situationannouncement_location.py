# Generated by Django 4.1.13 on 2024-06-20 07:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("exceptional_situations", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="situationannouncement",
            name="location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="announcements",
                to="exceptional_situations.situationlocation",
            ),
        ),
    ]
