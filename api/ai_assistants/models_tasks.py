"""
Async Task Models
==================
Track async task status and progress for long-running operations.
"""

from django.db import models
from django.conf import settings
from core.models import BaseModel


class TaskStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    STARTED = 'STARTED', 'Started'
    PROGRESS = 'PROGRESS', 'In Progress'
    SUCCESS = 'SUCCESS', 'Success'
    FAILURE = 'FAILURE', 'Failed'
    REVOKED = 'REVOKED', 'Cancelled'


class TaskType(models.TextChoices):
    OCR_PROCESS = 'OCR_PROCESS', 'OCR Processing'
    DOCUMENT_ANALYSIS = 'DOCUMENT_ANALYSIS', 'Document Analysis'
    REPORT_GENERATION = 'REPORT_GENERATION', 'Report Generation'
    BULK_IMPORT = 'BULK_IMPORT', 'Bulk Import'
    AI_ANALYSIS = 'AI_ANALYSIS', 'AI Analysis'
    DATA_EXPORT = 'DATA_EXPORT', 'Data Export'
    EMAIL_PROCESSING = 'EMAIL_PROCESSING', 'Email Processing'


class AsyncTask(BaseModel):
    """
    Track async task status and progress.
    Links Celery task IDs to user-facing task information.
    """
    # Celery task reference
    celery_task_id = models.CharField(max_length=255, unique=True, db_index=True)
    
    # User context
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='async_tasks'
    )
    
    # Task metadata
    task_type = models.CharField(
        max_length=50,
        choices=TaskType.choices,
        default=TaskType.AI_ANALYSIS
    )
    name = models.CharField(max_length=255, help_text='Human-readable task name')
    description = models.TextField(blank=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING
    )
    progress = models.IntegerField(default=0, help_text='Progress percentage 0-100')
    progress_message = models.CharField(max_length=500, blank=True, help_text='Current progress step')
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_completion = models.DateTimeField(null=True, blank=True)
    
    # Result data
    result = models.JSONField(default=dict, blank=True, help_text='Task result data')
    result_file = models.FileField(upload_to='task_results/', null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    # Input data
    input_data = models.JSONField(default=dict, blank=True, help_text='Task input parameters')
    input_files = models.JSONField(default=list, blank=True, help_text='List of input file paths')
    
    # Notification
    notify_on_complete = models.BooleanField(default=True)
    notification_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['task_type', 'status']),
            models.Index(fields=['celery_task_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    def update_progress(self, progress: int, message: str = ''):
        """Update task progress"""
        self.progress = min(progress, 100)
        if message:
            self.progress_message = message
        if progress > 0 and self.status == TaskStatus.PENDING:
            self.status = TaskStatus.PROGRESS
        self.save(update_fields=['progress', 'progress_message', 'status'])
    
    def mark_started(self):
        """Mark task as started"""
        from django.utils import timezone
        self.status = TaskStatus.STARTED
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_success(self, result: dict = None):
        """Mark task as successful"""
        from django.utils import timezone
        self.status = TaskStatus.SUCCESS
        self.progress = 100
        self.completed_at = timezone.now()
        if result:
            self.result = result
        self.save(update_fields=['status', 'progress', 'completed_at', 'result'])
    
    def mark_failure(self, error: str, traceback: str = ''):
        """Mark task as failed"""
        from django.utils import timezone
        self.status = TaskStatus.FAILURE
        self.completed_at = timezone.now()
        self.error_message = error
        self.error_traceback = traceback
        self.save(update_fields=['status', 'completed_at', 'error_message', 'error_traceback'])
    
    def mark_revoked(self):
        """Mark task as cancelled"""
        from django.utils import timezone
        self.status = TaskStatus.REVOKED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    @property
    def duration_seconds(self) -> int:
        """Get task duration in seconds"""
        if not self.started_at:
            return 0
        from django.utils import timezone
        end_time = self.completed_at or timezone.now()
        return int((end_time - self.started_at).total_seconds())
    
    @property
    def is_complete(self) -> bool:
        """Check if task is complete (success or failure)"""
        return self.status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]
    
    @property
    def is_running(self) -> bool:
        """Check if task is currently running"""
        return self.status in [TaskStatus.STARTED, TaskStatus.PROGRESS]


class TaskWebhook(BaseModel):
    """
    Webhook configuration for task completion notifications.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_webhooks'
    )
    
    name = models.CharField(max_length=255)
    url = models.URLField()
    task_types = models.JSONField(
        default=list,
        help_text='List of task types to trigger webhook (empty = all)'
    )
    
    # Auth
    secret_key = models.CharField(max_length=255, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    failure_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.url})"
