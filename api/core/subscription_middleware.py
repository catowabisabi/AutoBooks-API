"""
Subscription Middleware
========================
Middleware for checking subscription plan features and limits.
Adds subscription info to request and provides feature restriction.
"""

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext_lazy as _

from users.models import SubscriptionPlan, UserSubscription


class SubscriptionMiddleware(MiddlewareMixin):
    """
    Middleware to add subscription context to each request and
    enforce feature restrictions based on user's subscription plan.
    
    Add to MIDDLEWARE in settings.py AFTER AuthenticationMiddleware:
        'core.subscription_middleware.SubscriptionMiddleware',
    """
    
    # Paths that don't require subscription checks
    EXEMPT_PATHS = [
        '/api/v1/auth/',
        '/api/v1/subscription-plans/',
        '/api/v1/my-subscription/',
        '/admin/',
        '/health/',
        '/__debug__/',
    ]
    
    # Feature to endpoint mapping - which features require which plan capabilities
    FEATURE_RESTRICTIONS = {
        # AI features require has_ai_assistant
        '/api/v1/ai/': 'has_ai_assistant',
        '/api/v1/ai-assistants/': 'has_ai_assistant',
        '/api/v1/rag/': 'has_ai_assistant',
        
        # Analytics features require has_advanced_analytics
        '/api/v1/analytics/advanced/': 'has_advanced_analytics',
        '/api/v1/analytics/dashboard/': 'has_advanced_analytics',
        
        # Custom reports require has_custom_reports
        '/api/v1/reports/custom/': 'has_custom_reports',
        
        # API access (external integrations)
        '/api/v1/external/': 'has_api_access',
        '/api/v1/webhooks/': 'has_api_access',
        
        # SSO endpoints
        '/api/v1/sso/': 'has_sso',
        
        # Audit logs
        '/api/v1/audit-logs/': 'has_audit_logs',
    }
    
    def process_request(self, request):
        """Add subscription info to request and check feature access"""
        # Initialize defaults
        request.subscription = None
        request.subscription_plan = None
        request.subscription_features = {}
        
        # Skip for exempt paths
        if self._is_exempt_path(request.path):
            return None
        
        # Skip for unauthenticated users
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # Get user's subscription
        subscription = self._get_user_subscription(request.user)
        plan = self._get_subscription_plan(subscription)
        
        # Add to request
        request.subscription = subscription
        request.subscription_plan = plan
        request.subscription_features = self._get_features_dict(plan)
        
        # Check feature restrictions
        restriction_error = self._check_feature_restriction(request.path, plan)
        if restriction_error:
            return restriction_error
        
        return None
    
    def _is_exempt_path(self, path):
        """Check if path is exempt from subscription checks"""
        return any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS)
    
    def _get_user_subscription(self, user):
        """Get user's subscription"""
        try:
            return UserSubscription.objects.select_related('plan').get(
                user=user,
                status__in=['active', 'trial']
            )
        except UserSubscription.DoesNotExist:
            return None
    
    def _get_subscription_plan(self, subscription):
        """Get subscription plan (default to free if no subscription)"""
        if subscription:
            return subscription.plan
        
        # Return free plan as default
        try:
            return SubscriptionPlan.objects.get(plan_type='free', is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return None
    
    def _get_features_dict(self, plan):
        """Convert plan features to dictionary for easy access"""
        if not plan:
            return {
                'has_ai_assistant': False,
                'has_advanced_analytics': False,
                'has_custom_reports': False,
                'has_api_access': False,
                'has_priority_support': False,
                'has_sso': False,
                'has_audit_logs': False,
                'has_data_export': False,
                'has_multi_currency': False,
                'has_custom_branding': False,
                'max_users': 1,
                'max_companies': 1,
                'max_storage_gb': 1,
                'max_documents': 50,
                'max_invoices_monthly': 10,
                'max_employees': 5,
                'max_projects': 2,
                'ai_queries_monthly': 0,
                'rag_documents': 0,
            }
        
        return {
            'has_ai_assistant': plan.has_ai_assistant,
            'has_advanced_analytics': plan.has_advanced_analytics,
            'has_custom_reports': plan.has_custom_reports,
            'has_api_access': plan.has_api_access,
            'has_priority_support': plan.has_priority_support,
            'has_sso': plan.has_sso,
            'has_audit_logs': plan.has_audit_logs,
            'has_data_export': plan.has_data_export,
            'has_multi_currency': plan.has_multi_currency,
            'has_custom_branding': plan.has_custom_branding,
            'max_users': plan.max_users,
            'max_companies': plan.max_companies,
            'max_storage_gb': plan.max_storage_gb,
            'max_documents': plan.max_documents,
            'max_invoices_monthly': plan.max_invoices_monthly,
            'max_employees': plan.max_employees,
            'max_projects': plan.max_projects,
            'ai_queries_monthly': plan.ai_queries_monthly,
            'rag_documents': plan.rag_documents,
        }
    
    def _check_feature_restriction(self, path, plan):
        """Check if path requires a feature the user doesn't have"""
        if not plan:
            # No plan means free tier, check restrictions
            pass
        
        for restricted_path, required_feature in self.FEATURE_RESTRICTIONS.items():
            if path.startswith(restricted_path):
                if not plan or not getattr(plan, required_feature, False):
                    return JsonResponse({
                        'success': False,
                        'error': 'feature_restricted',
                        'message': _('This feature is not available on your current plan. Please upgrade to access this feature.'),
                        'required_feature': required_feature,
                        'upgrade_url': '/dashboard/settings/subscription'
                    }, status=403)
        
        return None


def check_subscription_limit(user, limit_type, current_count=None):
    """
    Utility function to check if user has reached a subscription limit.
    
    Usage:
        can_add, error = check_subscription_limit(request.user, 'max_users', current_count=5)
        if not can_add:
            return Response({'error': error}, status=403)
    
    Args:
        user: Django User instance
        limit_type: One of 'max_users', 'max_companies', 'max_documents', etc.
        current_count: Current count (if None, will return the limit)
    
    Returns:
        tuple: (can_proceed: bool, error_message: str or None)
    """
    try:
        subscription = UserSubscription.objects.select_related('plan').get(
            user=user,
            status__in=['active', 'trial']
        )
        plan = subscription.plan
    except UserSubscription.DoesNotExist:
        # Default to free plan limits
        try:
            plan = SubscriptionPlan.objects.get(plan_type='free', is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return False, "No subscription plan found"
    
    limit = getattr(plan, limit_type, 0)
    
    # 0 means unlimited
    if limit == 0:
        return True, None
    
    if current_count is not None and current_count >= limit:
        return False, f"You have reached the limit of {limit} for {limit_type.replace('max_', '').replace('_', ' ')} on your current plan."
    
    return True, None


def has_feature(user, feature_name):
    """
    Utility function to check if user has a specific feature.
    
    Usage:
        if has_feature(request.user, 'has_ai_assistant'):
            # Allow AI features
        else:
            # Show upgrade prompt
    
    Args:
        user: Django User instance
        feature_name: Feature name like 'has_ai_assistant', 'has_custom_reports', etc.
    
    Returns:
        bool: Whether the user has access to the feature
    """
    try:
        subscription = UserSubscription.objects.select_related('plan').get(
            user=user,
            status__in=['active', 'trial']
        )
        plan = subscription.plan
    except UserSubscription.DoesNotExist:
        try:
            plan = SubscriptionPlan.objects.get(plan_type='free', is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return False
    
    return getattr(plan, feature_name, False)
