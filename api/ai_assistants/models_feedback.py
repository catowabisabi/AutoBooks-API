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
