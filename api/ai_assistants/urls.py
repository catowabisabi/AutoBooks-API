from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ai_assistants.views.analyst_viewset import (
    AnalystDataView,
    AnalystDataStatusView,
    AnalystQueryView,
    AnalystSchemaView,
    StartDatasetLoadView as AnalystStartDatasetLoadView,
)
from ai_assistants.views.planner_viewset import (
    PlannerDataView,
    PlannerQueryView,
    StartDatasetLoadView as PlannerStartDatasetLoadView,
    PlannerTaskViewSet,
    ScheduleEventViewSet,
)
from ai_assistants.views.document_viewset import (
    DocumentUploadView,
    DocumentInfoView,
    DocumentQueryView,
    CombinedDocumentProcessingView,
    AIDocumentViewSet,
    DocumentComparisonViewSet,
)
from ai_assistants.views.email_viewset import (
    EmailViewSet,
    EmailAccountViewSet,
    EmailTemplateViewSet,
    EmailAttachmentViewSet,
)
from ai_assistants.views.brainstorm_viewset import (
    BrainstormSessionViewSet,
    BrainstormIdeaViewSet,
    BrainstormMeetingViewSet,
    BrainstormMeetingParticipantViewSet,
)
from ai_assistants.views.finance_viewset import ReceiptAnalyzerViewSet
from ai_assistants.views.ai_service_viewset import AIServiceViewSet
from ai_assistants.views.accounting_viewset import AccountingAssistantViewSet
from ai_assistants.views.agent_viewset import AIAgentViewSet
from ai_assistants.views.visualization_viewset import (
    ChartTypesView,
    AnalyzeDataView,
    GenerateChartView,
    GenerateChartWithAIView,
    DocumentChartView,
    FileVisualizationView,
    DashboardChartsView,
    QuickChartView,
)
from ai_assistants.views.project_viewset import (
    AccountingProjectViewSet,
    UnrecognizedReceiptsViewSet,
)
from ai_assistants.views.feedback_viewset import (
    AIFeedbackViewSet,
    AIResultLogViewSet,
)
from ai_assistants.views.task_viewset import (
    AsyncTaskViewSet,
    TaskProgressView,
)

# Router for viewsets
router = DefaultRouter()
router.register(r'ai-service', AIServiceViewSet, basename='ai-service')

# Email Assistant Router
router.register(r'email-assistant/accounts', EmailAccountViewSet, basename='email-account')
router.register(r'email-assistant/emails', EmailViewSet, basename='email')
router.register(r'email-assistant/templates', EmailTemplateViewSet, basename='email-template')
router.register(r'email-assistant/attachments', EmailAttachmentViewSet, basename='email-attachment')

# Planner Assistant Router  
router.register(r'planner-assistant/tasks', PlannerTaskViewSet, basename='planner-task')
router.register(r'planner-assistant/events', ScheduleEventViewSet, basename='schedule-event')

# Document Assistant Router
router.register(r'document-assistant/documents', AIDocumentViewSet, basename='ai-document')
router.register(r'document-assistant/comparisons', DocumentComparisonViewSet, basename='document-comparison')

# Accounting Projects Router / 會計項目路由
router.register(r'accounting-projects', AccountingProjectViewSet, basename='accounting-project')

# Brainstorming Assistant Router
router.register(r'brainstorm-assistant/sessions', BrainstormSessionViewSet, basename='brainstorm-session')
router.register(r'brainstorm-assistant/ideas', BrainstormIdeaViewSet, basename='brainstorm-idea')
router.register(r'brainstorm-assistant/meetings', BrainstormMeetingViewSet, basename='brainstorm-meeting')
router.register(r'brainstorm-assistant/participants', BrainstormMeetingParticipantViewSet, basename='brainstorm-participant')

# AI Feedback & Results Router
router.register(r'ai-feedback', AIFeedbackViewSet, basename='ai-feedback')
router.register(r'ai-results', AIResultLogViewSet, basename='ai-result')

# Async Tasks Router
router.register(r'tasks', AsyncTaskViewSet, basename='async-task')

