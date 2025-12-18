"""
Notification Views
==================
API views for the notification system.
"""
from django.conf import settings
from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from drf_spectacular.utils import extend_schema, extend_schema_view

from core.models_notifications import Notification, NotificationPreference, NotificationLog
from core.serializers_notifications import (
    NotificationSerializer, NotificationListSerializer, NotificationCreateSerializer,
    NotificationPreferenceSerializer, NotificationLogSerializer,
    MarkNotificationsReadSerializer, SendNotificationSerializer, NotificationCountSerializer
)
from core.services.notification_service import NotificationService


def get_permission_classes():
    """Allow anonymous access in DEBUG mode for development"""
    if settings.DEBUG:
        return [AllowAny]
    return [IsAuthenticated]


@extend_schema_view(
    list=extend_schema(
        tags=['Notifications'],
        summary='List Notifications',
        description='Get all notifications for the current user'
    ),
    retrieve=extend_schema(
        tags=['Notifications'],
        summary='Get Notification',
        description='Get a specific notification by ID'
    ),
    create=extend_schema(
        tags=['Notifications'],
        summary='Create Notification',
        description='Create a new notification'
    ),
    destroy=extend_schema(
        tags=['Notifications'],
        summary='Delete Notification',
        description='Delete a notification'
    ),
)
class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notifications
    """
    permission_classes = get_permission_classes()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_read', 'notification_type', 'category', 'priority']
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        if self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        
        user = self.request.user
        if not user.is_authenticated:
            return Notification.objects.none()
        
        return Notification.objects.filter(user=user)
    
    @extend_schema(
        tags=['Notifications'],
        summary='Get Unread Notifications',
        description='Get all unread notifications for the current user'
    )
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications"""
        notifications = self.get_queryset().filter(is_read=False)
        serializer = NotificationListSerializer(notifications, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Notifications'],
        summary='Get Notification Counts',
        description='Get notification counts by category and type',
        responses={200: NotificationCountSerializer}
    )
    @action(detail=False, methods=['get'])
    def counts(self, request):
        """Get notification counts"""
        if not request.user.is_authenticated:
            return Response({
                'total': 0,
                'unread': 0,
                'by_category': {},
                'by_type': {}
            })
        
        counts = NotificationService.get_notification_counts(request.user)
        return Response(counts)
    
    @extend_schema(
        tags=['Notifications'],
        summary='Mark Notifications as Read',
        description='Mark specific notifications or all notifications as read',
        request=MarkNotificationsReadSerializer
    )
    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """Mark notifications as read"""
        serializer = MarkNotificationsReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notification_ids = serializer.validated_data.get('notification_ids', [])
        
        if notification_ids:
            count = NotificationService.mark_as_read(notification_ids, request.user)
        else:
            count = NotificationService.mark_all_as_read(request.user)
        
        return Response({'marked_count': count})
    
    @extend_schema(
        tags=['Notifications'],
        summary='Mark Single Notification as Read'
    )
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """Mark a single notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'marked as read'})
    
    @extend_schema(
        tags=['Notifications'],
        summary='Clear All Notifications',
        description='Delete all read notifications'
    )
    @action(detail=False, methods=['post'])
    def clear_read(self, request):
        """Delete all read notifications"""
        count, _ = self.get_queryset().filter(is_read=True).delete()
        return Response({'deleted_count': count})


class NotificationPreferenceView(APIView):
    """
    API view for managing notification preferences
    GET /api/v1/notifications/preferences/
    PUT /api/v1/notifications/preferences/
    """
    permission_classes = get_permission_classes()
    serializer_class = NotificationPreferenceSerializer
    
    @extend_schema(
        tags=['Notifications'],
        summary='Get Notification Preferences',
        description='Get notification preferences for the current user',
        responses={200: NotificationPreferenceSerializer}
    )
    def get(self, request):
        """Get user's notification preferences"""
        if not request.user.is_authenticated:
            return Response({
                'email_enabled': True,
                'push_enabled': True,
                'sms_enabled': False,
                'in_app_enabled': True,
                'category_preferences': {},
                'quiet_hours_enabled': False,
                'quiet_hours_start': None,
                'quiet_hours_end': None,
                'email_digest': False,
                'digest_frequency': 'DAILY'
            })
        
        preferences = NotificationService.get_user_preferences(request.user)
        serializer = NotificationPreferenceSerializer(preferences)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Notifications'],
        summary='Update Notification Preferences',
        description='Update notification preferences for the current user',
        request=NotificationPreferenceSerializer,
        responses={200: NotificationPreferenceSerializer}
    )
    def put(self, request):
        """Update user's notification preferences"""
        preferences = NotificationService.get_user_preferences(request.user)
        serializer = NotificationPreferenceSerializer(preferences, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    patch = put  # Allow PATCH as well


class SendNotificationView(APIView):
    """
    API view for sending notifications to users (admin only)
    POST /api/v1/notifications/send/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SendNotificationSerializer
    
    @extend_schema(
        tags=['Notifications'],
        summary='Send Notification',
        description='Send notifications to specified users (admin only)',
        request=SendNotificationSerializer,
        responses={200: {'type': 'object', 'properties': {'sent_count': {'type': 'integer'}}}}
    )
    def post(self, request):
        """Send notification to users"""
        # Check if user is admin/staff
        if not request.user.is_staff:
            return Response(
                {'error': 'Only administrators can send notifications'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        user_ids = data['user_ids']
        channels = data.get('channels', ['IN_APP'])
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(id__in=user_ids)
        
        sent_count = 0
        for user in users:
            NotificationService.create_notification(
                user=user,
                title=data['title'],
                message=data['message'],
                notification_type=data.get('notification_type', 'INFO'),
                category=data.get('category', 'SYSTEM'),
                priority=data.get('priority', 'NORMAL'),
                action_url=data.get('action_url'),
                action_label=data.get('action_label'),
                send_email='EMAIL' in channels,
                send_push='PUSH' in channels,
            )
            sent_count += 1
        
        return Response({'sent_count': sent_count})
