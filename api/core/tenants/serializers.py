"""
Tenant Serializers
==================
DRF serializers for Tenant and Membership models.
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
import secrets

from .models import Tenant, TenantMembership, TenantInvitation, TenantRole


class TenantSerializer(serializers.ModelSerializer):
    """Full tenant serializer for admins"""
    member_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'legal_name', 'tax_id', 'industry',
            'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country',
            'phone', 'email', 'website',
            'default_currency', 'fiscal_year_start_month', 'timezone',
            'subscription_plan', 'subscription_status', 'max_users',
            'logo_url', 'is_active', 'member_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'member_count']


class TenantListSerializer(serializers.ModelSerializer):
    """Lightweight tenant serializer for lists"""
    member_count = serializers.ReadOnlyField()
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'logo_url', 'member_count', 'role', 'subscription_plan']
    
    def get_role(self, obj):
        """Get current user's role in this tenant"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                membership = TenantMembership.objects.get(
                    tenant=obj,
                    user=request.user,
                    is_active=True
                )
                return membership.role
            except TenantMembership.DoesNotExist:
                pass
        return None


class TenantCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new tenant"""
    
    class Meta:
        model = Tenant
        fields = ['name', 'slug', 'legal_name', 'tax_id', 'industry', 'country', 'default_currency']
    
    def create(self, validated_data):
        """Create tenant and add current user as owner"""
        request = self.context.get('request')
        tenant = Tenant.objects.create(**validated_data)
        
        # Add creator as owner
        if request and request.user.is_authenticated:
            TenantMembership.objects.create(
                tenant=tenant,
                user=request.user,
                role=TenantRole.OWNER.value,
                accepted_at=timezone.now()
            )
        
        return tenant


class TenantMembershipSerializer(serializers.ModelSerializer):
    """Serializer for tenant membership"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    has_write_access = serializers.ReadOnlyField()
    has_admin_access = serializers.ReadOnlyField()
    
    class Meta:
        model = TenantMembership
        fields = [
            'id', 'tenant', 'tenant_name', 'user', 'user_email', 'user_name',
            'role', 'custom_permissions', 'is_active',
            'has_write_access', 'has_admin_access',
            'invited_at', 'accepted_at', 'created_at'
        ]
        read_only_fields = ['id', 'tenant', 'user', 'invited_at', 'accepted_at', 'created_at']


class TenantInvitationSerializer(serializers.ModelSerializer):
    """Serializer for tenant invitations"""
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)
    is_valid = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = TenantInvitation
        fields = [
            'id', 'tenant', 'tenant_name', 'email', 'role',
            'invited_by', 'invited_by_email',
            'expires_at', 'is_valid', 'is_expired',
            'created_at'
        ]
        read_only_fields = ['id', 'tenant', 'token', 'invited_by', 'expires_at', 'created_at']


class InviteUserSerializer(serializers.Serializer):
    """Serializer for inviting a user to tenant"""
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=TenantRole.choices(), default=TenantRole.VIEWER.value)
    
    def create(self, validated_data):
        """Create invitation"""
        request = self.context.get('request')
        tenant = request.tenant
        
        invitation = TenantInvitation.objects.create(
            tenant=tenant,
            email=validated_data['email'],
            role=validated_data['role'],
            invited_by=request.user,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        return invitation


class AcceptInvitationSerializer(serializers.Serializer):
    """Serializer for accepting an invitation"""
    token = serializers.CharField()
    
    def validate_token(self, value):
        try:
            invitation = TenantInvitation.objects.get(token=value)
            if not invitation.is_valid:
                raise serializers.ValidationError("This invitation has expired or already been used.")
            return value
        except TenantInvitation.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation token.")
    
    def create(self, validated_data):
        """Accept invitation and create membership"""
        request = self.context.get('request')
        invitation = TenantInvitation.objects.get(token=validated_data['token'])
        
        # Create or update membership
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
        
        # Mark invitation as accepted
        invitation.accepted_at = timezone.now()
        invitation.save()
        
        return membership
