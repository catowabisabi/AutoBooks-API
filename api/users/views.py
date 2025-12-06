from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, BasePermission, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from .models import User, UserSettings, SubscriptionPlan, UserSubscription
from .serializers import (
    AdminCreateUserSerializer, UserSerializer, UserProfileSerializer, 
    UserSettingsSerializer, SubscriptionPlanSerializer, UserSubscriptionSerializer
)


class IsAdminUser(BasePermission):
    """Custom permission to only allow admin users"""

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'ADMIN'
        )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminCreateUserSerializer
        if self.action in ['update_profile', 'me']:
            return UserProfileSerializer
        return UserSerializer

    def get_permissions(self):
        """Only admins can create, update, delete users"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsAdminUser]
        else:
            self.permission_classes = [IsAuthenticated]
        return [permission() for permission in self.permission_classes]

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Return current authenticated user's information"""
        serializer = UserProfileSerializer(request.user)
        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=False, methods=['patch'], url_path='profile')
    def update_profile(self, request):
        """Update current user's profile"""
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data,
                'message': 'Profile updated successfully'
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserSettingsViewSet(viewsets.ViewSet):
    """ViewSet for user settings (notifications, billing)"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get current user's settings"""
        settings, created = UserSettings.objects.get_or_create(user=request.user)
        serializer = UserSettingsSerializer(settings)
        return Response({
            'success': True,
            'data': serializer.data
        })

    @action(detail=False, methods=['patch'], url_path='notifications')
    def update_notifications(self, request):
        """Update notification settings"""
        settings, created = UserSettings.objects.get_or_create(user=request.user)
        
        # Only allow notification-related fields
        notification_fields = [
            'email_notifications', 'push_notifications', 'sms_notifications',
            'notify_task_assigned', 'notify_task_completed', 'notify_invoice_received',
            'notify_payment_due', 'notify_system_updates', 'notify_security_alerts',
            'notify_weekly_digest', 'notify_monthly_report',
        ]
        
        data = {k: v for k, v in request.data.items() if k in notification_fields}
        serializer = UserSettingsSerializer(settings, data=data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data,
                'message': 'Notification settings updated successfully'
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['patch'], url_path='billing')
    def update_billing(self, request):
        """Update billing settings"""
        settings, created = UserSettings.objects.get_or_create(user=request.user)
        
        # Only allow billing-related fields
        billing_fields = [
            'billing_email', 'billing_address', 'billing_city', 'billing_country',
            'billing_postal_code', 'company_name', 'tax_id',
        ]
        
        data = {k: v for k, v in request.data.items() if k in billing_fields}
        serializer = UserSettingsSerializer(settings, data=data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data,
                'message': 'Billing settings updated successfully'
            })
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
