from django.contrib import admin

from maintenance.models import (
    MaintenanceUnit,
    MaintenanceWork,
    UnitMaintenance,
    UnitMaintenanceGeometry,
)

admin.site.register(MaintenanceWork)
admin.site.register(MaintenanceUnit)
admin.site.register(UnitMaintenance)
admin.site.register(UnitMaintenanceGeometry)
