"""
Email Assistant ViewSets
Handles email CRUD, AI analysis, sending, IMAP sync, attachments
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.http import FileResponse, Http404
import logging

from ai_assistants.models import Email, EmailAccount, EmailAttachment, EmailTemplate
from ai_assistants.serializers.email_serializer import (
    EmailSerializer, EmailListSerializer, EmailComposeSerializer,
    EmailAccountSerializer, EmailAccountCreateSerializer,
    EmailAttachmentSerializer, EmailTemplateSerializer,
    EmailAIAnalyzeSerializer, EmailAIReplySerializer,
    EmailAttachmentUploadSerializer,
)
from ai_assistants.services.email_service import (
    summarize_email, 
    generate_ai_reply,
    send_email_smtp,
    sync_emails_for_account,
    test_smtp_connection,
    test_imap_connection,
)

logger = logging.getLogger(__name__)


def get_permission_classes():
    """Return permission classes based on DEBUG setting"""
    if settings.DEBUG:
        return [AllowAny()]
    return [IsAuthenticated()]


def get_user_filter(request, queryset, owner_field='owner'):
    """Apply user-based filtering when authenticated"""
    if request.user.is_authenticated:
        return queryset.filter(**{owner_field: request.user})
    return queryset


class EmailAccountViewSet(viewsets.ModelViewSet):
    """
    Email Account management with SMTP/IMAP testing
    """
    queryset = EmailAccount.objects.all()
    serializer_class = EmailAccountSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = EmailAccount.objects.filter(is_active=True)
        if self.request.user.is_authenticated:
            return queryset.filter(owner=self.request.user)
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EmailAccountCreateSerializer
        return EmailAccountSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user if self.request.user.is_authenticated else None)
    
    @action(detail=True, methods=['post'])
    def test_smtp(self, request, pk=None):
        """Test SMTP connection"""
        account = self.get_object()
        result = test_smtp_connection(account)
        return Response(result)
    
    @action(detail=True, methods=['post'])
    def test_imap(self, request, pk=None):
        """Test IMAP connection"""
        account = self.get_object()
        result = test_imap_connection(account)
        return Response(result)
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Sync emails from IMAP server"""
        account = self.get_object()
        limit = int(request.data.get('limit', 50))
        result = sync_emails_for_account(account, limit=limit)
        return Response(result)


