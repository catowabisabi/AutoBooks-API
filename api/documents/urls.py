from rest_framework.routers import DefaultRouter
from documents.views.document_viewset import DocumentViewSet

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='documents')

urlpatterns = router.urls
