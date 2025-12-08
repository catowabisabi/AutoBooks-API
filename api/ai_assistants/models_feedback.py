"""
AI Feedback Models
==================
Store user feedback on AI results for model improvement.
"""

from django.db import models
from django.conf import settings
from core.models import BaseModel


class AIFeedbackType(models.TextChoices):
    CORRECT = 'CORRECT', 'Correct'
    INCORRECT = 'INCORRECT', 'Incorrect'
    PARTIAL = 'PARTIAL', 'Partially Correct'
    UNSURE = 'UNSURE', 'Unsure'


class AIFeedback(BaseModel):
    """
    Store user feedback on AI extraction/classification results.
    Used to improve AI models and track accuracy over time.
    """
    # User who provided feedback
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_feedbacks'
    )
    
    # Reference to the AI result
    result_id = models.CharField(max_length=255, db_index=True, help_text='ID of the AI result being reviewed')
    result_type = models.CharField(max_length=100, default='general', help_text='Type of AI result (e.g., receipt_extraction, document_classification)')
    
    # Specific field feedback (optional)
    field_name = models.CharField(max_length=100, blank=True, help_text='Specific field being reviewed')
    original_value = models.TextField(blank=True, help_text='Original AI-extracted value')
    corrected_value = models.TextField(blank=True, help_text='User-corrected value')
    
    # Feedback details
    feedback_type = models.CharField(
        max_length=20,
        choices=AIFeedbackType.choices,
        default=AIFeedbackType.UNSURE
    )
    comment = models.TextField(blank=True, help_text='Additional user comments')
    rating = models.IntegerField(null=True, blank=True, help_text='User rating 1-5')
    
    # AI reasoning metadata
    ai_confidence = models.FloatField(null=True, blank=True, help_text='AI confidence score 0-1')
    ai_reasoning = models.TextField(blank=True, help_text='AI reasoning for the result')
    ai_alternatives = models.JSONField(default=list, blank=True, help_text='Alternative values considered')
    
    # Context metadata
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional context metadata')
    source_document = models.CharField(max_length=500, blank=True, help_text='Source document path/URL')
    
    # Processing status
    reviewed = models.BooleanField(default=False, help_text='Whether feedback has been reviewed by admin')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_feedbacks'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    action_taken = models.TextField(blank=True, help_text='Action taken based on feedback')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['result_id', 'field_name']),
            models.Index(fields=['result_type', 'feedback_type']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"Feedback on {self.result_type}/{self.result_id} by {self.user}"


class AIResultLog(BaseModel):
    """
    Log AI extraction/classification results with full reasoning.
    Used for debugging and model improvement.
    """
    # User context
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_result_logs'
    )
    
    # Result identification
    result_id = models.CharField(max_length=255, unique=True, db_index=True)
    result_type = models.CharField(max_length=100, db_index=True, default='general')
    
    # Input data
    source_content = models.TextField(blank=True, help_text='Original input content or reference')
    input_type = models.CharField(max_length=50, blank=True, help_text='image, document, text, etc.')
    input_hash = models.CharField(max_length=64, blank=True, help_text='Hash of input for deduplication')
    input_metadata = models.JSONField(default=dict, blank=True)
    
    # AI output - extracted fields with confidence
    extracted_fields = models.JSONField(
        default=list, 
        blank=True,
        help_text='List of extracted fields with structure: [{field_name, value, confidence, source_location, alternatives}]'
    )
    output_data = models.JSONField(default=dict, help_text='Full AI extraction result')
    overall_confidence = models.FloatField(default=0.0)
    
    # Reasoning and explainability
    reasoning = models.JSONField(default=dict, help_text='AI reasoning for each field')
    classification_factors = models.JSONField(default=list, help_text='Factors that influenced classification')
    alternatives_considered = models.JSONField(default=dict, help_text='Alternative values/classifications')
    
    # Model info
    model_provider = models.CharField(max_length=50, blank=True, help_text='AI provider used')
    model_name = models.CharField(max_length=100, blank=True, help_text='Model name/version')
    model_version = models.CharField(max_length=50, blank=True)
    
    # Performance metrics
    processing_time_ms = models.IntegerField(null=True, blank=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    
    # Feedback aggregation
    feedback_count = models.IntegerField(default=0)
    positive_feedback_count = models.IntegerField(default=0)
    negative_feedback_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['result_type', 'created_at']),
            models.Index(fields=['model_provider', 'model_name']),
        ]
    
    def __str__(self):
        return f"{self.result_type}/{self.result_id}"
    
    def update_feedback_counts(self):
        """Update feedback counts from related AIFeedback records"""
        feedbacks = AIFeedback.objects.filter(result_id=self.result_id)
        self.feedback_count = feedbacks.count()
        self.positive_feedback_count = feedbacks.filter(feedback_type=AIFeedbackType.CORRECT).count()
        self.negative_feedback_count = feedbacks.filter(feedback_type=AIFeedbackType.INCORRECT).count()
        self.save(update_fields=['feedback_count', 'positive_feedback_count', 'negative_feedback_count'])


