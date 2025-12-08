"""
Tenant ViewSets
===============
API endpoints for tenant and membership management.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404

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
    
    accept: POST /invitations/accept/  - Accept an invitation
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def accept(self, request):
        """Accept a tenant invitation"""
        serializer = AcceptInvitationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        
        return Response({
            'message': _('Invitation accepted successfully.'),
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
