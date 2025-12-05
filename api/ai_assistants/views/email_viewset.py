"""
Email Assistant ViewSets
Handles email CRUD, AI analysis, sending
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
import logging

from ai_assistants.models import Email, EmailAccount, EmailAttachment, EmailTemplate
from ai_assistants.serializers.email_serializer import (
    EmailSerializer, EmailListSerializer, EmailComposeSerializer,
    EmailAccountSerializer, EmailAccountCreateSerializer,
    EmailAttachmentSerializer, EmailTemplateSerializer,
    EmailAIAnalyzeSerializer, EmailAIReplySerializer
)

logger = logging.getLogger(__name__)


def get_permission_classes():
    """Return permission classes based on DEBUG setting"""
    if settings.DEBUG:
        return [AllowAny()]
    return [IsAuthenticated()]


class EmailAccountViewSet(viewsets.ModelViewSet):
    """
    Email Account management
    """
    queryset = EmailAccount.objects.all()
    serializer_class = EmailAccountSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return EmailAccount.objects.filter(owner=self.request.user, is_active=True)
        return EmailAccount.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EmailAccountCreateSerializer
        return EmailAccountSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user if self.request.user.is_authenticated else None)


class EmailViewSet(viewsets.ModelViewSet):
    """
    Email CRUD and AI features
    """
    queryset = Email.objects.all()
    serializer_class = EmailSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = Email.objects.filter(is_active=True)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by read/unread
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        # Filter by starred
        is_starred = self.request.query_params.get('is_starred')
        if is_starred is not None:
            queryset = queryset.filter(is_starred=is_starred.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(subject__icontains=search) |
                Q(from_address__icontains=search) |
                Q(body_text__icontains=search) |
                Q(ai_summary__icontains=search)
            )
        
        return queryset.order_by('-received_at', '-created_at')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EmailListSerializer
        return EmailSerializer
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark email as read"""
        email = self.get_object()
        email.is_read = True
        email.read_at = timezone.now()
        email.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """Mark email as unread"""
        email = self.get_object()
        email.is_read = False
        email.read_at = None
        email.save()
        return Response({'status': 'marked as unread'})
    
    @action(detail=True, methods=['post'])
    def toggle_star(self, request, pk=None):
        """Toggle starred status"""
        email = self.get_object()
        email.is_starred = not email.is_starred
        email.save()
        return Response({'is_starred': email.is_starred})
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive email"""
        email = self.get_object()
        email.status = 'ARCHIVED'
        email.save()
        return Response({'status': 'archived'})
    
    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """
        AI analyze email - generate summary, extract action items
        """
        email = self.get_object()
        
        # TODO: Integrate with AI service
        # For now, return mock data
        email.ai_summary = f"Summary of email: {email.subject[:50]}..."
        email.ai_action_items = [
            {"action": "Follow up", "deadline": "Next week"},
            {"action": "Review documents", "deadline": "2 days"}
        ]
        email.ai_sentiment = "neutral"
        email.save()
        
        return Response({
            'summary': email.ai_summary,
            'action_items': email.ai_action_items,
            'sentiment': email.ai_sentiment
        })
    
    @action(detail=True, methods=['post'])
    def generate_reply(self, request, pk=None):
        """
        AI generate reply for email
        """
        email = self.get_object()
        serializer = EmailAIReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tone = serializer.validated_data.get('tone', 'professional')
        
        # TODO: Integrate with AI service
        # For now, return mock reply
        suggested_reply = f"""
Dear {email.from_name or 'Sir/Madam'},

Thank you for your email regarding "{email.subject}".

I acknowledge receipt of your message and will respond in detail shortly.

Best regards
        """.strip()
        
        email.ai_suggested_reply = suggested_reply
        email.save()
        
        return Response({
            'suggested_reply': suggested_reply,
            'tone': tone
        })
    
    @action(detail=False, methods=['post'])
    def compose(self, request):
        """
        Compose and send a new email
        """
        serializer = EmailComposeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Create email record
        email = Email.objects.create(
            from_address=data.get('from_address', 'demo@wisematic.com'),
            from_name='Demo User',
            to_addresses=data['to_addresses'],
            cc_addresses=data.get('cc_addresses', []),
            bcc_addresses=data.get('bcc_addresses', []),
            subject=data['subject'],
            body_text=data.get('body_text', ''),
            body_html=data.get('body_html', ''),
            priority=data.get('priority', 'NORMAL'),
            status='SENT',
            sent_at=timezone.now()
        )
        
        # In demo mode, just save to DB
        # In production, would use SMTP to send
        
        return Response(
            EmailSerializer(email).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['get'])
    def inbox(self, request):
        """Get inbox emails"""
        queryset = self.get_queryset().filter(status='RECEIVED')
        serializer = EmailListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def sent(self, request):
        """Get sent emails"""
        queryset = self.get_queryset().filter(status='SENT')
        serializer = EmailListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def drafts(self, request):
        """Get draft emails"""
        queryset = self.get_queryset().filter(status='DRAFT')
        serializer = EmailListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get email statistics"""
        queryset = self.get_queryset()
        return Response({
            'total': queryset.count(),
            'unread': queryset.filter(is_read=False).count(),
            'starred': queryset.filter(is_starred=True).count(),
            'by_category': {
                cat: queryset.filter(category=cat).count()
                for cat, _ in Email._meta.get_field('category').choices
            }
        })


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    Email template management
    """
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = EmailTemplate.objects.filter(is_active=True)
        
        # Show shared templates + user's own
        if self.request.user.is_authenticated:
            queryset = queryset.filter(
                Q(is_shared=True) | Q(owner=self.request.user)
            )
        else:
            queryset = queryset.filter(is_shared=True)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user if self.request.user.is_authenticated else None)
    
    @action(detail=True, methods=['post'])
    def render(self, request, pk=None):
        """
        Render template with variables
        """
        template = self.get_object()
        variables = request.data.get('variables', {})
        
        subject = template.subject_template
        body = template.body_template
        
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
        
        return Response({
            'subject': subject,
            'body': body
        })