# =================================================================
# RAG Observability Models
# =================================================================

class AIRequestType(models.TextChoices):
    """AI Request Types"""
    CHAT = 'CHAT', 'Chat Completion'
    EMBEDDING = 'EMBEDDING', 'Embedding'
    RAG = 'RAG', 'RAG Query'
    EXTRACTION = 'EXTRACTION', 'Data Extraction'
    CLASSIFICATION = 'CLASSIFICATION', 'Classification'
    SUMMARIZATION = 'SUMMARIZATION', 'Summarization'
    TRANSLATION = 'TRANSLATION', 'Translation'
    CODE_GEN = 'CODE_GEN', 'Code Generation'


class AIRequestStatus(models.TextChoices):
    """AI Request Status"""
    SUCCESS = 'SUCCESS', 'Success'
    FAILED = 'FAILED', 'Failed'
    TIMEOUT = 'TIMEOUT', 'Timeout'
    RATE_LIMITED = 'RATE_LIMITED', 'Rate Limited'
    CACHED = 'CACHED', 'Served from Cache'


class AIRequestLog(BaseModel):
    """
    Comprehensive AI Request Logging for Observability
    記錄所有AI請求的詳細信息，用於監控和優化
    """
    # Request identification
    request_id = models.CharField(max_length=100, unique=True, db_index=True)
    trace_id = models.CharField(max_length=100, blank=True, db_index=True, help_text='Distributed tracing ID')
    
    # User context
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_requests'
    )
    tenant_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Request type and status
    request_type = models.CharField(
        max_length=20,
        choices=AIRequestType.choices,
        default=AIRequestType.CHAT
    )
    status = models.CharField(
        max_length=20,
        choices=AIRequestStatus.choices,
        default=AIRequestStatus.SUCCESS
    )
    
    # Model information
    provider = models.CharField(max_length=50, db_index=True, help_text='openai, anthropic, google, deepseek')
    model = models.CharField(max_length=100, db_index=True, help_text='gpt-4o, claude-3-opus, etc.')
    
    # Token usage
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    
    # Cost tracking (in USD cents for precision)
    estimated_cost_cents = models.IntegerField(default=0, help_text='Estimated cost in cents')
    
    # Latency metrics (in milliseconds)
    latency_ms = models.IntegerField(default=0, help_text='Total request latency')
    ttfb_ms = models.IntegerField(null=True, blank=True, help_text='Time to first byte')
    
    # Request content (sanitized/truncated)
    prompt_preview = models.TextField(blank=True, help_text='First 500 chars of prompt')
    response_preview = models.TextField(blank=True, help_text='First 500 chars of response')
    
    # Context metadata
    endpoint = models.CharField(max_length=200, blank=True, help_text='API endpoint called')
    assistant_type = models.CharField(max_length=50, blank=True, help_text='analyst, planner, accounting, etc.')
    
    # Error tracking
    error_type = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Cache info
    cache_hit = models.BooleanField(default=False)
    cache_key = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provider', 'model', 'created_at']),
            models.Index(fields=['request_type', 'status', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['tenant_id', 'created_at']),
            models.Index(fields=['assistant_type', 'created_at']),
        ]
        verbose_name = 'AI Request Log'
        verbose_name_plural = 'AI Request Logs'
    
    def __str__(self):
        return f"{self.request_type}/{self.provider}/{self.model} - {self.status}"


