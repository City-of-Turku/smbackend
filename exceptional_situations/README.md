# Exceptional Situations APP
APP for importing, storing and serving exceptional situations

## Importing data
### Traffic Announcements
Imports road works and traffic announcements in Southwest Finland from digitraffic.fi.
To import type:
`./manage.py import_traffic_situations`

### Excavation permits
Imports excavation permits in the Turku area. 
To import type:
`./manage.py import_excavation_permits`

### Delete inactive situations
`./manage.py delete_inactive_situations`
Deletes also the related announcements and locations.

## API Documentation
See online swagger documentation. 
