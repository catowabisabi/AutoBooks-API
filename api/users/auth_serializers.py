"""
Auth Serializers
================
Serializers for sign-up, forgot-password, account-lock flows.
"""

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .auth_models import (
    PasswordResetToken,
    EmailVerificationToken,
    AccountLock,
    LoginAttempt
)

User = get_user_model()


class SignUpSerializer(serializers.Serializer):
    """
    用戶註冊序列化器
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    full_name = serializers.CharField(max_length=255)
    language = serializers.ChoiceField(choices=[('en', 'English'), ('zh-TW', '繁體中文'), ('zh-CN', '简体中文')], default='en')
    
    # Optional tenant creation
    create_tenant = serializers.BooleanField(default=True, required=False)
    company_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    
    def validate_email(self, value):
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(_("A user with this email already exists."))
        return email
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': _("Passwords do not match.")
            })
        
        # Validate password strength
        validate_password(data['password'])
        
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        create_tenant = validated_data.pop('create_tenant', True)
        company_name = validated_data.pop('company_name', '')
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            language=validated_data.get('language', 'en'),
            is_active=True  # Consider email verification first
        )
        
        # Create tenant if requested
        if create_tenant:
            from core.tenants.models import Tenant, TenantMembership, TenantRole
            from django.utils.text import slugify
            
            tenant_name = company_name or f"{user.full_name}'s Organization"
            base_slug = slugify(tenant_name)[:50]
            slug = base_slug
            counter = 1
            while Tenant.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            tenant = Tenant.objects.create(
                name=tenant_name,
                slug=slug
            )
            
            TenantMembership.objects.create(
                tenant=tenant,
                user=user,
                role=TenantRole.OWNER.value,
                accepted_at=timezone.now()
            )
        
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    """
    忘記密碼請求序列化器
    """
    email = serializers.EmailField()
    
    def validate_email(self, value):
        email = value.lower()
        try:
            user = User.objects.get(email=email, is_active=True)
            self.user = user
        except User.DoesNotExist:
            # Don't reveal if user exists
            self.user = None
        return email
    
    def create(self, validated_data):
        if self.user:
            request = self.context.get('request')
            ip_address = None
            user_agent = ''
            
            if request:
                ip_address = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            token = PasswordResetToken.create_for_user(
                self.user,
                ip_address=ip_address,
                user_agent=user_agent
            )
            return token
        return None


class ResetPasswordSerializer(serializers.Serializer):
    """
    密碼重設序列化器
    """
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    def validate_token(self, value):
        try:
            token = PasswordResetToken.objects.get(token=value)
            if not token.is_valid:
                raise serializers.ValidationError(_("This reset link has expired or already been used."))
            self.reset_token = token
            return value
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError(_("Invalid reset token."))
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': _("Passwords do not match.")
            })
        validate_password(data['password'])
        return data
    
    def create(self, validated_data):
        user = self.reset_token.user
        user.set_password(validated_data['password'])
        user.save()
        
        self.reset_token.use()
        
        # Unlock account if locked due to failed attempts
        AccountLock.objects.filter(
            user=user,
            reason='too_many_attempts',
            unlocked_at__isnull=True
        ).update(unlocked_at=timezone.now())
        
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """
    更改密碼序列化器 (需登入)
    """
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_current_password(self, value):
        user = self.context.get('request').user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Current password is incorrect."))
        return value
    
    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': _("Passwords do not match.")
            })
        validate_password(data['new_password'])
        return data
    
    def create(self, validated_data):
        user = self.context.get('request').user
        user.set_password(validated_data['new_password'])
        user.save()
        return user


class AccountLockSerializer(serializers.ModelSerializer):
    """
    帳號鎖定序列化器
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = AccountLock
        fields = [
            'id', 'user', 'user_email', 'reason', 'locked_at',
            'locked_until', 'unlocked_at', 'is_active', 'notes'
        ]
        read_only_fields = ['id', 'locked_at', 'unlocked_at']
    
    @extend_schema_field(serializers.BooleanField())
    def get_is_active(self, obj):
        return obj.is_active


class LockAccountSerializer(serializers.Serializer):
    """
    鎖定帳號請求序列化器 (管理員用)
    """
    user_id = serializers.UUIDField()
    reason = serializers.ChoiceField(choices=AccountLock.LOCK_REASONS)
    duration_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
            self.target_user = user
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(_("User not found."))
    
    def create(self, validated_data):
        request = self.context.get('request')
        ip_address = request.META.get('REMOTE_ADDR') if request else None
        
        lock = AccountLock.lock_user(
            user=self.target_user,
            reason=validated_data['reason'],
            duration_minutes=validated_data.get('duration_minutes'),
            ip_address=ip_address,
            notes=validated_data.get('notes', '')
        )
        return lock


class UnlockAccountSerializer(serializers.Serializer):
    """
    解鎖帳號請求序列化器 (管理員用)
    """
    user_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
            lock = AccountLock.get_active_lock(user)
            if not lock:
                raise serializers.ValidationError(_("User is not locked."))
            self.target_user = user
            self.active_lock = lock
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError(_("User not found."))
    
    def create(self, validated_data):
        request = self.context.get('request')
        unlocked_by = request.user if request and request.user.is_authenticated else None
        
        self.active_lock.unlock(
            unlocked_by=unlocked_by,
            notes=validated_data.get('notes', '')
        )
        return self.active_lock


class LoginAttemptSerializer(serializers.ModelSerializer):
    """
    登入嘗試記錄序列化器
    """
    class Meta:
        model = LoginAttempt
        fields = ['id', 'email', 'ip_address', 'success', 'failure_reason', 'created_at']
        read_only_fields = ['id', 'created_at']