class VectorSearchLog(BaseModel):
    """
    RAG Vector Search Logging for observability
    記錄向量搜索的詳細信息，用於優化RAG性能
    """
    # Request context
    request_log = models.ForeignKey(
        AIRequestLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vector_searches'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vector_searches'
    )
    tenant_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Query info
    query_text = models.TextField(help_text='Original search query')
    query_embedding_dim = models.IntegerField(default=1536, help_text='Embedding dimension used')
    
    # Collection/namespace
    collection_name = models.CharField(max_length=100, db_index=True, help_text='Vector DB collection')
    namespace = models.CharField(max_length=100, blank=True, help_text='Namespace within collection')
    
    # Search parameters
    top_k = models.IntegerField(default=10, help_text='Number of results requested')
    similarity_threshold = models.FloatField(default=0.0, help_text='Minimum similarity score')
    filters_applied = models.JSONField(default=dict, blank=True, help_text='Metadata filters')
    
    # Results metrics
    results_count = models.IntegerField(default=0, help_text='Actual results returned')
    avg_similarity_score = models.FloatField(null=True, blank=True, help_text='Average similarity of results')
    max_similarity_score = models.FloatField(null=True, blank=True, help_text='Highest similarity score')
    min_similarity_score = models.FloatField(null=True, blank=True, help_text='Lowest similarity score')
    
    # Result quality indicators
    above_threshold_count = models.IntegerField(default=0, help_text='Results above high confidence threshold (0.8)')
    below_threshold_count = models.IntegerField(default=0, help_text='Results below confidence threshold')
    
    # Retrieved document IDs (for debugging)
    retrieved_doc_ids = models.JSONField(default=list, blank=True, help_text='IDs of retrieved documents')
    retrieved_scores = models.JSONField(default=list, blank=True, help_text='Similarity scores')
    
    # Latency
    search_latency_ms = models.IntegerField(default=0, help_text='Vector search latency')
    embedding_latency_ms = models.IntegerField(default=0, help_text='Query embedding latency')
    total_latency_ms = models.IntegerField(default=0)
    
    # Reranking (if applied)
    rerank_applied = models.BooleanField(default=False)
    rerank_model = models.CharField(max_length=100, blank=True)
    rerank_latency_ms = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['collection_name', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['tenant_id', 'created_at']),
            models.Index(fields=['results_count', 'created_at']),
        ]
        verbose_name = 'Vector Search Log'
        verbose_name_plural = 'Vector Search Logs'
    
    def __str__(self):
        return f"VectorSearch in {self.collection_name}: {self.results_count} results"
    
    @property
    def is_empty_result(self):
        """Check if search returned no relevant results"""
        return self.results_count == 0
    
    @property
    def is_low_quality(self):
        """Check if results are below quality threshold"""
        return self.avg_similarity_score is not None and self.avg_similarity_score < 0.7


