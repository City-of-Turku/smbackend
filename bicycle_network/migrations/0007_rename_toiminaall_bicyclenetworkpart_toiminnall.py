# Generated by Django 3.2.7 on 2021-11-23 09:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bicycle_network", "0006_auto_20211123_1101"),
    ]

    operations = [
        migrations.RenameField(
            model_name="bicyclenetworkpart",
            old_name="toiminaall",
            new_name="toiminnall",
        ),
    ]
