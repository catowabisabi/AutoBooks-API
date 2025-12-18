from django.urls import path
from rest_framework.routers import DefaultRouter
from documents.views.document_viewset import DocumentViewSet
from documents.views.pdf_processing_views import (
    GenerateInvoicePdfView,
    AddStampToPdfView,
    AddSignatureToPdfView
)

router = DefaultRouter()
router.include_root_view = False  # Disable API root view to avoid "api" tag
router.register(r'documents', DocumentViewSet, basename='documents')

urlpatterns = [
    # PDF Processing endpoints
    path('invoices/generate-pdf/', GenerateInvoicePdfView.as_view(), name='generate-invoice-pdf'),
    path('documents/add-stamp/', AddStampToPdfView.as_view(), name='add-stamp-to-pdf'),
    path('documents/add-signature/', AddSignatureToPdfView.as_view(), name='add-signature-to-pdf'),
] + router.urls
