# Generated by Django 3.2.7 on 2021-12-16 11:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0087_auto_20211216_1357'),
    ]

    operations = [
        migrations.RunSQL(
            sql='''
              CREATE TRIGGER vector_column_trigger
              BEFORE INSERT OR UPDATE OF name, description, vector_column
              ON services_unit
              FOR EACH ROW EXECUTE PROCEDURE
              tsvector_update_trigger(
                vector_column, 'pg_catalog.finnish', name, description
              );

              UPDATE services_unit SET vector_column = NULL;
            ''',

            reverse_sql = '''
              DROP TRIGGER IF EXISTS vector_column_trigger
              ON services_unit;
            '''
        ),
    ]