# Generated by Django 3.2.7 on 2021-11-23 09:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bicycle_network', '0007_rename_toiminaall_bicyclenetworkpart_toiminnall'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bicyclenetworkpart',
            old_name='tienimi2',
            new_name='tienim2',
        ),
    ]