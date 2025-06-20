# Generated by Django 4.1.13 on 2024-07-01 06:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0101_exclusionword"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="unit",
            name="contract_type",
        ),
        migrations.AddField(
            model_name="unit",
            name="displayed_service_owner",
            field=models.CharField(max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="unit",
            name="displayed_service_owner_en",
            field=models.CharField(max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="unit",
            name="displayed_service_owner_fi",
            field=models.CharField(max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="unit",
            name="displayed_service_owner_sv",
            field=models.CharField(max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="unit",
            name="displayed_service_owner_type",
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name="unit",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Poistettu-aikaleima"
            ),
        ),
        migrations.AlterField(
            model_name="unit",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Aktiivinen"),
        ),
    ]
