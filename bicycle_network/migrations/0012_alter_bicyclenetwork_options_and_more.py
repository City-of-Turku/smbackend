# Generated by Django 4.0 on 2022-02-01 06:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bicycle_network", "0011_delete_bicyclenetworksource_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="bicyclenetwork",
            options={"ordering": ["-id"]},
        ),
        migrations.AlterField(
            model_name="bicyclenetwork",
            name="length",
            field=models.FloatField(
                blank=True, null=True, verbose_name="Length in meters."
            ),
        ),
        migrations.AlterField(
            model_name="bicyclenetwork",
            name="name",
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name="bicyclenetwork",
            name="name_en",
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name="bicyclenetwork",
            name="name_fi",
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name="bicyclenetwork",
            name="name_sv",
            field=models.CharField(max_length=64, null=True),
        ),
    ]
