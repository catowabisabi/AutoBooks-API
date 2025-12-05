from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, TaskBoardViewSet, TaskViewSet, TaskCommentViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='projects')
router.register(r'boards', TaskBoardViewSet, basename='taskboards')
router.register(r'tasks', TaskViewSet, basename='tasks')
router.register(r'comments', TaskCommentViewSet, basename='comments')

urlpatterns = router.urls
