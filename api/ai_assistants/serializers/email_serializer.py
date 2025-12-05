"""
Email Assistant Serializers
"""
from rest_framework import serializers
from ai_assistants.models import (
    EmailAccount, Email, EmailAttachment, EmailTemplate,
    EmailStatus, EmailCategory, EmailPriority
)


class EmailAccountSerializer(serializers.ModelSerializer):
    """Email account configuration serializer"""
    
    class Meta:
        model = EmailAccount
        fields = [
            'id', 'email_address', 'display_name',
            'smtp_host', 'smtp_port', 'smtp_user', 'use_tls',
            'imap_host', 'imap_port',
            'is_demo', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'smtp_password': {'write_only': True}
        }


class EmailAccountCreateSerializer(serializers.ModelSerializer):
    """Create email account with password"""
    
    class Meta:
        model = EmailAccount
        fields = [
            'email_address', 'display_name',
            'smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'use_tls',
            'imap_host', 'imap_port',
            'is_demo'
        ]


class EmailAttachmentSerializer(serializers.ModelSerializer):
    """Email attachment serializer"""
    
    class Meta:
        model = EmailAttachment
        fields = ['id', 'filename', 'file', 'content_type', 'size', 'created_at']
        read_only_fields = ['id', 'created_at']


class EmailSerializer(serializers.ModelSerializer):
    """Email message serializer"""
    attachments = EmailAttachmentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Email
        fields = [
            'id', 'account',
            'from_address', 'from_name', 'to_addresses', 'cc_addresses', 'bcc_addresses', 'reply_to',
            'subject', 'body_text', 'body_html',
            'status', 'status_display', 'category', 'category_display', 'priority', 'priority_display',
            'thread_id', 'in_reply_to',
            'sent_at', 'received_at', 'read_at',
            'is_read', 'is_starred', 'is_spam', 'has_attachments',
            'ai_summary', 'ai_sentiment', 'ai_action_items', 'ai_suggested_reply', 'ai_keywords',
            'related_project', 'related_client',
            'attachments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'ai_summary', 'ai_sentiment', 'ai_action_items', 'ai_suggested_reply', 'ai_keywords']


class EmailListSerializer(serializers.ModelSerializer):
    """Lightweight email list serializer"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Email
        fields = [
            'id', 'from_address', 'from_name', 'subject',
            'status', 'status_display', 'category', 'category_display', 'priority', 'priority_display',
            'received_at', 'sent_at',
            'is_read', 'is_starred', 'has_attachments',
            'ai_summary'
        ]


class EmailComposeSerializer(serializers.Serializer):
    """Serializer for composing/sending emails"""
    account_id = serializers.UUIDField(required=False)
    to_addresses = serializers.ListField(child=serializers.EmailField(), min_length=1)
    cc_addresses = serializers.ListField(child=serializers.EmailField(), required=False, default=list)
    bcc_addresses = serializers.ListField(child=serializers.EmailField(), required=False, default=list)
    subject = serializers.CharField(max_length=500)
    body_text = serializers.CharField(required=False, allow_blank=True)
    body_html = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=EmailPriority.choices, default=EmailPriority.NORMAL)
    reply_to_id = serializers.UUIDField(required=False)


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Email template serializer"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'category', 'category_display',
            'subject_template', 'body_template', 'variables',
            'is_shared', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailAIAnalyzeSerializer(serializers.Serializer):
    """Request to analyze an email with AI"""
    email_id = serializers.UUIDField()
    generate_reply = serializers.BooleanField(default=False)


class EmailAIReplySerializer(serializers.Serializer):
    """Request AI to generate email reply"""
    email_id = serializers.UUIDField()
    tone = serializers.ChoiceField(
        choices=[
            ('professional', 'Professional'),
            ('friendly', 'Friendly'),
            ('formal', 'Formal'),
            ('concise', 'Concise'),
        ],
        default='professional'
    )
    key_points = serializers.ListField(child=serializers.CharField(), required=False)
