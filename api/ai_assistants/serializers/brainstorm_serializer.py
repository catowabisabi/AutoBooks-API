# api/ai_assistants/serializers/brainstorm_serializer.py
"""
Brainstorming Assistant Serializers
"""
from rest_framework import serializers
from ai_assistants.models import BrainstormSession, BrainstormIdea


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
