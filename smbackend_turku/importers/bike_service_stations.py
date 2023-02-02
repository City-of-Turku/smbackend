from mobility_data.importers.bike_service_stations import (
    create_bike_service_station_content_type,
    get_bike_service_station_objects,
)
from smbackend_turku.importers.utils import BaseExternalSource


class BikeServiceStationImporter(BaseExternalSource):
    def __init__(self, config=None, logger=None, test_data=None):
        super().__init__(config)
        self.logger = logger
        self.test_data = test_data

    def import_bike_service_stations(self):
        self.logger.info("Importing Bike service stations...")
        content_type = create_bike_service_station_content_type()
        filtered_objects = get_bike_service_station_objects(geojson_file=self.test_data)
        super().save_objects_as_units(filtered_objects, content_type)


def delete_bike_service_stations(**kwargs):
    importer = BikeServiceStationImporter(**kwargs)
    importer.delete_external_source()


def import_bike_service_stations(**kwargs):
    importer = BikeServiceStationImporter(**kwargs)
    importer.import_bike_service_stations()
