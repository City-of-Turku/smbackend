# Generated by Django 4.0.7 on 2022-11-15 11:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mobility_data", "0029_add_content_type_paddling_trail"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contenttype",
            name="name",
            field=models.CharField(max_length=64, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="grouptype",
            name="name",
            field=models.CharField(max_length=64, null=True, unique=True),
        ),
    ]
