# api/ai_assistants/serializers/brainstorm_serializer.py
"""
Brainstorming Assistant Serializers
"""
from rest_framework import serializers
from ai_assistants.models import (
    BrainstormSession, BrainstormIdea,
    BrainstormMeeting, BrainstormMeetingParticipant,
    MeetingStatus, MeetingParticipantRole, MeetingParticipantStatus
)


class BrainstormSessionSerializer(serializers.ModelSerializer):
    """Full brainstorm session serializer"""
    ideas = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = BrainstormSession
        fields = [
            'id', 'title', 'session_type',
            'prompt', 'context',
            'ai_response', 'ai_structured_output',
            'saved_ideas', 'ideas',
            'created_by', 'created_by_name',
            'related_campaign', 'related_client',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'ai_response', 'ai_structured_output'
        ]
    
    def get_ideas(self, obj):
        return BrainstormIdeaSerializer(obj.ideas.all(), many=True).data


class BrainstormSessionListSerializer(serializers.ModelSerializer):
    """Lightweight session list serializer"""
    ideas_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BrainstormSession
        fields = [
            'id', 'title', 'session_type',
            'prompt', 'ideas_count',
            'created_at'
        ]
    
    def get_ideas_count(self, obj):
        return obj.ideas.count()


class BrainstormSessionCreateSerializer(serializers.ModelSerializer):
    """Create a new brainstorm session"""
    
    class Meta:
        model = BrainstormSession
        fields = [
            'title', 'session_type',
            'prompt', 'context',
            'related_campaign', 'related_client'
        ]


