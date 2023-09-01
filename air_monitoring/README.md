# Air monitoring APP
Imports, processes and servers air monitoring data.
The imported parameters are:
* AQINDEX_PT1H_avg (Ilmanlaatuindeksi)
* PM10_PT1H_avg (Hengitettävät hiukkaset)
* SO2_PT1H_avg (rikkidioksiidi)
* O3_PT1H_avg (otsooni)
* PM25_PT1H_avg (pienhiukkaset)
* NO2_PT1H_avg (typpidioksiidi)

# Importing
## Initial import
To import initial data and stations:
```
./manage.py import_air_monitoring_data --inital-import-with-stations
```
Initial importing without deleting stations:
```
./manage.py import_air_monitoring_data --inital-import
```
Note, inital import deletes all previously imported data.

## Incremental import
```
./manage.py import_air_monitoring_data
```

## To delete all data
```
./manage.py delete_all_air_monitoring_data
```


