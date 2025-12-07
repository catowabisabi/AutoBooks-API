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
from django.utils import timezone
import logging

from ai_assistants.models import (
    BrainstormSession, BrainstormIdea,
    BrainstormMeeting, BrainstormMeetingParticipant,
    MeetingStatus, MeetingParticipantRole, MeetingParticipantStatus
)
from ai_assistants.serializers.brainstorm_serializer import (
    BrainstormSessionSerializer, BrainstormSessionListSerializer, BrainstormSessionCreateSerializer,
    BrainstormIdeaSerializer, BrainstormIdeaCreateSerializer,
    BrainstormGenerateSerializer, CampaignBreakdownSerializer,
    PitchWriterSerializer, MarketAnalysisSerializer,
    # Meeting serializers
    BrainstormMeetingSerializer, BrainstormMeetingListSerializer,
    BrainstormMeetingCreateSerializer, BrainstormMeetingUpdateSerializer,
    BrainstormMeetingParticipantSerializer, BrainstormMeetingParticipantCreateSerializer,
    BrainstormMeetingParticipantListSerializer,
    AddParticipantSerializer, UpdateParticipantStatusSerializer
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


# =================================================================
# Brainstorming Meeting ViewSets
# =================================================================

class BrainstormMeetingViewSet(viewsets.ModelViewSet):
    """
    Brainstorming Meeting management
    管理腦力激盪會議
    """
    queryset = BrainstormMeeting.objects.all()
    serializer_class = BrainstormMeetingSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = BrainstormMeeting.objects.filter(is_active=True)
        
        # Filter by status
        meeting_status = self.request.query_params.get('status')
        if meeting_status:
            queryset = queryset.filter(status=meeting_status)
        
        # Filter by organizer
        organizer_id = self.request.query_params.get('organizer_id')
        if organizer_id:
            queryset = queryset.filter(organizer_id=organizer_id)
        
        # Filter by meeting type
        meeting_type = self.request.query_params.get('meeting_type')
        if meeting_type:
            queryset = queryset.filter(meeting_type=meeting_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(scheduled_start__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(scheduled_end__date__lte=end_date)
        
        # Filter by participant (meetings where user is a participant)
        participant_id = self.request.query_params.get('participant_id')
        if participant_id:
            queryset = queryset.filter(participants__user_id=participant_id)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(agenda__icontains=search)
            )
        
        # Filter upcoming meetings
        upcoming = self.request.query_params.get('upcoming')
        if upcoming and upcoming.lower() == 'true':
            queryset = queryset.filter(
                scheduled_start__gte=timezone.now(),
                status__in=[MeetingStatus.SCHEDULED, MeetingStatus.POSTPONED]
            )
        
        return queryset.order_by('-scheduled_start')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BrainstormMeetingListSerializer
        if self.action == 'create':
            return BrainstormMeetingCreateSerializer
        if self.action in ['update', 'partial_update']:
            return BrainstormMeetingUpdateSerializer
        return BrainstormMeetingSerializer
    
    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        meeting = serializer.save(organizer=user)
        
        # Add organizer as a participant with ORGANIZER role
        if user:
            BrainstormMeetingParticipant.objects.create(
                meeting=meeting,
                user=user,
                role=MeetingParticipantRole.ORGANIZER,
                status=MeetingParticipantStatus.ACCEPTED
            )
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start the meeting / 開始會議"""
        meeting = self.get_object()
        if meeting.status != MeetingStatus.SCHEDULED:
            return Response(
                {'error': 'Meeting can only be started from SCHEDULED status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        meeting.status = MeetingStatus.IN_PROGRESS
        meeting.actual_start = timezone.now()
        meeting.save()
        
        return Response(BrainstormMeetingSerializer(meeting).data)
    
    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        """End the meeting / 結束會議"""
        meeting = self.get_object()
        if meeting.status != MeetingStatus.IN_PROGRESS:
            return Response(
                {'error': 'Meeting can only be ended from IN_PROGRESS status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        meeting.status = MeetingStatus.COMPLETED
        meeting.actual_end = timezone.now()
        
        # Update summary if provided
        summary = request.data.get('summary')
        if summary:
            meeting.summary = summary
        
        meeting.save()
        
        # Mark all participants who joined as ATTENDED
        meeting.participants.filter(
            joined_at__isnull=False
        ).update(status=MeetingParticipantStatus.ATTENDED)
        
        return Response(BrainstormMeetingSerializer(meeting).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel the meeting / 取消會議"""
        meeting = self.get_object()
        if meeting.status in [MeetingStatus.COMPLETED, MeetingStatus.CANCELLED]:
            return Response(
                {'error': 'Cannot cancel a completed or already cancelled meeting'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        meeting.status = MeetingStatus.CANCELLED
        meeting.save()
        
        return Response(BrainstormMeetingSerializer(meeting).data)
    
    @action(detail=True, methods=['post'])
    def postpone(self, request, pk=None):
        """Postpone the meeting / 延期會議"""
        meeting = self.get_object()
        
        new_start = request.data.get('scheduled_start')
        new_end = request.data.get('scheduled_end')
        
        if not new_start or not new_end:
            return Response(
                {'error': 'New scheduled_start and scheduled_end are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        meeting.status = MeetingStatus.POSTPONED
        meeting.scheduled_start = new_start
        meeting.scheduled_end = new_end
        meeting.save()
        
        return Response(BrainstormMeetingSerializer(meeting).data)
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a participant to the meeting / 添加參與者"""
        meeting = self.get_object()
        serializer = AddParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        if data.get('is_external'):
            # Add external participant
            participant = BrainstormMeetingParticipant.objects.create(
                meeting=meeting,
                user=None,
                is_external=True,
                external_name=data.get('external_name'),
                external_email=data.get('external_email', ''),
                external_company=data.get('external_company', ''),
                role=data.get('role', MeetingParticipantRole.PARTICIPANT),
                status=MeetingParticipantStatus.INVITED
            )
        else:
            # Check if participant already exists
            from users.models import User
            try:
                user = User.objects.get(id=data['user_id'])
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if meeting.participants.filter(user=user).exists():
                return Response(
                    {'error': 'User is already a participant'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            participant = BrainstormMeetingParticipant.objects.create(
                meeting=meeting,
                user=user,
                role=data.get('role', MeetingParticipantRole.PARTICIPANT),
                status=MeetingParticipantStatus.INVITED
            )
        
        return Response(
            BrainstormMeetingParticipantSerializer(participant).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['delete'], url_path='remove_participant/(?P<participant_id>[^/.]+)')
    def remove_participant(self, request, pk=None, participant_id=None):
        """Remove a participant from the meeting / 移除參與者"""
        meeting = self.get_object()
        
        try:
            participant = meeting.participants.get(id=participant_id)
        except BrainstormMeetingParticipant.DoesNotExist:
            return Response(
                {'error': 'Participant not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Don't allow removing the organizer
        if participant.role == MeetingParticipantRole.ORGANIZER:
            return Response(
                {'error': 'Cannot remove the meeting organizer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Get all participants of the meeting / 獲取所有參與者"""
        meeting = self.get_object()
        participants = meeting.participants.all()
        return Response(
            BrainstormMeetingParticipantSerializer(participants, many=True).data
        )
    
    @action(detail=True, methods=['post'])
    def add_idea(self, request, pk=None):
        """Add an idea during the meeting / 在會議中添加想法"""
        meeting = self.get_object()
        
        idea_content = request.data.get('content')
        if not idea_content:
            return Response(
                {'error': 'Content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ideas = meeting.ideas_generated or []
        ideas.append({
            'content': idea_content,
            'author': request.user.full_name if request.user.is_authenticated else 'Anonymous',
            'created_at': timezone.now().isoformat(),
            'votes': 0
        })
        meeting.ideas_generated = ideas
        meeting.save()
        
        # Update participant's contribution count
        if request.user.is_authenticated:
            participant = meeting.participants.filter(user=request.user).first()
            if participant:
                participant.ideas_contributed += 1
                participant.save()
        
        return Response({'ideas': meeting.ideas_generated})
    
    @action(detail=True, methods=['post'])
    def vote_idea(self, request, pk=None):
        """Vote for an idea / 為想法投票"""
        meeting = self.get_object()
        
        idea_index = request.data.get('idea_index')
        if idea_index is None:
            return Response(
                {'error': 'idea_index is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ideas = meeting.ideas_generated or []
        if idea_index < 0 or idea_index >= len(ideas):
            return Response(
                {'error': 'Invalid idea_index'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ideas[idea_index]['votes'] = ideas[idea_index].get('votes', 0) + 1
        meeting.ideas_generated = ideas
        meeting.save()
        
        # Update participant's vote count
        if request.user.is_authenticated:
            participant = meeting.participants.filter(user=request.user).first()
            if participant:
                participant.votes_cast += 1
                participant.save()
        
        return Response({'ideas': meeting.ideas_generated})
    
    @action(detail=True, methods=['post'])
    def add_action_item(self, request, pk=None):
        """Add an action item / 添加行動項目"""
        meeting = self.get_object()
        
        action_item = {
            'task': request.data.get('task'),
            'assignee': request.data.get('assignee'),
            'deadline': request.data.get('deadline'),
            'created_at': timezone.now().isoformat()
        }
        
        if not action_item['task']:
            return Response(
                {'error': 'Task is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        action_items = meeting.action_items or []
        action_items.append(action_item)
        meeting.action_items = action_items
        meeting.save()
        
        return Response({'action_items': meeting.action_items})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get meeting statistics / 獲取會議統計"""
        queryset = self.get_queryset()
        
        return Response({
            'total_meetings': queryset.count(),
            'by_status': {
                status_value: queryset.filter(status=status_value).count()
                for status_value, _ in MeetingStatus.choices
            },
            'by_type': {
                'IN_PERSON': queryset.filter(meeting_type='IN_PERSON').count(),
                'ONLINE': queryset.filter(meeting_type='ONLINE').count(),
                'HYBRID': queryset.filter(meeting_type='HYBRID').count(),
            },
            'upcoming': queryset.filter(
                scheduled_start__gte=timezone.now(),
                status=MeetingStatus.SCHEDULED
            ).count(),
            'total_participants': BrainstormMeetingParticipant.objects.filter(
                meeting__in=queryset
            ).count()
        })
    
    @action(detail=False, methods=['get'])
    def my_meetings(self, request):
        """Get meetings where current user is organizer or participant / 獲取當前用戶的會議"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = request.user
        
        # Meetings organized by user
        organized = BrainstormMeeting.objects.filter(
            is_active=True,
            organizer=user
        )
        
        # Meetings where user is participant
        participating = BrainstormMeeting.objects.filter(
            is_active=True,
            participants__user=user
        ).exclude(organizer=user)
        
        return Response({
            'organized': BrainstormMeetingListSerializer(organized, many=True).data,
            'participating': BrainstormMeetingListSerializer(participating, many=True).data
        })


class BrainstormMeetingParticipantViewSet(viewsets.ModelViewSet):
    """
    Meeting Participant management
    會議參與者管理
    """
    queryset = BrainstormMeetingParticipant.objects.all()
    serializer_class = BrainstormMeetingParticipantSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = BrainstormMeetingParticipant.objects.filter(is_active=True)
        
        # Filter by meeting
        meeting_id = self.request.query_params.get('meeting_id')
        if meeting_id:
            queryset = queryset.filter(meeting_id=meeting_id)
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by status
        participant_status = self.request.query_params.get('status')
        if participant_status:
            queryset = queryset.filter(status=participant_status)
        
        return queryset.order_by('role', 'user__full_name')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BrainstormMeetingParticipantCreateSerializer
        if self.action == 'list':
            return BrainstormMeetingParticipantListSerializer
        return BrainstormMeetingParticipantSerializer
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """RSVP to meeting invitation / 回覆會議邀請"""
        participant = self.get_object()
        serializer = UpdateParticipantStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        participant.status = serializer.validated_data['status']
        participant.response_notes = serializer.validated_data.get('response_notes', '')
        participant.responded_at = timezone.now()
        participant.save()
        
        return Response(BrainstormMeetingParticipantSerializer(participant).data)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Mark participant as joined / 標記參與者已加入"""
        participant = self.get_object()
        participant.joined_at = timezone.now()
        if participant.status == MeetingParticipantStatus.INVITED:
            participant.status = MeetingParticipantStatus.ACCEPTED
        participant.save()
        
        return Response(BrainstormMeetingParticipantSerializer(participant).data)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Mark participant as left / 標記參與者已離開"""
        participant = self.get_object()
        participant.left_at = timezone.now()
        participant.save()
        
        return Response(BrainstormMeetingParticipantSerializer(participant).data)
