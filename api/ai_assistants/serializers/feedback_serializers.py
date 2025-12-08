"""
AI Feedback Serializers
=======================
Serializers for AI feedback and result logging.
"""

from rest_framework import serializers
from ..models_feedback import AIFeedback, AIResultLog, AIFeedbackType


class AIFeedbackSerializer(serializers.ModelSerializer):
    """Full serializer for AI Feedback"""
    feedback_type_display = serializers.CharField(source='get_feedback_type_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = AIFeedback
        fields = [
            'id',
            'result_id',
            'result_type',
            'feedback_type',
            'feedback_type_display',
            'field_name',
            'original_value',
            'corrected_value',
            'comment',
            'rating',
            'user_email',
            'metadata',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'user_email']


class AIFeedbackCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating AI Feedback"""
    
    class Meta:
        model = AIFeedback
        fields = [
            'result_id',
            'result_type',
            'feedback_type',
            'field_name',
            'original_value',
            'corrected_value',
            'comment',
            'rating',
            'metadata',
        ]
    
    def validate_rating(self, value):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
    def validate_feedback_type(self, value):
        valid_types = [t.value for t in AIFeedbackType]
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid feedback type. Must be one of: {valid_types}")
        return value


class ExtractionFieldSerializer(serializers.Serializer):
    """Serializer for individual extraction fields"""
    field_name = serializers.CharField()
    value = serializers.CharField(allow_blank=True)
    confidence = serializers.FloatField(min_value=0, max_value=1)
    source_location = serializers.DictField(required=False)
    alternatives = serializers.ListField(child=serializers.CharField(), required=False)


class AIResultLogSerializer(serializers.ModelSerializer):
    """Full serializer for AI Result Logs"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    extracted_fields = ExtractionFieldSerializer(many=True, read_only=True)
    has_low_confidence = serializers.SerializerMethodField()
    
    class Meta:
        model = AIResultLog
        fields = [
            'id',
            'result_id',
            'result_type',
            'user_email',
            'source_content',
            'extracted_fields',
            'overall_confidence',
            'has_low_confidence',
            'reasoning',
            'classification_factors',
            'alternatives_considered',
            'model_version',
            'processing_time_ms',
            'feedback_count',
            'positive_feedback_count',
            'negative_feedback_count',
            'created_at',
        ]
        read_only_fields = [
            'id', 
            'created_at', 
            'user_email',
            'feedback_count',
            'positive_feedback_count',
            'negative_feedback_count',
        ]
    
    def get_has_low_confidence(self, obj):
        """Check if any field has low confidence (below 0.7)"""
        if not obj.extracted_fields:
            return False
        for field in obj.extracted_fields:
            if field.get('confidence', 1.0) < 0.7:
                return True
        return False


class AIResultLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating AI Result Logs"""
    extracted_fields = ExtractionFieldSerializer(many=True, required=False)
    
    class Meta:
        model = AIResultLog
        fields = [
            'result_id',
            'result_type',
            'source_content',
            'extracted_fields',
            'overall_confidence',
            'reasoning',
            'classification_factors',
            'alternatives_considered',
            'model_version',
            'processing_time_ms',
        ]
    
    def validate_overall_confidence(self, value):
        if value is not None and (value < 0 or value > 1):
            raise serializers.ValidationError("Confidence must be between 0 and 1")
        return value


class AIExplanationSerializer(serializers.Serializer):
    """Serializer for AI explanation responses"""
    result_id = serializers.CharField()
    summary = serializers.CharField()
    reasoning_steps = serializers.ListField(child=serializers.CharField())
    classification_factors = serializers.ListField(child=serializers.DictField())
    confidence_breakdown = serializers.DictField()
    alternatives = serializers.ListField(child=serializers.DictField(), required=False)


class BulkFeedbackSerializer(serializers.Serializer):
    """Serializer for bulk feedback submission"""
    feedbacks = AIFeedbackCreateSerializer(many=True)
    
    def validate_feedbacks(self, value):
        if len(value) > 50:
            raise serializers.ValidationError("Maximum 50 feedbacks per request")
        return value


# =================================================================
# RAG Observability Serializers
# =================================================================

from ..models_feedback import (
    AIRequestLog, AIRequestType, AIRequestStatus,
    VectorSearchLog, KnowledgeGapLog, AIUsageSummary
)


class AIRequestLogSerializer(serializers.ModelSerializer):
    """Serializer for AI Request Logs"""
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    cost_usd = serializers.SerializerMethodField()
    
    class Meta:
        model = AIRequestLog
        fields = [
            'id',
            'request_id',
            'trace_id',
            'user_email',
            'tenant_id',
            'request_type',
            'request_type_display',
            'status',
            'status_display',
            'provider',
            'model',
            'prompt_tokens',
            'completion_tokens',
            'total_tokens',
            'estimated_cost_cents',
            'cost_usd',
            'latency_ms',
            'ttfb_ms',
            'prompt_preview',
            'response_preview',
            'endpoint',
            'assistant_type',
            'error_type',
            'error_message',
            'retry_count',
            'cache_hit',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_cost_usd(self, obj):
        """Convert cents to USD"""
        return obj.estimated_cost_cents / 100 if obj.estimated_cost_cents else 0


class AIRequestLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating AI Request Logs"""
    
    class Meta:
        model = AIRequestLog
        fields = [
            'request_id',
            'trace_id',
            'tenant_id',
            'request_type',
            'status',
            'provider',
            'model',
            'prompt_tokens',
            'completion_tokens',
            'total_tokens',
            'estimated_cost_cents',
            'latency_ms',
            'ttfb_ms',
            'prompt_preview',
            'response_preview',
            'endpoint',
            'assistant_type',
            'error_type',
            'error_message',
            'retry_count',
            'cache_hit',
            'cache_key',
        ]


class VectorSearchLogSerializer(serializers.ModelSerializer):
    """Serializer for Vector Search Logs"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    quality_indicator = serializers.SerializerMethodField()
    
    class Meta:
        model = VectorSearchLog
        fields = [
            'id',
            'request_log',
            'user_email',
            'tenant_id',
            'query_text',
            'collection_name',
            'namespace',
            'top_k',
            'similarity_threshold',
            'filters_applied',
            'results_count',
            'avg_similarity_score',
            'max_similarity_score',
            'min_similarity_score',
            'above_threshold_count',
            'below_threshold_count',
            'search_latency_ms',
            'embedding_latency_ms',
            'total_latency_ms',
            'rerank_applied',
            'rerank_model',
            'rerank_latency_ms',
            'quality_indicator',
            'is_empty_result',
            'is_low_quality',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'is_empty_result', 'is_low_quality']
    
    def get_quality_indicator(self, obj):
        """Return quality indicator: GOOD, FAIR, POOR"""
        if obj.is_empty_result:
            return 'EMPTY'
        if obj.avg_similarity_score is None:
            return 'UNKNOWN'
        if obj.avg_similarity_score >= 0.8:
            return 'GOOD'
        if obj.avg_similarity_score >= 0.6:
            return 'FAIR'
        return 'POOR'


class VectorSearchLogCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Vector Search Logs"""
    
    class Meta:
        model = VectorSearchLog
        fields = [
            'request_log',
            'tenant_id',
            'query_text',
            'query_embedding_dim',
            'collection_name',
            'namespace',
            'top_k',
            'similarity_threshold',
            'filters_applied',
            'results_count',
            'avg_similarity_score',
            'max_similarity_score',
            'min_similarity_score',
            'above_threshold_count',
            'below_threshold_count',
            'retrieved_doc_ids',
            'retrieved_scores',
            'search_latency_ms',
            'embedding_latency_ms',
            'total_latency_ms',
            'rerank_applied',
            'rerank_model',
            'rerank_latency_ms',
        ]


class KnowledgeGapLogSerializer(serializers.ModelSerializer):
    """Serializer for Knowledge Gap Logs"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    resolved_by_email = serializers.EmailField(source='resolved_by.email', read_only=True)
    gap_type_display = serializers.CharField(source='get_gap_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = KnowledgeGapLog
        fields = [
            'id',
            'vector_search',
            'user_email',
            'tenant_id',
            'query_text',
            'gap_type',
            'gap_type_display',
            'expected_topic',
            'actual_topics',
            'similarity_scores',
            'user_feedback',
            'feedback_rating',
            'is_resolved',
            'resolution_notes',
            'resolved_by_email',
            'resolved_at',
            'priority',
            'priority_display',
            'occurrence_count',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'resolved_by_email']


class KnowledgeGapCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Knowledge Gap entries"""
    
    class Meta:
        model = KnowledgeGapLog
        fields = [
            'vector_search',
            'tenant_id',
            'query_text',
            'gap_type',
            'expected_topic',
            'actual_topics',
            'similarity_scores',
            'user_feedback',
            'feedback_rating',
        ]


class KnowledgeGapResolveSerializer(serializers.Serializer):
    """Serializer for resolving a Knowledge Gap"""
    resolution_notes = serializers.CharField(required=True)
    is_resolved = serializers.BooleanField(default=True)


class AIUsageSummarySerializer(serializers.ModelSerializer):
    """Serializer for AI Usage Summary"""
    cost_usd = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = AIUsageSummary
        fields = [
            'id',
            'date',
            'period_type',
            'tenant_id',
            'total_requests',
            'successful_requests',
            'failed_requests',
            'success_rate',
            'total_prompt_tokens',
            'total_completion_tokens',
            'total_tokens',
            'total_cost_cents',
            'cost_usd',
            'usage_by_provider',
            'usage_by_model',
            'usage_by_type',
            'avg_latency_ms',
            'p95_latency_ms',
            'p99_latency_ms',
            'total_vector_searches',
            'avg_results_per_search',
            'avg_similarity_score',
            'knowledge_gaps_detected',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_cost_usd(self, obj):
        return obj.total_cost_cents / 100 if obj.total_cost_cents else 0
    
    def get_success_rate(self, obj):
        if obj.total_requests > 0:
            return round(obj.successful_requests / obj.total_requests * 100, 2)
        return 0


# =================================================================
# Dashboard & Analytics Serializers
# =================================================================

class RAGObservabilityDashboardSerializer(serializers.Serializer):
    """Serializer for RAG Observability Dashboard data"""
    # Summary stats
    total_requests = serializers.IntegerField()
    total_tokens = serializers.IntegerField()
    total_cost_usd = serializers.FloatField()
    avg_latency_ms = serializers.IntegerField()
    success_rate = serializers.FloatField()
    
    # RAG specific
    total_vector_searches = serializers.IntegerField()
    avg_similarity_score = serializers.FloatField()
    knowledge_gaps_count = serializers.IntegerField()
    unresolved_gaps_count = serializers.IntegerField()
    
    # Trends (lists of dicts with date + value)
    requests_trend = serializers.ListField(child=serializers.DictField())
    tokens_trend = serializers.ListField(child=serializers.DictField())
    latency_trend = serializers.ListField(child=serializers.DictField())
    cost_trend = serializers.ListField(child=serializers.DictField())
    
    # Top items
    top_failing_queries = serializers.ListField(child=serializers.DictField())
    top_knowledge_gaps = serializers.ListField(child=serializers.DictField())
    usage_by_model = serializers.DictField()
    usage_by_assistant = serializers.DictField()


class TokenUsageBreakdownSerializer(serializers.Serializer):
    """Serializer for token usage breakdown"""
    provider = serializers.CharField()
    model = serializers.CharField()
    prompt_tokens = serializers.IntegerField()
    completion_tokens = serializers.IntegerField()
    total_tokens = serializers.IntegerField()
    estimated_cost_usd = serializers.FloatField()
    request_count = serializers.IntegerField()


class FailingQuerySerializer(serializers.Serializer):
    """Serializer for failing query analysis"""
    query_text = serializers.CharField()
    failure_count = serializers.IntegerField()
    avg_similarity = serializers.FloatField()
    last_occurred = serializers.DateTimeField()
    gap_type = serializers.CharField(required=False)
