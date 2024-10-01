from django.contrib import admin

from maintenance.models import MaintenanceUnit, MaintenanceWork

admin.site.register(MaintenanceWork)
admin.site.register(MaintenanceUnit)