class EmailViewSet(viewsets.ModelViewSet):
    """
    Email CRUD and AI features with user isolation
    """
    queryset = Email.objects.all()
    serializer_class = EmailSerializer
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = Email.objects.filter(is_active=True)
        
        # User isolation - filter by accounts owned by user
        if self.request.user.is_authenticated:
            user_accounts = EmailAccount.objects.filter(owner=self.request.user)
            queryset = queryset.filter(
                Q(account__in=user_accounts) | Q(account__isnull=True)
            )
        
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
        
        # Filter by account
        account_id = self.request.query_params.get('account')
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        
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
        payload = request.data.copy()
        payload['email_id'] = str(email.id)

        serializer = EmailAIAnalyzeSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        try:
            analysis = summarize_email(email)
            email.ai_summary = analysis.get('summary')
            email.ai_action_items = analysis.get('action_items', [])
            email.ai_sentiment = analysis.get('sentiment')
            email.save(update_fields=['ai_summary', 'ai_action_items', 'ai_sentiment'])
        except Exception as exc:
            logger.error("Email analyze failed: %s", exc, exc_info=True)
            return Response(
                {"error": "Failed to analyze email"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
        payload = request.data.copy()
        payload['email_id'] = str(email.id)

        serializer = EmailAIReplySerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        tone = serializer.validated_data.get('tone', 'professional')
        key_points = serializer.validated_data.get('key_points') or []

        try:
            result = generate_ai_reply(email, tone, key_points)
            email.ai_suggested_reply = result.get('suggested_reply')
            email.save(update_fields=['ai_suggested_reply'])
        except Exception as exc:
            logger.error("Email reply generation failed: %s", exc, exc_info=True)
            return Response(
                {"error": "Failed to generate reply"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(result)
    
    @action(detail=False, methods=['post'])
    def compose(self, request):
        """
        Compose and send a new email via SMTP
        """
        serializer = EmailComposeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        account_id = data.get('account_id')
        account = None
        
        # Get account if specified
        if account_id:
            try:
                account = EmailAccount.objects.get(id=account_id)
                if self.request.user.is_authenticated and account.owner != self.request.user:
                    return Response(
                        {"error": "Account not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            except EmailAccount.DoesNotExist:
                return Response(
                    {"error": "Account not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Determine from address
        from_address = account.email_address if account else data.get('from_address', 'demo@wisematic.com')
        from_name = account.display_name if account else 'Demo User'
        
        # Create email record
        email = Email.objects.create(
            account=account,
            from_address=from_address,
            from_name=from_name,
            to_addresses=data['to_addresses'],
            cc_addresses=data.get('cc_addresses', []),
            bcc_addresses=data.get('bcc_addresses', []),
            subject=data['subject'],
            body_text=data.get('body_text', ''),
            body_html=data.get('body_html', ''),
            priority=data.get('priority', 'NORMAL'),
            status='DRAFT',
        )
        
        # Send via SMTP if account is configured
        send_result = {"success": True, "demo": True}
        if account:
            send_result = send_email_smtp(
                account=account,
                to_addresses=data['to_addresses'],
                subject=data['subject'],
                body_text=data.get('body_text', ''),
                body_html=data.get('body_html', ''),
                cc_addresses=data.get('cc_addresses', []),
                bcc_addresses=data.get('bcc_addresses', []),
            )
        
        if send_result.get('success'):
            email.status = 'SENT'
            email.sent_at = timezone.now()
            email.save()
        else:
            # Keep as draft if send failed
            return Response(
                {
                    "error": send_result.get('error', 'Failed to send email'),
                    "email": EmailSerializer(email).data
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(
            {
                **EmailSerializer(email).data,
                "send_result": send_result
            },
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


class EmailAttachmentViewSet(viewsets.ModelViewSet):
    """
    Email attachment management - upload and download
    """
    queryset = EmailAttachment.objects.all()
    serializer_class = EmailAttachmentSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def get_permissions(self):
        return get_permission_classes()
    
    def get_queryset(self):
        queryset = EmailAttachment.objects.filter(is_active=True)
        
        # Filter by email
        email_id = self.request.query_params.get('email')
        if email_id:
            queryset = queryset.filter(email_id=email_id)
        
        # User isolation
        if self.request.user.is_authenticated:
            user_accounts = EmailAccount.objects.filter(owner=self.request.user)
            queryset = queryset.filter(
                Q(email__account__in=user_accounts) | Q(email__account__isnull=True)
            )
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Upload attachment to an email
        """
        email_id = request.data.get('email_id')
        if not email_id:
            return Response(
                {"error": "email_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            email = Email.objects.get(id=email_id)
        except Email.DoesNotExist:
            return Response(
                {"error": "Email not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission
        if self.request.user.is_authenticated:
            if email.account and email.account.owner != self.request.user:
                return Response(
                    {"error": "Permission denied"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        file = request.FILES.get('file')
        if not file:
            return Response(
                {"error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        attachment = EmailAttachment.objects.create(
            email=email,
            filename=file.name,
            file=file,
            content_type=file.content_type or 'application/octet-stream',
            size=file.size,
        )
        
        # Update email has_attachments flag
        email.has_attachments = True
        email.save(update_fields=['has_attachments'])
        
        return Response(
            EmailAttachmentSerializer(attachment).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download attachment file
        """
        attachment = self.get_object()
        
        if not attachment.file:
            raise Http404("File not found")
        
        response = FileResponse(
            attachment.file.open('rb'),
            content_type=attachment.content_type or 'application/octet-stream',
        )
        response['Content-Disposition'] = f'attachment; filename="{attachment.filename}"'
        return response
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """
        Preview attachment (for images, PDFs)
        """
        attachment = self.get_object()
        
        if not attachment.file:
            raise Http404("File not found")
        
        # Determine if file can be previewed inline
        previewable_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'text/html',
        ]
        
        content_type = attachment.content_type or 'application/octet-stream'
        disposition = 'inline' if content_type in previewable_types else 'attachment'
        
        response = FileResponse(
            attachment.file.open('rb'),
            content_type=content_type,
        )
        response['Content-Disposition'] = f'{disposition}; filename="{attachment.filename}"'
        return response

