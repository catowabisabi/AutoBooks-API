"""
Planner AI Serializers
"""
from rest_framework import serializers
from ai_assistants.models import (
    PlannerTask, ScheduleEvent,
    TaskPriority, TaskStatus
)


class PlannerQuerySerializer(serializers.Serializer):
    """Query for planner AI"""
    query = serializers.CharField()


class PlannerTaskSerializer(serializers.ModelSerializer):
    """Full planner task serializer"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = PlannerTask
        fields = [
            'id', 'title', 'description',
            'assigned_to', 'assigned_to_name', 'created_by',
            'status', 'status_display', 'priority', 'priority_display',
            'due_date', 'due_time', 'reminder_at', 'completed_at',
            'ai_generated', 'ai_priority_score', 'ai_suggested_deadline', 'ai_reasoning',
            'source_type', 'source_id',
            'related_project', 'related_client', 'related_email',
            'tags',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'ai_priority_score', 'ai_suggested_deadline', 'ai_reasoning'
        ]


class PlannerTaskListSerializer(serializers.ModelSerializer):
    """Lightweight task list serializer"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = PlannerTask
        fields = [
            'id', 'title', 'status', 'status_display',
            'priority', 'priority_display',
            'due_date', 'due_time',
            'assigned_to_name',
            'ai_generated', 'ai_priority_score',
            'tags'
        ]


class PlannerTaskCreateSerializer(serializers.ModelSerializer):
    """Create a new task"""
    
    class Meta:
        model = PlannerTask
        fields = [
            'title', 'description',
            'assigned_to', 'status', 'priority',
            'due_date', 'due_time', 'reminder_at',
            'related_project', 'related_client',
            'tags'
        ]


class ScheduleEventSerializer(serializers.ModelSerializer):
    """Calendar event serializer"""
    organizer_name = serializers.CharField(source='organizer.get_full_name', read_only=True)
    attendee_names = serializers.SerializerMethodField()
    
    class Meta:
        model = ScheduleEvent
        fields = [
            'id', 'title', 'description', 'location',
            'organizer', 'organizer_name', 'attendees', 'attendee_names',
            'start_time', 'end_time', 'is_all_day', 'timezone',
            'is_recurring', 'recurrence_rule',
            'meeting_link', 'meeting_type',
            'ai_generated', 'source_email',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_attendee_names(self, obj):
        return [u.get_full_name() for u in obj.attendees.all()]


class ScheduleEventCreateSerializer(serializers.ModelSerializer):
    """Create a calendar event"""
    
    class Meta:
        model = ScheduleEvent
        fields = [
            'title', 'description', 'location',
            'attendees',
            'start_time', 'end_time', 'is_all_day', 'timezone',
            'is_recurring', 'recurrence_rule',
            'meeting_link', 'meeting_type'
        ]


class PlannerAICreateTaskSerializer(serializers.Serializer):
    """Request AI to create tasks from input"""
    input_text = serializers.CharField(help_text='Free-form input describing tasks')
    source_email_id = serializers.UUIDField(required=False)
    auto_prioritize = serializers.BooleanField(default=True)
    auto_schedule = serializers.BooleanField(default=True)


class PlannerAIReprioritizeSerializer(serializers.Serializer):
    """Request AI to reprioritize all tasks"""
    consider_deadlines = serializers.BooleanField(default=True)
    consider_dependencies = serializers.BooleanField(default=True)
