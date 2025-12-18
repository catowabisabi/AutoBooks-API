"""
Notification Serializers
========================
Serializers for notification API endpoints.
"""
from rest_framework import serializers
from core.models_notifications import (
    Notification, NotificationPreference, NotificationLog,
    NotificationType, NotificationCategory, NotificationPriority
)


class NotificationSerializer(serializers.ModelSerializer):
    """Full notification serializer"""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'category',
            'priority', 'is_read', 'read_at', 'action_url', 'action_label',
            'related_object_type', 'related_object_id', 'metadata',
            'expires_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class NotificationListSerializer(serializers.ModelSerializer):
    """Compact notification serializer for lists"""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'category',
            'priority', 'is_read', 'action_url', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications"""
    user_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Notification
        fields = [
            'user_id', 'title', 'message', 'notification_type', 'category',
            'priority', 'action_url', 'action_label',
            'related_object_type', 'related_object_id', 'metadata', 'expires_at'
        ]
    
    def create(self, validated_data):
        user_id = validated_data.pop('user_id', None)
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            validated_data['user'] = User.objects.get(id=user_id)
        else:
            validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'push_enabled', 'sms_enabled', 'in_app_enabled',
            'category_preferences', 'quiet_hours_enabled',
            'quiet_hours_start', 'quiet_hours_end',
            'email_digest', 'digest_frequency'
        ]


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for notification delivery logs"""
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'channel', 'status', 'recipient', 'subject',
            'content', 'sent_at', 'delivered_at', 'error_message',
            'external_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MarkNotificationsReadSerializer(serializers.Serializer):
    """Serializer for marking multiple notifications as read"""
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of notification IDs to mark as read. If empty, marks all as read."
    )


class SendNotificationSerializer(serializers.Serializer):
    """Serializer for sending notifications via specific channels"""
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text="List of user IDs to send notification to"
    )
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    notification_type = serializers.ChoiceField(
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    category = serializers.ChoiceField(
        choices=NotificationCategory.choices,
        default=NotificationCategory.SYSTEM
    )
    priority = serializers.ChoiceField(
        choices=NotificationPriority.choices,
        default=NotificationPriority.NORMAL
    )
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=['EMAIL', 'PUSH', 'SMS', 'IN_APP']),
        default=['IN_APP'],
        help_text="Channels to send notification through"
    )
    action_url = serializers.URLField(required=False, allow_blank=True)
    action_label = serializers.CharField(max_length=100, required=False, allow_blank=True)


class NotificationCountSerializer(serializers.Serializer):
    """Serializer for notification counts"""
    total = serializers.IntegerField()
    unread = serializers.IntegerField()
    by_category = serializers.DictField(child=serializers.IntegerField())
    by_type = serializers.DictField(child=serializers.IntegerField())