class BrainstormIdeaSerializer(serializers.ModelSerializer):
    """Brainstorm idea serializer"""
    
    class Meta:
        model = BrainstormIdea
        fields = [
            'id', 'session', 'content', 'category',
            'is_selected', 'rating', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BrainstormIdeaCreateSerializer(serializers.ModelSerializer):
    """Create an idea"""
    
    class Meta:
        model = BrainstormIdea
        fields = ['session', 'content', 'category', 'rating', 'notes']


class BrainstormGenerateSerializer(serializers.Serializer):
    """Request AI to generate brainstorming ideas"""
    session_type = serializers.ChoiceField(
        choices=[
            ('IDEA_GENERATOR', 'Idea Generator'),
            ('CAMPAIGN_BREAKDOWN', 'Campaign Breakdown'),
            ('MARKET_ANALYSIS', 'Market Analysis'),
            ('PITCH_WRITER', 'Pitch Writer'),
            ('STRATEGY', 'Strategy Planning'),
            ('GENERAL', 'General Brainstorm'),
        ]
    )
    prompt = serializers.CharField(help_text='Your question or topic')
    context = serializers.JSONField(required=False, default=dict)
    
    # Optional links
    campaign_id = serializers.UUIDField(required=False)
    client_id = serializers.UUIDField(required=False)
    
    # Generation parameters
    num_ideas = serializers.IntegerField(default=5, min_value=1, max_value=20)
    creativity_level = serializers.ChoiceField(
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        default='medium'
    )


class CampaignBreakdownSerializer(serializers.Serializer):
    """Request campaign breakdown analysis"""
    campaign_name = serializers.CharField()
    campaign_type = serializers.ChoiceField(
        choices=[('BMI', 'BMI'), ('IPO', 'IPO'), ('PR', 'PR')]
    )
    target_audience = serializers.CharField(required=False)
    budget = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    timeline_days = serializers.IntegerField(required=False)
    goals = serializers.ListField(child=serializers.CharField(), required=False)


class PitchWriterSerializer(serializers.Serializer):
    """Request AI to write a pitch"""
    topic = serializers.CharField()
    pitch_type = serializers.ChoiceField(
        choices=[
            ('elevator', 'Elevator Pitch'),
            ('investor', 'Investor Pitch'),
            ('sales', 'Sales Pitch'),
            ('press', 'Press Release'),
        ]
    )
    key_points = serializers.ListField(child=serializers.CharField())
    tone = serializers.ChoiceField(
        choices=[
            ('professional', 'Professional'),
            ('casual', 'Casual'),
            ('enthusiastic', 'Enthusiastic'),
            ('formal', 'Formal'),
        ],
        default='professional'
    )
    max_words = serializers.IntegerField(default=300, min_value=50, max_value=2000)


class MarketAnalysisSerializer(serializers.Serializer):
    """Request market analysis"""
    industry = serializers.CharField()
    region = serializers.ChoiceField(
        choices=[
            ('HK', 'Hong Kong'),
            ('CN', 'China'),
            ('APAC', 'Asia Pacific'),
            ('GLOBAL', 'Global'),
        ],
        default='HK'
    )
    analysis_type = serializers.ChoiceField(
        choices=[
            ('competitor', 'Competitor Analysis'),
            ('trend', 'Trend Analysis'),
            ('swot', 'SWOT Analysis'),
            ('opportunity', 'Opportunity Analysis'),
        ]
    )
    specific_questions = serializers.ListField(child=serializers.CharField(), required=False)


# =================================================================
# Brainstorming Meeting Serializers
# =================================================================

class BrainstormMeetingParticipantSerializer(serializers.ModelSerializer):
    """Full participant serializer"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_avatar = serializers.CharField(source='user.avatar_url', read_only=True)
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BrainstormMeetingParticipant
        fields = [
            'id', 'meeting', 'user', 'user_name', 'user_email', 'user_avatar',
            'role', 'status', 'responded_at', 'response_notes',
            'joined_at', 'left_at', 'ideas_contributed', 'votes_cast', 'notes',
            'is_external', 'external_name', 'external_email', 'external_company',
            'display_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_display_name(self, obj):
        if obj.is_external:
            return obj.external_name
        return obj.user.full_name if obj.user else ''


class BrainstormMeetingParticipantCreateSerializer(serializers.ModelSerializer):
    """Create participant serializer"""
    class Meta:
        model = BrainstormMeetingParticipant
        fields = [
            'meeting', 'user', 'role', 'status',
            'is_external', 'external_name', 'external_email', 'external_company'
        ]


class BrainstormMeetingParticipantListSerializer(serializers.ModelSerializer):
    """Lightweight participant list serializer"""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BrainstormMeetingParticipant
        fields = ['id', 'user', 'user_name', 'display_name', 'role', 'status', 'is_external']
    
    def get_display_name(self, obj):
        if obj.is_external:
            return obj.external_name
        return obj.user.full_name if obj.user else ''


class BrainstormMeetingSerializer(serializers.ModelSerializer):
    """Full meeting serializer"""
    organizer_name = serializers.CharField(source='organizer.full_name', read_only=True)
    organizer_email = serializers.CharField(source='organizer.email', read_only=True)
    participants_list = serializers.SerializerMethodField()
    participant_count = serializers.IntegerField(read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = BrainstormMeeting
        fields = [
            'id', 'title', 'description', 'status',
            'scheduled_start', 'scheduled_end', 'actual_start', 'actual_end',
            'location', 'meeting_link', 'meeting_type',
            'agenda', 'objectives', 'meeting_notes', 'summary',
            'action_items', 'decisions_made',
            'ideas_generated', 'selected_ideas',
            'organizer', 'organizer_name', 'organizer_email',
            'max_participants', 'participant_count', 'duration_minutes',
            'participants_list',
            'related_session', 'related_project', 'related_campaign', 'related_client',
            'tags', 'attachments',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'participant_count', 'duration_minutes', 'created_at', 'updated_at']
    
    def get_participants_list(self, obj):
        return BrainstormMeetingParticipantListSerializer(
            obj.participants.all(), many=True
        ).data


class BrainstormMeetingListSerializer(serializers.ModelSerializer):
    """Lightweight meeting list serializer"""
    organizer_name = serializers.CharField(source='organizer.full_name', read_only=True)
    participant_count = serializers.IntegerField(read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = BrainstormMeeting
        fields = [
            'id', 'title', 'status', 'meeting_type',
            'scheduled_start', 'scheduled_end',
            'organizer', 'organizer_name',
            'participant_count', 'duration_minutes',
            'location', 'tags', 'created_at'
        ]


class BrainstormMeetingCreateSerializer(serializers.ModelSerializer):
    """Create meeting serializer"""
    participant_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        help_text='List of user UUIDs to invite as participants'
    )
    
    class Meta:
        model = BrainstormMeeting
        fields = [
            'title', 'description', 'status',
            'scheduled_start', 'scheduled_end',
            'location', 'meeting_link', 'meeting_type',
            'agenda', 'objectives', 'max_participants',
            'related_session', 'related_project', 'related_campaign', 'related_client',
            'tags', 'participant_user_ids'
        ]
    
    def create(self, validated_data):
        participant_user_ids = validated_data.pop('participant_user_ids', [])
        meeting = super().create(validated_data)
        
        # Add participants
        from users.models import User
        for user_id in participant_user_ids:
            try:
                user = User.objects.get(id=user_id)
                BrainstormMeetingParticipant.objects.create(
                    meeting=meeting,
                    user=user,
                    role=MeetingParticipantRole.PARTICIPANT,
                    status=MeetingParticipantStatus.INVITED
                )
            except User.DoesNotExist:
                pass
        
        return meeting


class BrainstormMeetingUpdateSerializer(serializers.ModelSerializer):
    """Update meeting serializer"""
    class Meta:
        model = BrainstormMeeting
        fields = [
            'title', 'description', 'status',
            'scheduled_start', 'scheduled_end', 'actual_start', 'actual_end',
            'location', 'meeting_link', 'meeting_type',
            'agenda', 'objectives', 'meeting_notes', 'summary',
            'action_items', 'decisions_made',
            'ideas_generated', 'selected_ideas',
            'max_participants', 'tags', 'attachments'
        ]


class AddParticipantSerializer(serializers.Serializer):
    """Add participant to meeting"""
    user_id = serializers.UUIDField(required=False)
    role = serializers.ChoiceField(
        choices=MeetingParticipantRole.choices,
        default=MeetingParticipantRole.PARTICIPANT
    )
    # For external participants
    is_external = serializers.BooleanField(default=False)
    external_name = serializers.CharField(required=False, allow_blank=True)
    external_email = serializers.EmailField(required=False, allow_blank=True)
    external_company = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if not data.get('is_external') and not data.get('user_id'):
            raise serializers.ValidationError("user_id is required for internal participants")
        if data.get('is_external') and not data.get('external_name'):
            raise serializers.ValidationError("external_name is required for external participants")
        return data


class UpdateParticipantStatusSerializer(serializers.Serializer):
    """Update participant status (RSVP)"""
    status = serializers.ChoiceField(choices=MeetingParticipantStatus.choices)
    response_notes = serializers.CharField(required=False, allow_blank=True)
