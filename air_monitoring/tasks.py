from django.core import management

from smbackend.utils import shared_task_email


@shared_task_email
def initial_import_data(name="initial_import_data"):
    management.call_command("import_air_monitoring_data", "--initial-import")


@shared_task_email
def initial_import_data_with_stations(name="initial_import_data_with_stations"):
    management.call_command(
        "import_air_monitoring_data", "--initial-import-with-stations"
    )


@shared_task_email
def incremental_import_data(
    name="incremental_import_data",
):
    management.call_command("import_air_monitoring_data")


@shared_task_email
def delete_all_data(name="delete_all_data"):
    management.call_command("delete_all_data")
