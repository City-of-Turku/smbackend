# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-01-09 09:49
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0039_increase_phone_field_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnitOntologyWordDetails",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("period_begin_year", models.PositiveSmallIntegerField(null=True)),
                ("period_end_year", models.PositiveSmallIntegerField(null=True)),
                ("clarification", models.CharField(blank=True, max_length=200)),
                (
                    "ontologyword",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="unit_details",
                        to="services.OntologyWord",
                    ),
                ),
            ],
        ),
        migrations.RemoveField(model_name="unit", name="services",),
        migrations.AlterField(
            model_name="unitconnection",
            name="section_type",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "PHONE_OR_EMAIL"),
                    (2, "LINK"),
                    (3, "TOPICAL"),
                    (4, "OTHER_INFO"),
                    (5, "OPENING_HOURS"),
                    (6, "SOCIAL_MEDIA_LINK"),
                    (7, "OTHER_ADDRESS"),
                    (8, "HIGHLIGHT"),
                ],
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="unitontologyworddetails",
            name="unit",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ontologyword_details",
                to="services.Unit",
            ),
        ),
        migrations.AddField(
            model_name="unit",
            name="ontologywords",
            field=models.ManyToManyField(
                related_name="units",
                through="services.UnitOntologyWordDetails",
                to="services.OntologyWord",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="unitontologyworddetails",
            unique_together=set([("period_begin_year", "unit", "ontologyword")]),
        ),
    ]