urlpatterns = [
    # AI Service (unified AI API)
    path("ai-service/chat/", AIServiceViewSet.as_view({"post": "chat"}), name="ai-service-chat"),
    path("ai-service/chat-with-history/", AIServiceViewSet.as_view({"post": "chat_with_history"}), name="ai-service-chat-history"),
    path("ai-service/analyze-image/", AIServiceViewSet.as_view({"post": "analyze_image"}), name="ai-service-analyze-image"),
    path("ai-service/providers/", AIServiceViewSet.as_view({"get": "providers"}), name="ai-service-providers"),
    path("ai-service/models/", AIServiceViewSet.as_view({"get": "models"}), name="ai-service-models"),
    path("ai-service/module-analyze/", AIServiceViewSet.as_view({"post": "module_analyze"}), name="ai-service-module-analyze"),
    
    # Analyst Assistant
    path("analyst-assistant/start/", AnalystStartDatasetLoadView.as_view(), name="analyst-assistant-start"),
    path("analyst-assistant/data/", AnalystDataView.as_view(), name="analyst-assistant-data"),
    path("analyst-assistant/status/", AnalystDataStatusView.as_view(), name="analyst-assistant-status"),
    path("analyst-assistant/query/", AnalystQueryView.as_view(), name="analyst-assistant-query"),
    path("analyst-assistant/schema/", AnalystSchemaView.as_view(), name="analyst-assistant-schema"),
    
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
    path("finance-assistant/analyze-report/", ReceiptAnalyzerViewSet.as_view({"post": "analyze_report"}),
         name="finance-assistant-analyze-report"),
    path("finance-assistant/compare-periods/", ReceiptAnalyzerViewSet.as_view({"post": "compare_periods"}),
         name="finance-assistant-compare-periods"),
    path("finance-assistant/forecast/", ReceiptAnalyzerViewSet.as_view({"post": "forecast"}),
         name="finance-assistant-forecast"),
    
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
    
    # Unrecognized Receipts / 無法識別收據
    path("accounting-assistant/unrecognized/", 
         UnrecognizedReceiptsViewSet.as_view({"get": "list"}), 
         name="accounting-assistant-unrecognized"),
    path("accounting-assistant/unrecognized/<uuid:pk>/", 
         UnrecognizedReceiptsViewSet.as_view({"get": "retrieve"}), 
         name="accounting-assistant-unrecognized-detail"),
    path("accounting-assistant/unrecognized/<uuid:pk>/reclassify/", 
         UnrecognizedReceiptsViewSet.as_view({"post": "reclassify"}), 
         name="accounting-assistant-reclassify"),
    path("accounting-assistant/unrecognized/batch-reclassify/", 
         UnrecognizedReceiptsViewSet.as_view({"post": "batch_reclassify"}), 
         name="accounting-assistant-batch-reclassify"),
    
    # AI Agent / AI代理 (Autonomous CRUD with logging)
    path("agent/chat/", 
         AIAgentViewSet.as_view({"post": "chat"}), 
         name="ai-agent-chat"),
    path("agent/agents/", 
         AIAgentViewSet.as_view({"get": "agents"}), 
         name="ai-agent-agents"),
    path("agent/tools/", 
         AIAgentViewSet.as_view({"get": "tools"}), 
         name="ai-agent-tools"),
    path("agent/actions/", 
         AIAgentViewSet.as_view({"get": "actions"}), 
         name="ai-agent-actions"),
    path("agent/actions/<uuid:pk>/rollback/", 
         AIAgentViewSet.as_view({"post": "rollback_action"}), 
         name="ai-agent-rollback"),
    path("agent/sessions/", 
         AIAgentViewSet.as_view({"get": "sessions"}), 
         name="ai-agent-sessions"),
    path("agent/sessions/<str:session_id>/", 
         AIAgentViewSet.as_view({"get": "get_session"}), 
         name="ai-agent-session-detail"),
    
    # Visualization API / 視覺化 API
    path("visualization/chart-types/", 
         ChartTypesView.as_view(), 
         name="visualization-chart-types"),
    path("visualization/analyze/", 
         AnalyzeDataView.as_view(), 
         name="visualization-analyze"),
    path("visualization/generate/", 
         GenerateChartView.as_view(), 
         name="visualization-generate"),
    path("visualization/generate-ai/", 
         GenerateChartWithAIView.as_view(), 
         name="visualization-generate-ai"),
    path("visualization/document/<int:document_id>/", 
         DocumentChartView.as_view(), 
         name="visualization-document"),
    path("visualization/upload/", 
         FileVisualizationView.as_view(), 
         name="visualization-upload"),
    path("visualization/dashboard/", 
         DashboardChartsView.as_view(), 
         name="visualization-dashboard"),
    path("visualization/quick/", 
         QuickChartView.as_view(), 
         name="visualization-quick"),
    
    # Task Progress API / 任務進度 API
    path("task-status/<str:task_id>/", 
         TaskProgressView.as_view(), 
         name="task-status"),
    
    # Include router URLs
    path("", include(router.urls)),
]
