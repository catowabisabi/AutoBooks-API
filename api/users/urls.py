from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserSettingsViewSet, SubscriptionPlanViewSet, UserSubscriptionViewSet
from .oauth_views import GoogleOAuthView, GoogleOAuthCallbackView
from .auth_views import (
    SignUpView,
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
    AccountLockStatusView,
    LockAccountView,
    UnlockAccountView,
    LoginAttemptsView,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'user-settings', UserSettingsViewSet, basename='user-settings')
router.register(r'subscription-plans', SubscriptionPlanViewSet, basename='subscription-plan')
router.register(r'my-subscription', UserSubscriptionViewSet, basename='my-subscription')

urlpatterns = [
    # OAuth
    path('auth/google/', GoogleOAuthView.as_view(), name='google-oauth'),
    path('auth/google/callback/', GoogleOAuthCallbackView.as_view(), name='google-oauth-callback'),
    
    # Sign-up & Password Management
    path('auth/signup/', SignUpView.as_view(), name='auth-signup'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='auth-forgot-password'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='auth-reset-password'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    
    # Account Lock Management
    path('auth/account-lock-status/', AccountLockStatusView.as_view(), name='auth-account-lock-status'),
    path('auth/account-lock-status/<int:user_id>/', AccountLockStatusView.as_view(), name='auth-account-lock-status-user'),
    path('auth/lock-account/<int:user_id>/', LockAccountView.as_view(), name='auth-lock-account'),
    path('auth/unlock-account/<int:user_id>/', UnlockAccountView.as_view(), name='auth-unlock-account'),
    path('auth/login-attempts/', LoginAttemptsView.as_view(), name='auth-login-attempts'),
    path('auth/login-attempts/<int:user_id>/', LoginAttemptsView.as_view(), name='auth-login-attempts-user'),
] + router.urls
