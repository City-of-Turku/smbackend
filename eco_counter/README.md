# Eco-counter Turku Importer

Imports and processes counter data for the Turku region:
- Eco Counter (EC) via Eco-Visio API v2
- Traffic Counter (TC) CSV (15 min intervals)
- LAM Counter (LC) from Digitraffic
- Telraam (TR) from Telraam API

## Environment
Add the following to `.env` (update URLs if the data sources change):
- `ECO_VISIO_API_KEY=` **(required)** API key for Eco-Visio
- `ECO_VISIO_API_URL=https://api.eco-counter.com/api/v2` (override if needed)
- `ECO_COUNTER_OBSERVATIONS_URL=https://data.turku.fi/cjtv3brqr7gectdv7rfttc/counters-15min.csv` (kept for backward compatibility, still required by the importer)
- `TRAFFIC_COUNTER_OBSERVATIONS_BASE_URL=https://data.turku.fi/2yxpk2imqi2mzxpa6e6knq/`
- `LAM_COUNTER_STATIONS_URL=https://tie.digitraffic.fi/api/v3/metadata/tms-stations`
- `LAM_COUNTER_API_BASE_URL=https://tie-lam-test.digitraffic.fi`
- `TELRAAM_TOKEN=` Telraam API token (used for Telraam data and `import_telraam_to_csv.py`)

Up-to-date open data URLs can be found at https://www.avoindata.fi/data/fi/dataset/turun-seudun-liikennemaaria and https://www.digitraffic.fi/tieliikenne/lam/.

## Eco-Visio (Eco Counter)
- EC stations and observations are fetched directly from Eco-Visio API v2 using `ECO_VISIO_API_KEY`.
- Stations are pulled with segment geometry, filtered to the Southwestern Finland polygon, and stored with transformed geometry.
- Raw traffic is retrieved per station in ≤31-day chunks with rate-limit-aware retries; native granularity (15 min / 1 h) is preserved, and existing aggregation logic handles rollups.
- Travel modes map to existing columns (bike→P, pedestrian→J, car/motorized→A, bus→B; undefined directions are split evenly between K/P).
- Legacy EC endpoints/models remain unchanged; only the data source is now the Eco-Visio API.
- Initial imports for Eco-Visio data start from 2025-01-01 (earlier dates are not fetched).

## Importing

### Initial import
Run before continuous imports:
```
./manage.py import_counter_data --init COUNTERS
```
Example: `./manage.py import_counter_data --init EC TC`

### Continuous import
Hourly imports:
```
./manage.py import_counter_data --counters COUNTERS
```
Example: `./manage.py import_counter_data --counters EC TC`

Counter names: EC (Eco Counter), TC (Traffic Counter), LC (Lam Counter), TR (Telraam Counter). Traffic Counter data updates weekly; Lam Counter daily.

## Deleting data
Use the `delete_counter_data` management command.
Example (delete all Lam Counter data):
```
./manage.py delete_counter_data --counters LC
```

## Importing Telraam raw data
To load Telraam data into the database, import the raw data first with the `import_telraam_to_csv` management command. Schedule it hourly (see: https://github.com/City-of-Turku/smbackend/wiki/Celery-Tasks#telraam-to-csv-eco_countertasksimport_telraam_to_csv). Telraam raw data is stored in `PROJECT_ROOT/media/telraam_data/`.

## Troubleshooting
- EC 401/403 responses: check `ECO_VISIO_API_KEY`/`ECO_VISIO_API_URL` and key permissions.
- EC 429 or rate-limit warnings: the client retries using API headers; rerun after the cooldown if imports still fail.
- "No Eco-Visio data..." warnings: verify the station exists within Southwestern Finland, has a valid `station_id`, and the requested time range contains data.
- "Start time ... not found" during imports: data may start later than expected; rerun with `--init` to reset state if needed.
- CSV-based counters (TC/LC) can change column layouts; rerun `./manage.py import_counter_data --init` before resuming continuous imports.

## Testing
If changes are made to the importer, run:
```
pytest -m test_import_counter_data
```
