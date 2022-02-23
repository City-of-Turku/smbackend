# Generated by Django 4.0 on 2022-02-17 11:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="IoTDataSource",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "source_name",
                    models.CharField(
                        max_length=3,
                        unique=True,
                        verbose_name="Three letter long name for the source",
                    ),
                ),
                ("source_full_name", models.CharField(max_length=64, null=True)),
                ("url", models.URLField()),
            ],
        ),
        migrations.CreateModel(
            name="IoTData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("data", models.JSONField(null=True)),
                (
                    "data_source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="iot.iotdatasource",
                    ),
                ),
            ],
        ),
    ]