"""
Notification Models
==================
Models for the notification system including in-app, email, and push notifications.
"""
import uuid
from django.db import models
from django.conf import settings
from core.models import BaseModel


class NotificationType(models.TextChoices):
    """Types of notifications"""
    INFO = 'INFO', 'Information'
    SUCCESS = 'SUCCESS', 'Success'
    WARNING = 'WARNING', 'Warning'
    ERROR = 'ERROR', 'Error'
    REMINDER = 'REMINDER', 'Reminder'
    APPROVAL = 'APPROVAL', 'Approval Request'
    PAYMENT = 'PAYMENT', 'Payment'
    DEADLINE = 'DEADLINE', 'Deadline'


class NotificationCategory(models.TextChoices):
    """Categories for notifications"""
    SYSTEM = 'SYSTEM', 'System'
    ACCOUNTING = 'ACCOUNTING', 'Accounting'
    INVOICES = 'INVOICES', 'Invoices'
    EXPENSES = 'EXPENSES', 'Expenses'
    PROJECTS = 'PROJECTS', 'Projects'
    TASKS = 'TASKS', 'Tasks'
    HRMS = 'HRMS', 'HR Management'
    AI = 'AI', 'AI Assistant'


class NotificationPriority(models.TextChoices):
    """Priority levels for notifications"""
    LOW = 'LOW', 'Low'
    NORMAL = 'NORMAL', 'Normal'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'


class Notification(BaseModel):
    """
    In-app notification model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Recipient
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Content
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    category = models.CharField(
        max_length=20,
        choices=NotificationCategory.choices,
        default=NotificationCategory.SYSTEM
    )
    priority = models.CharField(
        max_length=20,
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Optional action link
    action_url = models.URLField(max_length=500, null=True, blank=True)
    action_label = models.CharField(max_length=100, null=True, blank=True)
    
    # Related object (generic reference)
    related_object_type = models.CharField(max_length=100, null=True, blank=True)
    related_object_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(BaseModel):
    """
    User notification preferences
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Channel preferences
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    
    # Category preferences (JSON: category -> enabled)
    category_preferences = models.JSONField(default=dict, blank=True)
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)  # e.g., 22:00
    quiet_hours_end = models.TimeField(null=True, blank=True)    # e.g., 08:00
    
    # Digest preferences
    email_digest = models.BooleanField(default=False)  # Send daily digest instead of immediate
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
        ],
        default='DAILY'
    )
    
    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Notification preferences for {self.user.email}"


class NotificationLog(BaseModel):
    """
    Log of sent notifications (email, push, SMS)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='delivery_logs',
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_logs'
    )
    
    # Delivery channel
    channel = models.CharField(
        max_length=20,
        choices=[
            ('EMAIL', 'Email'),
            ('PUSH', 'Push'),
            ('SMS', 'SMS'),
            ('IN_APP', 'In-App'),
        ]
    )
    
    # Delivery status
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('SENT', 'Sent'),
            ('DELIVERED', 'Delivered'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING'
    )
    
    # Details
    recipient = models.CharField(max_length=255)  # Email address, phone, device token
    subject = models.CharField(max_length=255, null=True, blank=True)
    content = models.TextField()
    
    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    # External reference (e.g., email service message ID)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'channel']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.channel} to {self.recipient} - {self.status}"
