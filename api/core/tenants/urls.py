"""
Tenant URL Configuration
========================
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TenantViewSet, InvitationViewSet

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'invitations', InvitationViewSet, basename='invitation')
# Alias expected by tests
router.register(r'tenant-invitations', InvitationViewSet, basename='tenant-invitation')

urlpatterns = [
    path('', include(router.urls)),
]
