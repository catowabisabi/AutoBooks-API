from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserViewSet
from .oauth_views import GoogleOAuthView, GoogleOAuthCallbackView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('auth/google/', GoogleOAuthView.as_view(), name='google-oauth'),
    path('auth/google/callback/', GoogleOAuthCallbackView.as_view(), name='google-oauth-callback'),
] + router.urls
