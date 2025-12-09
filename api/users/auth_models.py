"""
Extended Auth Models
====================
Password reset tokens, account lock tracking, email verification.
"""

import secrets
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone

from core.models import BaseModel


class PasswordResetToken(BaseModel):
    """
    密碼重設令牌
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'
    
    def __str__(self):
        return f"Reset token for {self.user.email}"
    
    @classmethod
    def create_for_user(cls, user, ip_address=None, user_agent=''):
        """Create a new password reset token"""
        # Invalidate existing tokens
        cls.objects.filter(user=user, used_at__isnull=True).update(
            used_at=timezone.now()
        )
        
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(hours=24),
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @property
    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at
    
    def use(self):
        """Mark token as used"""
        self.used_at = timezone.now()
        self.save()


class EmailVerificationToken(BaseModel):
    """
    郵件驗證令牌
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verification_tokens'
    )
    email = models.EmailField()  # Email to verify (may differ from current)
    token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Email Verification Token'
        verbose_name_plural = 'Email Verification Tokens'
    
    def __str__(self):
        return f"Verification for {self.email}"
    
    @classmethod
    def create_for_user(cls, user, email=None):
        """Create a new email verification token"""
        email = email or user.email
        
        return cls.objects.create(
            user=user,
            email=email,
            token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timedelta(days=7)
        )
    
    @property
    def is_valid(self):
        return self.verified_at is None and timezone.now() < self.expires_at
    
    def verify(self):
        """Mark email as verified"""
        self.verified_at = timezone.now()
        self.save()


class LoginAttempt(BaseModel):
    """
    登入嘗試記錄 (用於帳號鎖定)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='login_attempts',
        null=True,
        blank=True
    )
    email = models.EmailField()  # Store email even if user not found
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Login Attempt'
        verbose_name_plural = 'Login Attempts'
    
    def __str__(self):
        status = '✓' if self.success else '✗'
        return f"{status} {self.email} @ {self.created_at}"

    def __init__(self, *args, **kwargs):
        # Accept legacy kwarg used in tests
        was_successful = kwargs.pop('was_successful', None)
        super().__init__(*args, **kwargs)
        if was_successful is not None:
            self.success = was_successful


class AccountLock(BaseModel):
    """
    帳號鎖定記錄
    """
    LOCK_REASONS = [
        ('too_many_attempts', 'Too many failed login attempts'),
        ('admin_action', 'Locked by administrator'),
        ('suspicious_activity', 'Suspicious activity detected'),
        ('user_request', 'User requested lock'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='account_locks'
    )
    reason = models.CharField(max_length=50, choices=LOCK_REASONS)
    locked_at = models.DateTimeField(auto_now_add=True)
    locked_until = models.DateTimeField(null=True, blank=True)  # null = permanent
    unlocked_at = models.DateTimeField(null=True, blank=True)
    unlocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='account_unlocks'
    )
    notes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-locked_at']
        verbose_name = 'Account Lock'
        verbose_name_plural = 'Account Locks'
    
    def __str__(self):
        return f"Lock on {self.user.email} ({self.reason})"
    
    @property
    def is_active(self):
        """Check if lock is currently active"""
        if self.unlocked_at:
            return False
        if self.locked_until and timezone.now() > self.locked_until:
            return False
        return True
    
    def unlock(self, unlocked_by=None, notes=''):
        """Unlock the account"""
        self.unlocked_at = timezone.now()
        self.unlocked_by = unlocked_by
        if notes:
            self.notes = f"{self.notes}\nUnlock note: {notes}".strip()
        self.save()
    
    @classmethod
    def lock_user(cls, user, reason, duration_minutes=None, ip_address=None, notes=''):
        """Lock a user's account"""
        locked_until = None
        if duration_minutes:
            locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        
        return cls.objects.create(
            user=user,
            reason=reason,
            locked_until=locked_until,
            ip_address=ip_address,
            notes=notes
        )
    
    @classmethod
    def is_user_locked(cls, user):
        """Check if user has any active locks"""
        return cls.objects.filter(
            user=user,
            unlocked_at__isnull=True
        ).filter(
            models.Q(locked_until__isnull=True) | models.Q(locked_until__gt=timezone.now())
        ).exists()
    
    @classmethod
    def get_active_lock(cls, user):
        """Get current active lock for user"""
        return cls.objects.filter(
            user=user,
            unlocked_at__isnull=True
        ).filter(
            models.Q(locked_until__isnull=True) | models.Q(locked_until__gt=timezone.now())
        ).first()
