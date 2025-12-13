"""
Permission Utilities
====================
Centralized permission helpers for API views.

Usage:
    from core.permissions import get_permission_classes
    
    class MyViewSet(viewsets.ModelViewSet):
        permission_classes = get_permission_classes()
        
    # Or dynamically:
    class MyViewSet(viewsets.ModelViewSet):
        def get_permissions(self):
            return [p() for p in get_permission_classes()]
"""

from django.conf import settings
from rest_framework.permissions import IsAuthenticated, AllowAny


def get_permission_classes(require_auth=True):
    """
    Get permission classes based on settings.
    
    Args:
        require_auth: If True (default), requires authentication unless AUTH_DISABLED is set.
                      If False, always allows any access.
    
    Returns:
        List of permission classes to use.
    
    Usage in settings or .env:
        AUTH_DISABLED=true   # Disable all auth (for testing)
        AUTH_DISABLED=false  # Normal authentication (default)
    """
    if not require_auth:
        return [AllowAny]
    
    # Check if auth is globally disabled
    if getattr(settings, 'AUTH_DISABLED', False):
        return [AllowAny]
    
    return [IsAuthenticated]


def get_auth_status():
    """
    Get current authentication status for debugging.
    
    Returns:
        dict with auth configuration info
    """
    return {
        'auth_disabled': getattr(settings, 'AUTH_DISABLED', False),
        'debug': getattr(settings, 'DEBUG', False),
        'effective_permission': 'AllowAny' if getattr(settings, 'AUTH_DISABLED', False) else 'IsAuthenticated'
    }


class ConditionalAuthentication:
    """
    Mixin for ViewSets that respects AUTH_DISABLED setting.
    
    Usage:
        class MyViewSet(ConditionalAuthentication, viewsets.ModelViewSet):
            # permission_classes will be set automatically
            pass
    """
    
    def get_permissions(self):
        return [p() for p in get_permission_classes()]
