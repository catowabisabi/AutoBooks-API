from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, BasePermission, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from .models import User, UserSettings, SubscriptionPlan, UserSubscription
from .serializers import (
    AdminCreateUserSerializer, UserSerializer, UserProfileSerializer, 
    UserSettingsSerializer, SubscriptionPlanSerializer, UserSubscriptionSerializer,
    UserRegistrationSerializer
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
        if self.action == 'register':
            return UserRegistrationSerializer
        if self.action == 'create':
            return AdminCreateUserSerializer
        if self.action in ['update_profile', 'me']:
            return UserProfileSerializer
        return UserSerializer

    def get_permissions(self):
        """Only admins can create, update, delete users"""
        if self.action == 'register':
            self.permission_classes = [AllowAny]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsAdminUser]
        else:
            self.permission_classes = [IsAuthenticated]
        return [permission() for permission in self.permission_classes]
    
    def list(self, request):
        """List all users with filtering and pagination"""
        queryset = self.get_queryset()
        
        # Filter by role
        role = request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by active status
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search by email or name
        search = request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(email__icontains=search) | Q(full_name__icontains=search)
            )
        
        # Order by
        ordering = request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        # Pagination
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        total = queryset.count()
        users = queryset[start:end]
        
        serializer = UserSerializer(users, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        })
    
    def retrieve(self, request, pk=None):
        """Get user details by ID"""
        try:
            user = self.get_queryset().get(pk=pk)
            serializer = UserProfileSerializer(user)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a new user"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens for immediate login
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'message': 'User registered successfully',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserProfileSerializer(user).data
            }, status=status.HTTP_201_CREATED)
            
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

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
    
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Get user statistics (admin only)"""
        if not request.user.role == 'ADMIN':
            return Response({
                'success': False,
                'error': 'Admin access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        total = User.objects.count()
        active = User.objects.filter(is_active=True).count()
        admins = User.objects.filter(role='ADMIN').count()
        
        return Response({
            'success': True,
            'data': {
                'total': total,
                'active': active,
                'inactive': total - active,
                'admins': admins,
                'users': total - admins
            }
        })


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


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for subscription plans (public read-only)"""
    queryset = SubscriptionPlan.objects.filter(is_active=True).order_by('sort_order')
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]
    
    def list(self, request):
        """List all active subscription plans"""
        plans = self.get_queryset()
        serializer = self.get_serializer(plans, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    def retrieve(self, request, pk=None):
        """Get a specific subscription plan"""
        try:
            plan = self.get_queryset().get(pk=pk)
            serializer = self.get_serializer(plan)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Plan not found'
            }, status=status.HTTP_404_NOT_FOUND)


class UserSubscriptionViewSet(viewsets.ViewSet):
    """ViewSet for user subscription management"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get current user's subscription"""
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            serializer = UserSubscriptionSerializer(subscription)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except UserSubscription.DoesNotExist:
            # Return free plan info if no subscription
            try:
                free_plan = SubscriptionPlan.objects.get(plan_type='free')
                return Response({
                    'success': True,
                    'data': {
                        'plan': SubscriptionPlanSerializer(free_plan).data,
                        'status': 'none',
                        'message': 'No active subscription'
                    }
                })
            except SubscriptionPlan.DoesNotExist:
                return Response({
                    'success': True,
                    'data': {
                        'status': 'none',
                        'message': 'No subscription plans available'
                    }
                })
    
    @action(detail=False, methods=['post'], url_path='subscribe')
    def subscribe(self, request):
        """Subscribe to a plan"""
        plan_id = request.data.get('plan_id')
        billing_cycle = request.data.get('billing_cycle', 'monthly')
        
        if not plan_id:
            return Response({
                'success': False,
                'error': 'plan_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Plan not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create or update subscription
        today = timezone.now().date()
        trial_days = 14 if plan.plan_type != 'free' else 0
        
        subscription, created = UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'plan': plan,
                'status': 'trial' if trial_days > 0 else 'active',
                'billing_cycle': billing_cycle,
                'start_date': today,
                'trial_end_date': today + timedelta(days=trial_days) if trial_days > 0 else None,
                'next_billing_date': today + timedelta(days=trial_days) if trial_days > 0 else today + timedelta(days=30 if billing_cycle == 'monthly' else 365),
            }
        )
        
        serializer = UserSubscriptionSerializer(subscription)
        return Response({
            'success': True,
            'data': serializer.data,
            'message': f'Successfully subscribed to {plan.name}'
        })
    
    @action(detail=False, methods=['post'], url_path='cancel')
    def cancel(self, request):
        """Cancel subscription"""
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            subscription.status = 'cancelled'
            subscription.cancelled_at = timezone.now()
            subscription.save()
            
            serializer = UserSubscriptionSerializer(subscription)
            return Response({
                'success': True,
                'data': serializer.data,
                'message': 'Subscription cancelled successfully'
            })
        except UserSubscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'No active subscription found'
            }, status=status.HTTP_404_NOT_FOUND)