class KnowledgeGapLog(BaseModel):
    """
    Track queries that resulted in poor RAG results (knowledge gaps)
    追蹤RAG回答效果不佳的查詢，用於識別知識庫缺口
    """
    # Related search
    vector_search = models.ForeignKey(
        VectorSearchLog,
        on_delete=models.CASCADE,
        related_name='knowledge_gaps'
    )
    
    # User context
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='knowledge_gaps'
    )
    tenant_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Gap details
    query_text = models.TextField(help_text='Query that exposed the gap')
    gap_type = models.CharField(max_length=50, choices=[
        ('NO_RESULTS', 'No Results Found'),
        ('LOW_SIMILARITY', 'Low Similarity Scores'),
        ('IRRELEVANT', 'Results Not Relevant'),
        ('INCOMPLETE', 'Incomplete Information'),
        ('OUTDATED', 'Information Outdated'),
        ('USER_FLAGGED', 'Flagged by User'),
    ])
    
    # Expected vs actual
    expected_topic = models.CharField(max_length=200, blank=True, help_text='Topic user was looking for')
    actual_topics = models.JSONField(default=list, blank=True, help_text='Topics actually retrieved')
    
    # Quality indicators
    similarity_scores = models.JSONField(default=list, blank=True)
    user_feedback = models.TextField(blank=True, help_text='User feedback on why results were poor')
    feedback_rating = models.IntegerField(null=True, blank=True, help_text='User rating 1-5')
    
    # Resolution tracking
    is_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_knowledge_gaps'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Priority for addressing
    priority = models.CharField(max_length=20, default='MEDIUM', choices=[
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ])
    occurrence_count = models.IntegerField(default=1, help_text='How often this gap occurred')
    
    class Meta:
        ordering = ['-occurrence_count', '-created_at']
        indexes = [
            models.Index(fields=['gap_type', 'is_resolved']),
            models.Index(fields=['priority', 'is_resolved']),
            models.Index(fields=['tenant_id', 'created_at']),
        ]
        verbose_name = 'Knowledge Gap'
        verbose_name_plural = 'Knowledge Gaps'
    
    def __str__(self):
        return f"{self.gap_type}: {self.query_text[:50]}..."
    
    def increment_occurrence(self):
        """Increment occurrence count when same gap is detected"""
        self.occurrence_count += 1
        if self.occurrence_count >= 5:
            self.priority = 'HIGH'
        if self.occurrence_count >= 10:
            self.priority = 'CRITICAL'
        self.save(update_fields=['occurrence_count', 'priority'])


class AIUsageSummary(BaseModel):
    """
    Daily/Weekly AI Usage Summary for cost monitoring
    AI使用量彙總，用於成本監控和預算管理
    """
    # Time period
    date = models.DateField(db_index=True)
    period_type = models.CharField(max_length=20, default='DAILY', choices=[
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    ])
    
    # Tenant context
    tenant_id = models.CharField(max_length=100, db_index=True)
    
    # Aggregated metrics
    total_requests = models.IntegerField(default=0)
    successful_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)
    
    # Token usage by category
    total_prompt_tokens = models.BigIntegerField(default=0)
    total_completion_tokens = models.BigIntegerField(default=0)
    total_tokens = models.BigIntegerField(default=0)
    
    # Cost tracking (in cents)
    total_cost_cents = models.IntegerField(default=0)
    
    # By provider breakdown
    usage_by_provider = models.JSONField(default=dict, blank=True, help_text='{provider: {tokens, cost, requests}}')
    
    # By model breakdown
    usage_by_model = models.JSONField(default=dict, blank=True, help_text='{model: {tokens, cost, requests}}')
    
    # By request type breakdown
    usage_by_type = models.JSONField(default=dict, blank=True, help_text='{type: {tokens, cost, requests}}')
    
    # Performance metrics
    avg_latency_ms = models.IntegerField(default=0)
    p95_latency_ms = models.IntegerField(default=0)
    p99_latency_ms = models.IntegerField(default=0)
    
    # RAG specific
    total_vector_searches = models.IntegerField(default=0)
    avg_results_per_search = models.FloatField(default=0.0)
    avg_similarity_score = models.FloatField(default=0.0)
    knowledge_gaps_detected = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['date', 'period_type', 'tenant_id']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['tenant_id', 'date']),
            models.Index(fields=['period_type', 'date']),
        ]
        verbose_name = 'AI Usage Summary'
        verbose_name_plural = 'AI Usage Summaries'
    
    def __str__(self):
        return f"{self.tenant_id} - {self.date} ({self.period_type})"
