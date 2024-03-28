# Generated by Django 4.1.13 on 2024-03-13 08:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("iot", "0003_iotdatasource_headers"),
    ]

    operations = [
        migrations.AddField(
            model_name="iotdatasource",
            name="is_xml",
            field=models.BooleanField(
                default=False,
                verbose_name="If True, XML data will be converted to JSON.",
            ),
        ),
        migrations.AlterField(
            model_name="iotdatasource",
            name="headers",
            field=models.JSONField(
                blank=True,
                null=True,
                verbose_name='request headers in JSON format, e.g., {"key1": "value1", "key2": "value2"}',
            ),
        ),
        migrations.AlterField(
            model_name="iotdatasource",
            name="source_name",
            field=models.CharField(
                max_length=3,
                unique=True,
                verbose_name="Three letter long identifier for the source. Set the identifier as an argument to the Celery task that fetches the data.",
            ),
        ),
    ]