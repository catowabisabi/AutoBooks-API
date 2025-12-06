from rest_framework import serializers
from .models import User, UserSettings, SubscriptionPlan, UserSubscription


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


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Subscription Plan serializer"""
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'plan_type', 'name', 'name_en', 'name_zh',
            'description', 'description_en', 'description_zh',
            'price_monthly', 'price_yearly', 'currency',
            'max_users', 'max_companies', 'max_storage_gb', 'max_documents',
            'max_invoices_monthly', 'max_employees', 'max_projects',
            'has_ai_assistant', 'has_advanced_analytics', 'has_custom_reports',
            'has_api_access', 'has_priority_support', 'has_sso',
            'has_audit_logs', 'has_data_export', 'has_multi_currency', 'has_custom_branding',
            'ai_queries_monthly', 'rag_documents',
            'is_active', 'is_popular', 'sort_order', 'features'
        ]
    
    def get_features(self, obj):
        """Return list of features for display"""
        features = []
        lang = self.context.get('request', {})
        if hasattr(lang, 'headers'):
            lang = lang.headers.get('Accept-Language', 'en')[:2]
        else:
            lang = 'en'
        
        # User/Company limits
        if obj.max_users == 0:
            features.append({'key': 'users', 'en': 'Unlimited users', 'zh': '無限用戶'})
        else:
            features.append({'key': 'users', 'en': f'Up to {obj.max_users} users', 'zh': f'最多 {obj.max_users} 位用戶'})
        
        if obj.max_companies == 0:
            features.append({'key': 'companies', 'en': 'Unlimited companies', 'zh': '無限公司'})
        else:
            features.append({'key': 'companies', 'en': f'{obj.max_companies} companies', 'zh': f'{obj.max_companies} 間公司'})
        
        # Storage
        features.append({'key': 'storage', 'en': f'{obj.max_storage_gb} GB storage', 'zh': f'{obj.max_storage_gb} GB 儲存空間'})
        
        # Feature flags
        if obj.has_ai_assistant:
            features.append({'key': 'ai', 'en': 'AI Assistant', 'zh': 'AI 助理'})
        if obj.has_advanced_analytics:
            features.append({'key': 'analytics', 'en': 'Advanced Analytics', 'zh': '進階分析'})
        if obj.has_custom_reports:
            features.append({'key': 'reports', 'en': 'Custom Reports', 'zh': '自訂報表'})
        if obj.has_api_access:
            features.append({'key': 'api', 'en': 'API Access', 'zh': 'API 存取'})
        if obj.has_priority_support:
            features.append({'key': 'support', 'en': 'Priority Support', 'zh': '優先支援'})
        if obj.has_sso:
            features.append({'key': 'sso', 'en': 'Single Sign-On (SSO)', 'zh': '單一登入 (SSO)'})
        if obj.has_audit_logs:
            features.append({'key': 'audit', 'en': 'Audit Logs', 'zh': '稽核日誌'})
        if obj.has_multi_currency:
            features.append({'key': 'currency', 'en': 'Multi-Currency', 'zh': '多幣別支援'})
        if obj.has_custom_branding:
            features.append({'key': 'branding', 'en': 'Custom Branding', 'zh': '自訂品牌'})
        
        return features


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """User Subscription serializer"""
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        write_only=True,
        source='plan'
    )
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan', 'plan_id', 'status', 'billing_cycle',
            'start_date', 'end_date', 'trial_end_date', 'next_billing_date',
            'cancelled_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'start_date', 'cancelled_at', 'created_at', 'updated_at']


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


class UserRegistrationSerializer(serializers.ModelSerializer):
    """For public user registration"""
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['email', 'full_name', 'password']
        
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        # Create default settings
        UserSettings.objects.create(user=user)
        return user
