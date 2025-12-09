"""
Tenant ViewSets
===============
API endpoints for tenant and membership management.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.utils.translation import gettext_lazy as gettext
from django.shortcuts import get_object_or_404

# Alias for translation
_ = gettext

from .models import Tenant, TenantMembership, TenantInvitation, TenantRole
from .serializers import (
    TenantSerializer,
    TenantListSerializer,
    TenantCreateSerializer,
    TenantMembershipSerializer,
    TenantInvitationSerializer,
    InviteUserSerializer,
    AcceptInvitationSerializer,
)
from .decorators import require_tenant, require_admin_access
from core.schema_serializers import InvitationAcceptResponseSerializer


class TenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for tenant management.
    
    list:       GET /tenants/          - List user's tenants
    create:     POST /tenants/         - Create new tenant (user becomes owner)
    retrieve:   GET /tenants/{id}/     - Get tenant details
    update:     PUT /tenants/{id}/     - Update tenant (admin only)
    destroy:    DELETE /tenants/{id}/  - Delete tenant (owner only)
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return tenants where user is a member"""
        if self.request.user.is_superuser:
            return Tenant.objects.all()
        
        tenant_ids = TenantMembership.objects.filter(
            user=self.request.user,
            is_active=True
        ).values_list('tenant_id', flat=True)
        
        return Tenant.objects.filter(id__in=tenant_ids, is_active=True)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TenantListSerializer
        elif self.action == 'create':
            return TenantCreateSerializer
        return TenantSerializer
    
    def perform_update(self, serializer):
        """Only admins can update tenant"""
        tenant = self.get_object()
        membership = TenantMembership.objects.filter(
            tenant=tenant,
            user=self.request.user,
            is_active=True
        ).first()
        
        if not membership or not membership.has_admin_access:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(_("Admin access required to update tenant."))
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only owner can delete tenant"""
        membership = TenantMembership.objects.filter(
            tenant=instance,
            user=self.request.user,
            is_active=True
        ).first()
        
        if not membership or membership.role != TenantRole.OWNER.value:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(_("Only the owner can delete this organization."))
        
        # Soft delete
        instance.is_active = False
        instance.save()
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """List members of a tenant"""
        tenant = self.get_object()
        memberships = TenantMembership.objects.filter(tenant=tenant).select_related('user')
        serializer = TenantMembershipSerializer(memberships, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        """Invite a user to the tenant"""
        tenant = self.get_object()
        
        # Check admin access
        membership = TenantMembership.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True
        ).first()
        
        if not membership or not membership.has_admin_access:
            return Response({
                'error': 'permission_denied',
                'message': _('Admin access required to invite users.')
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Set tenant context for serializer
        request.tenant = tenant
        serializer = InviteUserSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()
        
        # TODO: Send invitation email
        
        return Response({
            'message': _('Invitation sent successfully.'),
            'invitation': TenantInvitationSerializer(invitation).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'], url_path='members/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        """Remove a member from the tenant"""
        tenant = self.get_object()
        
        # Check admin access
        membership = TenantMembership.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True
        ).first()
        
        if not membership or not membership.has_admin_access:
            return Response({
                'error': 'permission_denied',
                'message': _('Admin access required to remove users.')
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Cannot remove owner
        target_membership = get_object_or_404(TenantMembership, tenant=tenant, user_id=user_id)
        if target_membership.role == TenantRole.OWNER.value:
            return Response({
                'error': 'cannot_remove_owner',
                'message': _('Cannot remove the owner from the organization.')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        target_membership.is_active = False
        target_membership.save()
        
        return Response({'message': _('Member removed successfully.')})
    
    @action(detail=True, methods=['patch'], url_path='members/(?P<user_id>[^/.]+)/role')
    def update_role(self, request, pk=None, user_id=None):
        """Update a member's role"""
        tenant = self.get_object()
        
        # Check admin access
        membership = TenantMembership.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True
        ).first()
        
        if not membership or not membership.has_admin_access:
            return Response({
                'error': 'permission_denied',
                'message': _('Admin access required to change roles.')
            }, status=status.HTTP_403_FORBIDDEN)
        
        new_role = request.data.get('role')
        if new_role not in [r[0] for r in TenantRole.choices()]:
            return Response({
                'error': 'invalid_role',
                'message': _('Invalid role specified.')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cannot change owner role unless you are owner
        target_membership = get_object_or_404(TenantMembership, tenant=tenant, user_id=user_id)
        if target_membership.role == TenantRole.OWNER.value and membership.role != TenantRole.OWNER.value:
            return Response({
                'error': 'cannot_change_owner',
                'message': _('Only the owner can transfer ownership.')
            }, status=status.HTTP_403_FORBIDDEN)
        
        target_membership.role = new_role
        target_membership.save()
        
        return Response({
            'message': _('Role updated successfully.'),
            'membership': TenantMembershipSerializer(target_membership).data
        })


class InvitationViewSet(viewsets.ViewSet):
    """
    ViewSet for handling invitations.
    
    accept: POST /tenant-invitations/{id}/accept/  - Accept an invitation
    """
    permission_classes = [IsAuthenticated]
    serializer_class = InvitationAcceptResponseSerializer

    def _get_tenant_context(self, request):
        """Get tenant and membership from request, resolving from headers if needed"""
        tenant = getattr(request, 'tenant', None)
        membership = getattr(request, 'tenant_membership', None)
        
        if tenant and membership:
            return tenant, membership
        
        # Try to resolve from headers (fallback for test client)
        tenant_id = request.META.get('HTTP_X_TENANT_ID') or request.headers.get('X-Tenant-ID')
        tenant_slug = request.META.get('HTTP_X_TENANT_SLUG') or request.headers.get('X-Tenant-Slug')
        
        if tenant_id:
            try:
                tenant = Tenant.objects.get(id=tenant_id, is_active=True)
            except (Tenant.DoesNotExist, ValueError, Exception):
                return None, None
        elif tenant_slug:
            try:
                tenant = Tenant.objects.get(slug=tenant_slug, is_active=True)
            except Tenant.DoesNotExist:
                return None, None
        
        if tenant:
            try:
                membership = TenantMembership.objects.get(
                    user=request.user,
                    tenant=tenant,
                    is_active=True
                )
            except TenantMembership.DoesNotExist:
                return tenant, None
        
        return tenant, membership

    def create(self, request):
        """Create a tenant invitation (owner/admin only)"""
        from core.tenants.models import TenantRole

        tenant, membership = self._get_tenant_context(request)

        if tenant is None or membership is None:
            return Response({
                'error': 'tenant_required',
                'message': gettext('A valid tenant context is required.')
            }, status=status.HTTP_400_BAD_REQUEST)

        if membership.role not in [TenantRole.OWNER.value, TenantRole.ADMIN.value]:
            return Response({
                'error': 'permission_denied',
                'message': gettext('Admin access required to invite users.')
            }, status=status.HTTP_403_FORBIDDEN)

        # Ensure request has tenant for serializer
        request.tenant = tenant
        serializer = InviteUserSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()

        return Response(
            TenantInvitationSerializer(invitation).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        """Accept a tenant invitation"""
        invitation = get_object_or_404(TenantInvitation, pk=pk)

        if not invitation.is_valid:
            return Response({
                'error': 'invalid_invitation',
                'message': gettext('This invitation has expired or was already used.')
            }, status=status.HTTP_400_BAD_REQUEST)

        membership, created = TenantMembership.objects.update_or_create(
            tenant=invitation.tenant,
            user=request.user,
            defaults={
                'role': invitation.role,
                'is_active': True,
                'invited_by': invitation.invited_by,
                'accepted_at': timezone.now()
            }
        )

        invitation.accepted_at = timezone.now()
        invitation.save()
        
        return Response({
            'message': gettext('Invitation accepted successfully.'),
            'membership': TenantMembershipSerializer(membership).data
        })
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """List pending invitations for current user's email"""
        invitations = TenantInvitation.objects.filter(
            email=request.user.email,
            accepted_at__isnull=True
        ).select_related('tenant', 'invited_by')
        
        # Filter out expired
        valid_invitations = [inv for inv in invitations if inv.is_valid]
        
        serializer = TenantInvitationSerializer(valid_invitations, many=True)
        return Response(serializer.data)
