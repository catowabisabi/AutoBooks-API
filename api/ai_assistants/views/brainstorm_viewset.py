"""
Brainstorming Assistant ViewSets
AI-powered idea generation, campaign breakdown, pitch writing
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from django.db.models import Q
import logging

from ai_assistants.models import BrainstormSession, BrainstormIdea
from ai_assistants.serializers.brainstorm_serializer import (
    BrainstormSessionSerializer, BrainstormSessionListSerializer, BrainstormSessionCreateSerializer,
    BrainstormIdeaSerializer, BrainstormIdeaCreateSerializer,
    BrainstormGenerateSerializer, CampaignBreakdownSerializer,
    PitchWriterSerializer, MarketAnalysisSerializer
)

logger = logging.getLogger(__name__)


def get_permission_classes():
    """Return permission classes based on DEBUG setting"""
    if settings.DEBUG:
        return [AllowAny()]
    return [IsAuthenticated()]


class BrainstormSessionViewSet(viewsets.ModelViewSet):
    """
    Brainstorming Session management
    """
    queryset = BrainstormSession.objects.all()
    serializer_class = BrainstormSessionSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = BrainstormSession.objects.filter(is_active=True)
        
        # Filter by session type
        session_type = self.request.query_params.get('session_type')
        if session_type:
            queryset = queryset.filter(session_type=session_type)
        
        # Filter by campaign
        campaign_id = self.request.query_params.get('campaign_id')
        if campaign_id:
            queryset = queryset.filter(related_campaign_id=campaign_id)
        
        # Filter by client
        client_id = self.request.query_params.get('client_id')
        if client_id:
            queryset = queryset.filter(related_client_id=client_id)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(prompt__icontains=search) |
                Q(ai_response__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BrainstormSessionListSerializer
        if self.action == 'create':
            return BrainstormSessionCreateSerializer
        return BrainstormSessionSerializer
    
    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        AI-powered brainstorming idea generator
        """
        serializer = BrainstormGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = request.user if request.user.is_authenticated else None
        
        # Create session
        session = BrainstormSession.objects.create(
            title=f"Brainstorm: {data['prompt'][:50]}",
            session_type=data['session_type'],
            prompt=data['prompt'],
            context=data.get('context', {}),
            created_by=user,
            related_campaign_id=data.get('campaign_id'),
            related_client_id=data.get('client_id')
        )
        
        # TODO: Integrate with AI service (GPT)
        # For now, generate mock ideas
        num_ideas = data.get('num_ideas', 5)
        creativity = data.get('creativity_level', 'medium')
        
        mock_ideas = []
        idea_templates = {
            'IDEA_GENERATOR': [
                "Create a social media campaign featuring customer testimonials",
                "Develop an interactive landing page with gamification elements",
                "Launch an email marketing series with personalized content",
                "Partner with industry influencers for product endorsement",
                "Host a virtual event or webinar for customer engagement",
            ],
            'CAMPAIGN_BREAKDOWN': [
                "Phase 1: Pre-launch awareness building",
                "Phase 2: Launch day activities and press coverage",
                "Phase 3: Sustained engagement and community building",
                "Key KPIs: Reach, engagement, conversion rate",
                "Budget allocation: 40% digital, 30% PR, 30% events",
            ],
            'PITCH_WRITER': [
                "Opening hook: Address the key pain point",
                "Value proposition: Unique selling points",
                "Social proof: Success stories and metrics",
                "Call to action: Clear next steps",
                "Closing: Create urgency and FOMO",
            ],
            'MARKET_ANALYSIS': [
                "Market size and growth trajectory",
                "Key competitors and market share",
                "Target audience segments and behaviors",
                "Industry trends and disruptions",
                "Regulatory landscape and compliance",
            ],
            'STRATEGY': [
                "Short-term goals (Q1): Foundation building",
                "Medium-term goals (Q2-Q3): Growth acceleration",
                "Long-term goals (Q4+): Market leadership",
                "Resource requirements and allocation",
                "Risk mitigation strategies",
            ],
            'GENERAL': [
                "Innovative approach to solve the problem",
                "Data-driven insights for decision making",
                "Stakeholder alignment and communication",
                "Iterative improvement through feedback",
                "Measurement framework for success",
            ]
        }
        
        templates = idea_templates.get(data['session_type'], idea_templates['GENERAL'])
        
        for i in range(min(num_ideas, len(templates))):
            idea = BrainstormIdea.objects.create(
                session=session,
                content=f"{templates[i]} - based on: {data['prompt'][:30]}",
                category=data['session_type']
            )
            mock_ideas.append(BrainstormIdeaSerializer(idea).data)
        
        # Generate AI response
        session.ai_response = f"Generated {len(mock_ideas)} ideas for your {data['session_type']} session about '{data['prompt'][:50]}'.\n\nCreativity level: {creativity}"
        session.ai_structured_output = {
            'ideas_count': len(mock_ideas),
            'session_type': data['session_type'],
            'creativity_level': creativity
        }
        session.save()
        
        return Response({
            'session': BrainstormSessionSerializer(session).data,
            'ideas': mock_ideas
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def campaign_breakdown(self, request):
        """
        AI campaign breakdown analysis
        """
        serializer = CampaignBreakdownSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = request.user if request.user.is_authenticated else None
        
        # Create session
        session = BrainstormSession.objects.create(
            title=f"Campaign Breakdown: {data['campaign_name']}",
            session_type='CAMPAIGN_BREAKDOWN',
            prompt=f"{data['campaign_type']} campaign for {data['campaign_name']}",
            context=data,
            created_by=user
        )
        
        # TODO: Integrate with AI service
        # Mock breakdown
        breakdown = {
            'campaign_name': data['campaign_name'],
            'campaign_type': data['campaign_type'],
            'phases': [
                {
                    'name': 'Pre-Launch',
                    'duration': '2 weeks',
                    'activities': ['Teaser content', 'Media outreach', 'Influencer engagement'],
                    'budget_percent': 20
                },
                {
                    'name': 'Launch',
                    'duration': '1 week',
                    'activities': ['Press release', 'Event', 'Social media blitz'],
                    'budget_percent': 50
                },
                {
                    'name': 'Post-Launch',
                    'duration': '3 weeks',
                    'activities': ['Follow-up coverage', 'Community engagement', 'Performance analysis'],
                    'budget_percent': 30
                }
            ],
            'key_messages': [
                f"Introducing {data['campaign_name']} - Revolutionary solution",
                "Industry-leading innovation",
                "Trusted by market leaders"
            ],
            'target_channels': ['LinkedIn', 'Industry publications', 'Email', 'Events'],
            'success_metrics': ['Media impressions', 'Lead generation', 'Brand awareness lift']
        }
        
        session.ai_response = f"Campaign breakdown for {data['campaign_name']} completed."
        session.ai_structured_output = breakdown
        session.save()
        
        return Response({
            'session_id': session.id,
            'breakdown': breakdown
        })
    
    @action(detail=False, methods=['post'])
    def write_pitch(self, request):
        """
        AI pitch writer
        """
        serializer = PitchWriterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = request.user if request.user.is_authenticated else None
        
        # Create session
        session = BrainstormSession.objects.create(
            title=f"Pitch: {data['topic']}",
            session_type='PITCH_WRITER',
            prompt=f"{data['pitch_type']} pitch for {data['topic']}",
            context=data,
            created_by=user
        )
        
        # TODO: Integrate with AI service
        # Mock pitch
        key_points_text = '\n'.join(f"• {point}" for point in data['key_points'])
        
        pitch_templates = {
            'elevator': f"""
{data['topic']} - The Game Changer

In today's fast-paced market, businesses struggle with [common pain point]. 
{data['topic']} solves this by providing [unique solution].

Key benefits:
{key_points_text}

We're already trusted by [number] clients achieving [metric] results.
Let's connect to discuss how we can help you too.
            """,
            'investor': f"""
Executive Summary: {data['topic']}

Market Opportunity:
The market for [industry] is valued at $X billion and growing at Y% annually.

Our Solution:
{data['topic']} addresses this opportunity by:
{key_points_text}

Traction:
• [X] paying customers
• [Y]% month-over-month growth
• $[Z] ARR

Ask: We're seeking $[X]M to accelerate growth and expand our team.
            """,
            'sales': f"""
Dear [Prospect],

I noticed [personalized observation about their business].

Many companies like yours face [pain point]. 
{data['topic']} has helped similar organizations achieve:
{key_points_text}

Would you be open to a 15-minute call to explore if we could help?

Best regards
            """,
            'press': f"""
FOR IMMEDIATE RELEASE

{data['topic'].upper()}: [Headline that captures the news]

[City, Date] - [Company] today announced {data['topic']}, a groundbreaking [description].

Key highlights:
{key_points_text}

"[Quote from executive about the announcement]," said [Name], [Title].

For more information, visit [website] or contact [media contact].

###
            """
        }
        
        pitch = pitch_templates.get(data['pitch_type'], pitch_templates['elevator'])
        
        session.ai_response = pitch.strip()
        session.ai_structured_output = {
            'pitch_type': data['pitch_type'],
            'topic': data['topic'],
            'tone': data['tone'],
            'word_count': len(pitch.split())
        }
        session.save()
        
        return Response({
            'session_id': session.id,
            'pitch': pitch.strip(),
            'word_count': len(pitch.split())
        })
    
    @action(detail=False, methods=['post'])
    def market_analysis(self, request):
        """
        AI market analysis
        """
        serializer = MarketAnalysisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user = request.user if request.user.is_authenticated else None
        
        # Create session
        session = BrainstormSession.objects.create(
            title=f"Market Analysis: {data['industry']}",
            session_type='MARKET_ANALYSIS',
            prompt=f"{data['analysis_type']} analysis for {data['industry']} in {data['region']}",
            context=data,
            created_by=user
        )
        
        # TODO: Integrate with AI service
        # Mock analysis
        analysis = {
            'industry': data['industry'],
            'region': data['region'],
            'analysis_type': data['analysis_type'],
            'key_findings': [
                f"The {data['industry']} market in {data['region']} is growing at X% CAGR",
                "Digital transformation is a key driver",
                "Top 3 players control 60% market share",
                "Emerging opportunities in niche segments"
            ],
            'opportunities': [
                "Untapped SME segment",
                "Cross-border expansion",
                "Technology integration"
            ],
            'threats': [
                "Regulatory changes",
                "New market entrants",
                "Economic uncertainty"
            ],
            'recommendations': [
                "Focus on differentiation",
                "Invest in technology",
                "Build strategic partnerships"
            ]
        }
        
        session.ai_response = f"Market analysis for {data['industry']} in {data['region']} completed."
        session.ai_structured_output = analysis
        session.save()
        
        return Response({
            'session_id': session.id,
            'analysis': analysis
        })
    
    @action(detail=True, methods=['post'])
    def save_idea(self, request, pk=None):
        """
        Save an idea to the session
        """
        session = self.get_object()
        content = request.data.get('content')
        
        if not content:
            return Response(
                {'error': 'Content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        idea = BrainstormIdea.objects.create(
            session=session,
            content=content,
            category=request.data.get('category', ''),
            is_selected=True
        )
        
        return Response(
            BrainstormIdeaSerializer(idea).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get brainstorm statistics"""
        queryset = self.get_queryset()
        return Response({
            'total_sessions': queryset.count(),
            'by_type': {
                session_type: queryset.filter(session_type=session_type).count()
                for session_type, _ in [
                    ('IDEA_GENERATOR', 'Idea Generator'),
                    ('CAMPAIGN_BREAKDOWN', 'Campaign Breakdown'),
                    ('MARKET_ANALYSIS', 'Market Analysis'),
                    ('PITCH_WRITER', 'Pitch Writer'),
                    ('STRATEGY', 'Strategy Planning'),
                    ('GENERAL', 'General Brainstorm'),
                ]
            },
            'total_ideas': BrainstormIdea.objects.filter(session__in=queryset).count()
        })


class BrainstormIdeaViewSet(viewsets.ModelViewSet):
    """
    Individual brainstorm ideas
    """
    queryset = BrainstormIdea.objects.all()
    serializer_class = BrainstormIdeaSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = BrainstormIdea.objects.filter(is_active=True)
        
        # Filter by session
        session_id = self.request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        # Filter by selected
        is_selected = self.request.query_params.get('is_selected')
        if is_selected is not None:
            queryset = queryset.filter(is_selected=is_selected.lower() == 'true')
        
        return queryset.order_by('-rating', '-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BrainstormIdeaCreateSerializer
        return BrainstormIdeaSerializer
    
    @action(detail=True, methods=['post'])
    def select(self, request, pk=None):
        """Mark idea as selected"""
        idea = self.get_object()
        idea.is_selected = True
        idea.save()
        return Response({'status': 'selected'})
    
    @action(detail=True, methods=['post'])
    def deselect(self, request, pk=None):
        """Mark idea as not selected"""
        idea = self.get_object()
        idea.is_selected = False
        idea.save()
        return Response({'status': 'deselected'})
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """Rate an idea"""
        idea = self.get_object()
        rating = request.data.get('rating')
        
        if rating is None or not (1 <= int(rating) <= 5):
            return Response(
                {'error': 'Rating must be between 1 and 5'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        idea.rating = int(rating)
        idea.save()
        return Response({'rating': idea.rating})
