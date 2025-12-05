# from rest_framework.routers import DefaultRouter
# from .views import DashboardViewSet, ChartViewSet
#
# router = DefaultRouter()
# router.register(r'dashboards', DashboardViewSet, basename='dashboard')
# router.register(r'charts', ChartViewSet, basename='chart')
#
# urlpatterns = router.urls


from rest_framework.routers import DefaultRouter
from .views import DashboardViewSet, ChartViewSet

router = DefaultRouter()
router.register(r'dashboards', DashboardViewSet)
router.register(r'charts', ChartViewSet)

urlpatterns = router.urls
