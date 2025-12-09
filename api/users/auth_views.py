"""
Auth Views
==========
Views for sign-up, forgot-password, account-lock flows with i18n.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _, activate
from django.conf import settings

from .models import User
from .serializers import UserProfileSerializer
from .auth_models import AccountLock, LoginAttempt
from .auth_serializers import (
    SignUpSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    LockAccountSerializer,
    UnlockAccountSerializer,
    AccountLockSerializer,
)
from core.schema_serializers import (
    SignUpRequestSerializer,
    ForgotPasswordRequestSerializer,
    ResetPasswordRequestSerializer,
    ChangePasswordRequestSerializer,
    LockAccountRequestSerializer,
    UnlockAccountRequestSerializer,
)


class SignUpView(APIView):
    serializer_class = SignUpRequestSerializer
    """
    POST /auth/signup/
    
    用戶註冊端點，支援 i18n
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Set language from request
        lang = request.data.get('language', request.headers.get('Accept-Language', 'en'))
        activate(lang[:2] if lang else 'en')
        
        serializer = SignUpSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            # Get user's tenant memberships
            from core.tenants.models import TenantMembership
            from core.tenants.serializers import TenantListSerializer
            
            memberships = TenantMembership.objects.filter(user=user, is_active=True).select_related('tenant')
            tenants = [m.tenant for m in memberships]
            
            return Response({
                'success': True,
                'message': _('Account created successfully. Welcome!'),
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserProfileSerializer(user).data,
                'tenants': TenantListSerializer(tenants, many=True, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': _('Registration failed. Please check your input.'),
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    """
    POST /auth/forgot-password/
    
    忘記密碼請求端點
    """
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordRequestSerializer
    
    def post(self, request):
        lang = request.data.get('language', request.headers.get('Accept-Language', 'en'))
        activate(lang[:2] if lang else 'en')
        
        serializer = ForgotPasswordSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            token = serializer.save()
            
            # TODO: Send email with reset link
            # For now, return token in dev mode
            response_data = {
                'success': True,
                'message': _('If an account with this email exists, a password reset link has been sent.')
            }
            
            # Include token in development for testing
            if settings.DEBUG and token:
                response_data['debug_token'] = token.token
            
            return Response(response_data)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    """
    POST /auth/reset-password/
    
    密碼重設端點
    """
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordRequestSerializer
    
    def post(self, request):
        lang = request.data.get('language', request.headers.get('Accept-Language', 'en'))
        activate(lang[:2] if lang else 'en')
        
        serializer = ResetPasswordSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.save()
            
            return Response({
                'success': True,
                'message': _('Password has been reset successfully. You can now log in with your new password.')
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    POST /auth/change-password/
    
    更改密碼端點 (需登入)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordRequestSerializer
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            
            return Response({
                'success': True,
                'message': _('Password changed successfully.')
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AccountLockStatusView(APIView):
    """
    GET /auth/lock-status/
    GET /auth/lock-status/<user_id>/
    
    檢查帳號鎖定狀態
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AccountLockSerializer
    
    def get(self, request, user_id=None):
        if user_id:
            # Admin checking another user (require admin role)
            if request.user.role != 'ADMIN':
                return Response({
                    'error': 'permission_denied',
                    'message': _('Admin access required.')
                }, status=status.HTTP_403_FORBIDDEN)
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({
                    'error': 'user_not_found',
                    'message': _('User not found.')
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user
        
        is_locked = AccountLock.is_user_locked(user)
        active_lock = AccountLock.get_active_lock(user) if is_locked else None
        
        return Response({
            'user_id': str(user.id),
            'email': user.email,
            'is_locked': is_locked,
            'lock': AccountLockSerializer(active_lock).data if active_lock else None
        })


class LockAccountView(APIView):
    """
    POST /auth/lock-account/
    
    鎖定帳號 (管理員)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LockAccountRequestSerializer
    
    def post(self, request):
        # Admin only
        if request.user.role != 'ADMIN':
            return Response({
                'error': 'permission_denied',
                'message': _('Admin access required.')
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = LockAccountSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            lock = serializer.save()
            
            return Response({
                'success': True,
                'message': _('Account has been locked.'),
                'lock': AccountLockSerializer(lock).data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UnlockAccountView(APIView):
    """
    POST /auth/unlock-account/
    
    解鎖帳號 (管理員)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UnlockAccountRequestSerializer
    
    def post(self, request):
        # Admin only
        if request.user.role != 'ADMIN':
            return Response({
                'error': 'permission_denied',
                'message': _('Admin access required.')
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = UnlockAccountSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            lock = serializer.save()
            
            return Response({
                'success': True,
                'message': _('Account has been unlocked.'),
                'lock': AccountLockSerializer(lock).data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginAttemptsView(APIView):
    """
    GET /auth/login-attempts/
    GET /auth/login-attempts/<user_id>/
    
    查看登入嘗試記錄 (管理員)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AccountLockSerializer
    
    def get(self, request, user_id=None):
        # Admin only for viewing other users
        if user_id and request.user.role != 'ADMIN':
            return Response({
                'error': 'permission_denied',
                'message': _('Admin access required.')
            }, status=status.HTTP_403_FORBIDDEN)
        
        target_user_id = user_id or request.user.id
        
        attempts = LoginAttempt.objects.filter(
            user_id=target_user_id
        ).order_by('-created_at')[:50]
        
        return Response({
            'attempts': [{
                'id': str(a.id),
                'email': a.email,
                'ip_address': a.ip_address,
                'success': a.success,
                'failure_reason': a.failure_reason,
                'created_at': a.created_at.isoformat()
            } for a in attempts]
        })
