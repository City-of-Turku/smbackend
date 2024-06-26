# Generated by Django 3.2.6 on 2021-12-01 06:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0085_unit_extra"),
    ]

    operations = [
        migrations.AddField(
            model_name="unit",
            name="related_units",
            field=models.ManyToManyField(
                blank=True,
                related_name="_services_unit_related_units_+",
                to="services.Unit",
            ),
        ),
    ]
