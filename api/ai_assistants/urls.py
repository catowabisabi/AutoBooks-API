from django.urls import path
from rest_framework.routers import DefaultRouter
from ai_assistants.views.analyst_viewset import (
    AnalystDataView,
    AnalystQueryView,
    StartDatasetLoadView as AnalystStartDatasetLoadView,
)
from ai_assistants.views.planner_viewset import (
    PlannerDataView,
    PlannerQueryView,
    StartDatasetLoadView as PlannerStartDatasetLoadView,
)
from ai_assistants.views.document_viewset import (
    DocumentUploadView,
    DocumentInfoView,
    DocumentQueryView,
    CombinedDocumentProcessingView
)
from ai_assistants.views.finance_viewset import ReceiptAnalyzerViewSet
from ai_assistants.views.ai_service_viewset import AIServiceViewSet
from ai_assistants.views.accounting_viewset import AccountingAssistantViewSet

# Router for viewsets
router = DefaultRouter()
router.register(r'ai-service', AIServiceViewSet, basename='ai-service')

urlpatterns = [
    # AI Service (unified AI API)
    path("ai-service/chat/", AIServiceViewSet.as_view({"post": "chat"}), name="ai-service-chat"),
    path("ai-service/chat-with-history/", AIServiceViewSet.as_view({"post": "chat_with_history"}), name="ai-service-chat-history"),
    path("ai-service/analyze-image/", AIServiceViewSet.as_view({"post": "analyze_image"}), name="ai-service-analyze-image"),
    path("ai-service/providers/", AIServiceViewSet.as_view({"get": "providers"}), name="ai-service-providers"),
    path("ai-service/models/", AIServiceViewSet.as_view({"get": "models"}), name="ai-service-models"),
    
    # Analyst Assistant
    path("analyst-assistant/start/", AnalystStartDatasetLoadView.as_view(), name="analyst-assistant-start"),
    path("analyst-assistant/data/", AnalystDataView.as_view(), name="analyst-assistant-data"),
    path("analyst-assistant/query/", AnalystQueryView.as_view(), name="analyst-assistant-query"),
    
    # Planner Assistant
    path("planner-assistant/start/", PlannerStartDatasetLoadView.as_view(), name="planner-assistant-start"),
    path("planner-assistant/data/", PlannerDataView.as_view(), name="planner-assistant-data"),
    path("planner-assistant/query/", PlannerQueryView.as_view(), name="planner-assistant-query"),

    # Document Assistant
    path("document-assistant/upload/", DocumentUploadView.as_view(), name="document-assistant-upload"),
    path("document-assistant/<str:document_id>/info/", DocumentInfoView.as_view(), name="document-assistant-info"),
    path("document-assistant/query/", DocumentQueryView.as_view(), name="document-assistant-query"),
    path('document-assistant/process/', CombinedDocumentProcessingView.as_view(), name='document-assistant-process'),
    
    # Finance Assistant
    path("finance-assistant/analyze/", ReceiptAnalyzerViewSet.as_view({"post": "analyze_receipt"}),
         name="finance-assistant-analyze"),
    
    # Accounting Assistant / 會計助手
    path("accounting-assistant/upload/", 
         AccountingAssistantViewSet.as_view({"post": "upload_receipt"}), 
         name="accounting-assistant-upload"),
    path("accounting-assistant/receipts/", 
         AccountingAssistantViewSet.as_view({"get": "list_receipts"}), 
         name="accounting-assistant-receipts"),
    path("accounting-assistant/receipts/<uuid:pk>/", 
         AccountingAssistantViewSet.as_view({"get": "get_receipt", "patch": "update_receipt"}), 
         name="accounting-assistant-receipt-detail"),
    path("accounting-assistant/receipts/<uuid:pk>/approve/", 
         AccountingAssistantViewSet.as_view({"post": "approve_receipt"}), 
         name="accounting-assistant-approve"),
    path("accounting-assistant/receipts/<uuid:pk>/create-journal/", 
         AccountingAssistantViewSet.as_view({"post": "create_journal_entry"}), 
         name="accounting-assistant-create-journal"),
    path("accounting-assistant/receipts/<uuid:pk>/ai-review/", 
         AccountingAssistantViewSet.as_view({"post": "ai_review_receipt"}), 
         name="accounting-assistant-ai-review"),
    path("accounting-assistant/compare/", 
         AccountingAssistantViewSet.as_view({"post": "compare_excel"}), 
         name="accounting-assistant-compare"),
    path("accounting-assistant/comparisons/", 
         AccountingAssistantViewSet.as_view({"get": "list_comparisons"}), 
         name="accounting-assistant-comparisons"),
    path("accounting-assistant/reports/create/", 
         AccountingAssistantViewSet.as_view({"post": "create_report"}), 
         name="accounting-assistant-create-report"),
    path("accounting-assistant/reports/", 
         AccountingAssistantViewSet.as_view({"get": "list_reports"}), 
         name="accounting-assistant-reports"),
    path("accounting-assistant/reports/<uuid:pk>/download/", 
         AccountingAssistantViewSet.as_view({"get": "download_report"}), 
         name="accounting-assistant-download-report"),
    path("accounting-assistant/reports/<uuid:pk>/approve/", 
         AccountingAssistantViewSet.as_view({"post": "approve_report"}), 
         name="accounting-assistant-approve-report"),
    path("accounting-assistant/ai-query/", 
         AccountingAssistantViewSet.as_view({"post": "ai_query"}), 
         name="accounting-assistant-ai-query"),
    path("accounting-assistant/stats/", 
         AccountingAssistantViewSet.as_view({"get": "get_stats"}), 
         name="accounting-assistant-stats"),
]
