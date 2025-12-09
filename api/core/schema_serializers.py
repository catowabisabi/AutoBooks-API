"""
Schema Serializers for drf-spectacular OpenAPI generation.
These serializers are used only for API documentation, not for actual request/response handling.
"""
from rest_framework import serializers


# =============================================================================
# Auth Views Serializers
# =============================================================================

class SignUpRequestSerializer(serializers.Serializer):
    """Request serializer for SignUpView"""
    email = serializers.EmailField()
    password = serializers.CharField()
    full_name = serializers.CharField(required=False)
    language = serializers.CharField(required=False, default='en')


class ForgotPasswordRequestSerializer(serializers.Serializer):
    """Request serializer for ForgotPasswordView"""
    email = serializers.EmailField()
    language = serializers.CharField(required=False, default='en')


class ResetPasswordRequestSerializer(serializers.Serializer):
    """Request serializer for ResetPasswordView"""
    token = serializers.CharField()
    password = serializers.CharField()
    language = serializers.CharField(required=False, default='en')


class ChangePasswordRequestSerializer(serializers.Serializer):
    """Request serializer for ChangePasswordView"""
    old_password = serializers.CharField()
    new_password = serializers.CharField()


class LockAccountRequestSerializer(serializers.Serializer):
    """Request serializer for LockAccountView"""
    user_id = serializers.UUIDField()
    reason = serializers.CharField(required=False)
    duration_hours = serializers.IntegerField(required=False)


class UnlockAccountRequestSerializer(serializers.Serializer):
    """Request serializer for UnlockAccountView"""
    user_id = serializers.UUIDField()


# =============================================================================
# Google OAuth Serializers
# =============================================================================

class GoogleOAuthRequestSerializer(serializers.Serializer):
    """Request serializer for GoogleOAuth views"""
    code = serializers.CharField(required=False)
    credential = serializers.CharField(required=False)


# =============================================================================
# RAG Views Serializers
# =============================================================================

class RAGQueryRequestSerializer(serializers.Serializer):
    """Request serializer for RAGQueryView"""
    query = serializers.CharField()
    category = serializers.CharField(required=False)
    include_context = serializers.BooleanField(default=True)


class RAGChatRequestSerializer(serializers.Serializer):
    """Request serializer for RAGChatView"""
    query = serializers.CharField()
    category = serializers.CharField(required=False)
    provider = serializers.ChoiceField(choices=['openai', 'gemini', 'deepseek'], default='openai')


# =============================================================================
# API Key Views Serializers
# =============================================================================

class ApiKeyRequestSerializer(serializers.Serializer):
    """Request serializer for ApiKeyManageView"""
    api_key = serializers.CharField()


# =============================================================================
# Analytics Serializers
# =============================================================================

class AnalyticsDashboardResponseSerializer(serializers.Serializer):
    """Response serializer for AnalyticsDashboardView"""
    current_month = serializers.DictField(required=False)
    previous_month = serializers.DictField(required=False)
    kpis = serializers.ListField(required=False)


# =============================================================================
# Business Serializers
# =============================================================================

class DashboardOverviewResponseSerializer(serializers.Serializer):
    """Response serializer for DashboardOverviewView"""
    audits = serializers.DictField(required=False)
    tax_returns = serializers.DictField(required=False)
    billable_hours = serializers.DictField(required=False)
    revenue = serializers.DictField(required=False)


# =============================================================================
# HRMS Serializers
# =============================================================================

class HRMSDashboardResponseSerializer(serializers.Serializer):
    """Response serializer for HRMSDashboardView"""
    employees = serializers.DictField(required=False)
    leaves = serializers.DictField(required=False)
    payroll = serializers.DictField(required=False)


# =============================================================================
# CoreData Serializers
# =============================================================================

class CountryListResponseSerializer(serializers.Serializer):
    """Response serializer for country_list"""
    success = serializers.BooleanField()
    data = serializers.ListField()
    count = serializers.IntegerField()


class CurrencyListResponseSerializer(serializers.Serializer):
    """Response serializer for currency_list"""
    success = serializers.BooleanField()
    data = serializers.ListField()
    count = serializers.IntegerField()


class TimezoneListResponseSerializer(serializers.Serializer):
    """Response serializer for timezone_list"""
    success = serializers.BooleanField()
    data = serializers.ListField()
    count = serializers.IntegerField()


# =============================================================================
# Health Check Serializers
# =============================================================================

class HealthCheckResponseSerializer(serializers.Serializer):
    """Response serializer for health_check"""
    status = serializers.CharField()
    message = serializers.CharField()
    timestamp = serializers.DateTimeField()


# =============================================================================
# AI Assistants - Agent Serializers
# =============================================================================

class AIAgentChatRequestSerializer(serializers.Serializer):
    """Request serializer for AIAgentViewSet.chat"""
    message = serializers.CharField()
    session_id = serializers.CharField(required=False)
    agent_id = serializers.UUIDField(required=False)
    auto_execute = serializers.BooleanField(default=True)


# =============================================================================
# AI Assistants - Analyst Serializers
# =============================================================================

class AnalystQueryRequestSerializer(serializers.Serializer):
    """Request serializer for AnalystQueryView"""
    query = serializers.CharField()


class AnalystDataResponseSerializer(serializers.Serializer):
    """Response serializer for AnalystDataView"""
    data = serializers.ListField(required=False)
    error = serializers.CharField(required=False)


# =============================================================================
# AI Assistants - Document Serializers
# =============================================================================

class DocumentUploadResponseSerializer(serializers.Serializer):
    """Response serializer for DocumentUploadView"""
    document_id = serializers.CharField()
    filename = serializers.CharField()
    status = serializers.CharField()


