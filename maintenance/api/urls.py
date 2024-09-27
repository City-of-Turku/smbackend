from django.urls import include, path
from rest_framework import routers

from . import views

app_name = "maintenance"

router = routers.DefaultRouter()
router.register("active_events", views.ActiveEventsViewSet, basename="active_events")

router.register(
    "maintenance_works", views.MaintenanceWorkViewSet, basename="maintenance_works"
)
router.register(
    "maintenance_units", views.MaintenanceUnitViewSet, basename="maintenance_units"
)
router.register(
    "geometry_history", views.GeometryHitoryViewSet, basename="geometry_history"
)
router.register(
    "unit_maintenance", views.UnitMaintenanceViewSet, basename="unit_maintenance"
)
router.register(
    "unit_maintenance_geometry",
    views.UnitMaintenanceGeometryViewSet,
    basename="unit_maintenance_geometry",
)
urlpatterns = [
    path("", include(router.urls), name="maintenance"),
]
