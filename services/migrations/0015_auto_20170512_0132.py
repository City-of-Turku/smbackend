# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-05-11 22:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0014_servicemapping"),
    ]

    operations = [
        migrations.AlterField(
            model_name="servicemapping",
            name="service_id",
            field=models.IntegerField(unique=True),
        ),
    ]
