# Generated by Django 3.2.7 on 2021-11-02 14:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mobility_data', '0004_auto_20211102_0806'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mobileunit',
            name='unit_id',
            field=models.IntegerField(null=True, verbose_name='optonal id to a unit in the servicemap'),
        ),
    ]
