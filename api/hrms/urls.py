from rest_framework.routers import DefaultRouter
from .views import (
    DepartmentViewset,
    DesignationViewset,
    LeaveApplicationViewset,
    ProjectViewset,
    TaskViewset,
)

router = DefaultRouter()
router.register(r'departments', DepartmentViewset, basename='departments')
router.register(r'designations', DesignationViewset, basename='designations')
router.register(r'projects', ProjectViewset, basename='projects')
router.register(r'tasks', TaskViewset, basename='tasks')
router.register(r'leave_applications', LeaveApplicationViewset, basename='leave_applications')

urlpatterns = router.urls
