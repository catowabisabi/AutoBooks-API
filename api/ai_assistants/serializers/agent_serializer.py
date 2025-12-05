"""
AI Agent Serializers
====================
Serializers for AI Agent models
"""

from rest_framework import serializers
from ai_assistants.models import (
    AIAgent,
    AIActionLog,
    AIConversation,
    AIActionType,
    AIActionStatus,
)


class AIAgentSerializer(serializers.ModelSerializer):
    """Serializer for AI Agent"""
    
    class Meta:
        model = AIAgent
        fields = [
            'id',
            'name',
            'display_name',
            'description',
            'agent_type',
            'allowed_tools',
            'auto_execute',
            'max_auto_actions',
            'llm_provider',
            'llm_model',
            'temperature',
            'system_prompt',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AIAgentListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing agents"""
    
    class Meta:
        model = AIAgent
        fields = [
            'id',
            'name',
            'display_name',
            'description',
            'agent_type',
            'auto_execute',
        ]


class AIActionLogSerializer(serializers.ModelSerializer):
    """Serializer for AI Action Log"""
    
    agent_name = serializers.CharField(source='agent.display_name', read_only=True, allow_null=True)
    triggered_by_name = serializers.CharField(source='triggered_by.email', read_only=True, allow_null=True)
    can_rollback = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = AIActionLog
        fields = [
            'id',
            'agent',
            'agent_name',
            'triggered_by',
            'triggered_by_name',
            'session_id',
            'action_type',
            'status',
            'target_model',
            'target_id',
            'data_before',
            'data_after',
            'user_prompt',
            'ai_reasoning',
            'ai_confidence',
            'executed_at',
            'execution_duration_ms',
            'error_message',
            'rolled_back_at',
            'rolled_back_by',
            'rollback_reason',
            'can_rollback',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'agent_name', 
            'triggered_by_name', 'can_rollback'
        ]


class AIActionLogListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing action logs"""
    
    agent_name = serializers.CharField(source='agent.display_name', read_only=True, allow_null=True)
    can_rollback = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = AIActionLog
        fields = [
            'id',
            'agent_name',
            'session_id',
            'action_type',
            'status',
            'target_model',
            'target_id',
            'ai_confidence',
            'can_rollback',
            'error_message',
            'created_at',
            'executed_at',
        ]


class AIConversationSerializer(serializers.ModelSerializer):
    """Serializer for AI Conversation"""
    
    agent_name = serializers.CharField(source='agent.display_name', read_only=True, allow_null=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AIConversation
        fields = [
            'id',
            'session_id',
            'user',
            'user_email',
            'agent',
            'agent_name',
            'title',
            'messages',
            'context',
            'message_count',
            'total_actions',
            'successful_actions',
            'failed_actions',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'agent_name', 
            'user_email', 'message_count'
        ]
    
    def get_message_count(self, obj):
        return len(obj.messages) if obj.messages else 0


class AIConversationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing conversations"""
    
    agent_name = serializers.CharField(source='agent.display_name', read_only=True, allow_null=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AIConversation
        fields = [
            'id',
            'session_id',
            'agent_name',
            'title',
            'message_count',
            'total_actions',
            'successful_actions',
            'failed_actions',
            'created_at',
            'updated_at',
        ]
    
    def get_message_count(self, obj):
        return len(obj.messages) if obj.messages else 0


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat request"""
    
    message = serializers.CharField(required=True, help_text='User message')
    session_id = serializers.CharField(required=False, allow_blank=True, help_text='Optional session ID')
    agent_id = serializers.UUIDField(required=False, allow_null=True, help_text='Optional agent UUID')
    auto_execute = serializers.BooleanField(default=True, help_text='Auto-execute tool calls')


class RollbackRequestSerializer(serializers.Serializer):
    """Serializer for rollback request"""
    
    reason = serializers.CharField(required=False, allow_blank=True, help_text='Reason for rollback')


class ToolParameterSerializer(serializers.Serializer):
    """Serializer for tool parameter"""
    
    name = serializers.CharField()
    type = serializers.CharField()
    description = serializers.CharField()
    required = serializers.BooleanField()
    enum = serializers.ListField(child=serializers.CharField(), required=False, allow_null=True)


class ToolDefinitionSerializer(serializers.Serializer):
    """Serializer for tool definition"""
    
    name = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    target_model = serializers.CharField()
    parameters = ToolParameterSerializer(many=True)
