from django.urls import path
from .views import health_check, detailed_health_check

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("health/detailed/", detailed_health_check, name="health-check-detailed"),
]
