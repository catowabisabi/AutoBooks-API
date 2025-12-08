from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from users.google_oauth import GoogleOAuthURLView, GoogleOAuthCallbackView, GoogleOAuthTokenView
from core.views.api_key_views import ApiKeyStatusView, ApiKeyManageView, ApiKeyTestView
from core.views.rag_views import RAGQueryView, RAGChatView, RAGKnowledgeListView

urlpatterns = [
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # JWT Auth
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Google OAuth
    path('api/v1/auth/google/', GoogleOAuthURLView.as_view(), name='google_oauth_url'),
    path('api/v1/auth/google/callback/', GoogleOAuthCallbackView.as_view(), name='google_oauth_callback'),
    path('api/v1/auth/google/token/', GoogleOAuthTokenView.as_view(), name='google_oauth_token'),

    # API Key Management
    path('api/v1/settings/api-keys/status/', ApiKeyStatusView.as_view(), name='api_key_status'),
    path('api/v1/settings/api-keys/<str:provider>/', ApiKeyManageView.as_view(), name='api_key_manage'),
    path('api/v1/settings/api-keys/<str:provider>/test/', ApiKeyTestView.as_view(), name='api_key_test'),

    # RAG Knowledge Base
    path('api/v1/rag/query/', RAGQueryView.as_view(), name='rag_query'),
    path('api/v1/rag/chat/', RAGChatView.as_view(), name='rag_chat'),
    path('api/v1/rag/knowledge/', RAGKnowledgeListView.as_view(), name='rag_knowledge'),

    # Feature Modules
    path('api/v1/', include('health.urls')),
    path('api/v1/', include('coredata.urls')),
    path('api/v1/', include('users.urls')),
    path('api/v1/hrms/', include('hrms.urls')),
    path('api/v1/', include('documents.urls')),
    path('api/v1/analytics/', include('analytics.urls')),

    # AI Assistants
    path('api/v1/', include('ai_assistants.urls')),
    
    # Accounting Module
    path('api/v1/', include('accounting.urls')),
    
    # Business Operations Module
    path('api/v1/business/', include('business.urls')),
    
    # Tenant Management
    path('api/v1/', include('core.tenants.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