class AdminSubscriptionViewSet(viewsets.ModelViewSet):
    """Admin ViewSet for managing all user subscriptions"""
    queryset = UserSubscription.objects.select_related('user', 'plan').order_by('-created_at')
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def list(self, request):
        """List all subscriptions with filtering"""
        queryset = self.get_queryset()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by plan type
        plan_type = request.query_params.get('plan_type')
        if plan_type:
            queryset = queryset.filter(plan__plan_type=plan_type)
        
        # Search by user email
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(user__email__icontains=search)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': queryset.count()
        })
    
    def retrieve(self, request, pk=None):
        """Get a specific subscription"""
        try:
            subscription = self.get_queryset().get(pk=pk)
            serializer = self.get_serializer(subscription)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except UserSubscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Subscription not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'], url_path='change-plan')
    def change_plan(self, request, pk=None):
        """Admin: Change user's subscription plan"""
        try:
            subscription = self.get_queryset().get(pk=pk)
        except UserSubscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Subscription not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response({
                'success': False,
                'error': 'plan_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            new_plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Plan not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        subscription.plan = new_plan
        subscription.save()
        
        serializer = self.get_serializer(subscription)
        return Response({
            'success': True,
            'data': serializer.data,
            'message': f'Subscription changed to {new_plan.name}'
        })
    
    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        """Admin: Change subscription status"""
        try:
            subscription = self.get_queryset().get(pk=pk)
        except UserSubscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Subscription not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        new_status = request.data.get('status')
        valid_statuses = [choice[0] for choice in UserSubscription.Status.choices]
        
        if new_status not in valid_statuses:
            return Response({
                'success': False,
                'error': f'Invalid status. Must be one of: {valid_statuses}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        subscription.status = new_status
        if new_status == 'cancelled':
            subscription.cancelled_at = timezone.now()
        subscription.save()
        
        serializer = self.get_serializer(subscription)
        return Response({
            'success': True,
            'data': serializer.data,
            'message': f'Subscription status changed to {new_status}'
        })
    
    @action(detail=True, methods=['post'], url_path='extend')
    def extend(self, request, pk=None):
        """Admin: Extend subscription end date"""
        try:
            subscription = self.get_queryset().get(pk=pk)
        except UserSubscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Subscription not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        days = request.data.get('days', 30)
        try:
            days = int(days)
        except ValueError:
            return Response({
                'success': False,
                'error': 'days must be a number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if subscription.end_date:
            subscription.end_date = subscription.end_date + timedelta(days=days)
        else:
            subscription.end_date = timezone.now().date() + timedelta(days=days)
        
        if subscription.next_billing_date:
            subscription.next_billing_date = subscription.next_billing_date + timedelta(days=days)
        
        subscription.save()
        
        serializer = self.get_serializer(subscription)
        return Response({
            'success': True,
            'data': serializer.data,
            'message': f'Subscription extended by {days} days'
        })
    
    @action(detail=False, methods=['post'], url_path='create-for-user')
    def create_for_user(self, request):
        """Admin: Create subscription for a user"""
        user_id = request.data.get('user_id')
        plan_id = request.data.get('plan_id')
        billing_cycle = request.data.get('billing_cycle', 'monthly')
        status_value = request.data.get('status', 'active')
        
        if not user_id or not plan_id:
            return Response({
                'success': False,
                'error': 'user_id and plan_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Plan not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user already has subscription
        if UserSubscription.objects.filter(user=user).exists():
            return Response({
                'success': False,
                'error': 'User already has a subscription. Use change-plan instead.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        today = timezone.now().date()
        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            status=status_value,
            billing_cycle=billing_cycle,
            start_date=today,
            next_billing_date=today + timedelta(days=30 if billing_cycle == 'monthly' else 365),
        )
        
        serializer = self.get_serializer(subscription)
        return Response({
            'success': True,
            'data': serializer.data,
            'message': f'Subscription created for {user.email}'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Admin: Get subscription statistics"""
        total = UserSubscription.objects.count()
        active = UserSubscription.objects.filter(status='active').count()
        trial = UserSubscription.objects.filter(status='trial').count()
        cancelled = UserSubscription.objects.filter(status='cancelled').count()
        expired = UserSubscription.objects.filter(status='expired').count()
        
        # By plan type
        by_plan = {}
        for plan in SubscriptionPlan.objects.filter(is_active=True):
            by_plan[plan.plan_type] = UserSubscription.objects.filter(plan=plan).count()
        
        return Response({
            'success': True,
            'data': {
                'total': total,
                'by_status': {
                    'active': active,
                    'trial': trial,
                    'cancelled': cancelled,
                    'expired': expired,
                },
                'by_plan': by_plan,
            }
        })