class DocumentInfoResponseSerializer(serializers.Serializer):
    """Response serializer for DocumentInfoView"""
    document_id = serializers.CharField()
    filename = serializers.CharField()
    content = serializers.CharField(required=False)
    metadata = serializers.DictField(required=False)


# =============================================================================
# AI Assistants - Finance Serializers
# =============================================================================

class ReceiptAnalyzeRequestSerializer(serializers.Serializer):
    """Request serializer for ReceiptAnalyzerViewSet"""
    file = serializers.FileField()
    category = serializers.JSONField(required=False, default=list)


# =============================================================================
# AI Assistants - Planner Serializers
# =============================================================================

class PlannerDataResponseSerializer(serializers.Serializer):
    """Response serializer for PlannerDataView"""
    data = serializers.ListField(required=False)
    error = serializers.CharField(required=False)


# =============================================================================
# AI Assistants - Task Serializers
# =============================================================================

class TaskProgressResponseSerializer(serializers.Serializer):
    """Response serializer for TaskProgressView"""
    task_id = serializers.CharField()
    status = serializers.CharField()
    progress = serializers.IntegerField()
    message = serializers.CharField(required=False)


class AsyncTaskResponseSerializer(serializers.Serializer):
    """Response serializer for AsyncTaskViewSet"""
    id = serializers.CharField()
    celery_task_id = serializers.CharField()
    task_type = serializers.CharField()
    name = serializers.CharField()
    status = serializers.CharField()
    progress = serializers.IntegerField()
    progress_message = serializers.CharField(required=False)
    started_at = serializers.DateTimeField(required=False)
    completed_at = serializers.DateTimeField(required=False)
    duration_seconds = serializers.FloatField(required=False)
    result = serializers.JSONField(required=False)
    error_message = serializers.CharField(required=False)


# =============================================================================
# AI Assistants - AI Service Serializers
# =============================================================================

class AIChatRequestSerializer(serializers.Serializer):
    """Request serializer for AIServiceViewSet.chat"""
    message = serializers.CharField()
    provider = serializers.ChoiceField(choices=['openai', 'gemini', 'deepseek'], default='openai')
    model = serializers.CharField(required=False)
    system_prompt = serializers.CharField(required=False)
    temperature = serializers.FloatField(required=False, default=0.7)
    max_tokens = serializers.IntegerField(required=False, default=2000)


class AIChatWithHistoryRequestSerializer(serializers.Serializer):
    """Request serializer for AIServiceViewSet.chat_with_history"""
    messages = serializers.ListField(child=serializers.DictField())
    provider = serializers.ChoiceField(choices=['openai', 'gemini', 'deepseek'], default='openai')
    model = serializers.CharField(required=False)
    system_prompt = serializers.CharField(required=False)
    temperature = serializers.FloatField(required=False, default=0.7)
    max_tokens = serializers.IntegerField(required=False, default=2000)


class AIAnalyzeImageRequestSerializer(serializers.Serializer):
    """Request serializer for AIServiceViewSet.analyze_image"""
    image = serializers.CharField(required=False, help_text="Base64 encoded image")
    prompt = serializers.CharField()
    provider = serializers.ChoiceField(choices=['openai', 'gemini'], default='gemini')
    mime_type = serializers.CharField(required=False, default='image/jpeg')


# =============================================================================
# AI Assistants - Feedback Serializers
# =============================================================================

class RAGObservabilityDashboardResponseSerializer(serializers.Serializer):
    """Response serializer for RAGObservabilityDashboardViewSet"""
    total_requests = serializers.IntegerField()
    total_searches = serializers.IntegerField()
    knowledge_gaps = serializers.IntegerField()
    metrics = serializers.DictField(required=False)


# =============================================================================
# Accounting - Report Serializers
# =============================================================================

class TrialBalanceResponseSerializer(serializers.Serializer):
    """Response serializer for ReportViewSet.trial_balance"""
    accounts = serializers.ListField()
    totals = serializers.DictField()


class BalanceSheetResponseSerializer(serializers.Serializer):
    """Response serializer for ReportViewSet.balance_sheet"""
    as_of_date = serializers.DateField(required=False)
    assets = serializers.DecimalField(max_digits=20, decimal_places=2)
    liabilities = serializers.DecimalField(max_digits=20, decimal_places=2)
    equity = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_liabilities_equity = serializers.DecimalField(max_digits=20, decimal_places=2)
    is_balanced = serializers.BooleanField()


class IncomeStatementResponseSerializer(serializers.Serializer):
    """Response serializer for ReportViewSet.income_statement"""
    period = serializers.DictField()
    revenue = serializers.DecimalField(max_digits=20, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=20, decimal_places=2)
    net_income = serializers.DecimalField(max_digits=20, decimal_places=2)


# =============================================================================
# Tenant Serializers
# =============================================================================

class InvitationAcceptResponseSerializer(serializers.Serializer):
    """Response serializer for InvitationViewSet.accept"""
    message = serializers.CharField()
    membership = serializers.DictField()


# =============================================================================
# Visualization Serializers
# =============================================================================

class ChartTypesResponseSerializer(serializers.Serializer):
    """Response serializer for ChartTypesView"""
    chart_types = serializers.DictField()
    message = serializers.CharField()

# =============================================================================
# User Settings Serializers
# =============================================================================

class UserSettingsResponseSerializer(serializers.Serializer):
    """Response serializer for UserSettingsViewSet"""
    success = serializers.BooleanField()
    data = serializers.DictField()


class UserSubscriptionResponseSerializer(serializers.Serializer):
    """Response serializer for UserSubscriptionViewSet"""
    success = serializers.BooleanField()
    data = serializers.DictField()
