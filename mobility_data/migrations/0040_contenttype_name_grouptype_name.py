# Generated by Django 4.1.2 on 2023-03-07 09:37

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mobility_data", "0039_contentype_and_grouptype_rename_name_to_type_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="contenttype",
            name="name",
            field=models.CharField(max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="grouptype",
            name="name",
            field=models.CharField(max_length=128, null=True),
        ),
    ]
