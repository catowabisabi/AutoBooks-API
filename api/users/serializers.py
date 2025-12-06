from rest_framework import serializers
from .models import User, UserSettings


# serializers.py - Keep only these
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role', 'is_active', 'phone', 'avatar_url', 'timezone', 'language']
        read_only_fields = ['id', 'email']


class UserProfileSerializer(serializers.ModelSerializer):
    """For updating user profile"""
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone', 'avatar_url', 'timezone', 'language', 'role', 'is_active']
        read_only_fields = ['id', 'email', 'role', 'is_active']


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = [
            'id',
            # Notification Settings
            'email_notifications', 'push_notifications', 'sms_notifications',
            'notify_task_assigned', 'notify_task_completed', 'notify_invoice_received',
            'notify_payment_due', 'notify_system_updates', 'notify_security_alerts',
            'notify_weekly_digest', 'notify_monthly_report',
            # Billing Settings
            'billing_email', 'billing_address', 'billing_city', 'billing_country',
            'billing_postal_code', 'company_name', 'tax_id',
            # Subscription
            'subscription_plan', 'subscription_status', 'subscription_start_date', 'subscription_end_date',
            # Payment
            'payment_method_type', 'payment_method_last_four', 'payment_method_expiry',
        ]
        read_only_fields = ['id', 'subscription_status', 'subscription_start_date', 'subscription_end_date']


class AdminCreateUserSerializer(serializers.ModelSerializer):
    """For admin to create users"""
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'password', 'role']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        # Create default settings for new user
        UserSettings.objects.create(user=user)
        return user
