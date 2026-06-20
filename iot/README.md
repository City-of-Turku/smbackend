## About
The purpose of the IoT app is to temporarily store data from various IoT data sources that do not support frequent data fetching.
Data is stored in JSON format using a JSONField and is served as JSON. The app uses caching to store all queries and serialized data. The cache is cleared for a source when:
* New data is imported
* A new data source is added
If the cache is empty when data is requested, it is populated automatically.

## Adding IoT Data Source via the Admin
To add a new IoT data source:
* Identifier: Provide a three-letter identifier. This is used:
    * For identifying the data source in the Celery task
    * When requesting data via the API
* Full Name: Enter the full name of the data source
* URL: Provide the URL that returns the data in JSON or XML format
*is_xml: Set this to True if the data is in XML format. The app will automatically convert the XML to JSON.
* Headers (optional): Add any headers needed for the data request

## Authentication with token
To use token-based authentication:
* Create an IoT-Data Token item
* Assign the token to the data source in the Token field
*In the Token Headers field of the data source, define how the token should be used in the request headers, e.g.:
```{ "Authorization": "Bearer <token>" }```
Note: <token> will be dynamically replaced with the actual token value.

## Setting Up Periodic Import with Celery
To periodically import data:
1. In the Admin, create a Periodic Task
2. Provide a descriptive name
3. Select the task: iot.tasks.import_iot_data (registered Celery task)
4. Choose the Interval Schedule
5. Set the Start DateTime
6. Add the data source identifier in the Positional Arguments, e.g.: ["R24"]
This will import the data source identified by R24.

## Manual import
To manually import data for a source, use either of the following methods:
`./manage.py import_iot_data identifier`
Or trigger the periodic task manually via the Admin interface.


## Retriving data
Refer to the OpenAPI/Swagger specification for the API: specification.swagger.yaml

