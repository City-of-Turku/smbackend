# Generated by Django 4.1.13 on 2024-06-17 06:19

import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("mobility_data", "0044_mobileunit_syllables_fi"),
    ]

    operations = [
        migrations.AddField(
            model_name="contenttype",
            name="search_column_en",
            field=django.contrib.postgres.search.SearchVectorField(null=True),
        ),
        migrations.AddField(
            model_name="contenttype",
            name="search_column_fi",
            field=django.contrib.postgres.search.SearchVectorField(null=True),
        ),
        migrations.AddField(
            model_name="contenttype",
            name="search_column_sv",
            field=django.contrib.postgres.search.SearchVectorField(null=True),
        ),
        migrations.AddIndex(
            model_name="contenttype",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["search_column_fi"], name="mobility_da_search__689c07_gin"
            ),
        ),
        migrations.AddIndex(
            model_name="contenttype",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["search_column_sv"], name="mobility_da_search__d7d981_gin"
            ),
        ),
        migrations.AddIndex(
            model_name="contenttype",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["search_column_en"], name="mobility_da_search__f12e27_gin"
            ),
        ),
    ]