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
