from rest_framework.routers import DefaultRouter
from documents.views.document_viewset import DocumentViewSet

router = DefaultRouter()
router.include_root_view = False  # Disable API root view to avoid "api" tag
router.register(r'documents', DocumentViewSet, basename='documents')

urlpatterns = router.urls
