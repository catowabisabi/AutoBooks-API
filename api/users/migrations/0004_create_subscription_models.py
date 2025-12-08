# Generated manually to fix migration dependency
import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_avatar_url_user_language_user_phone_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('name', models.CharField(max_length=100)),
                ('name_en', models.CharField(help_text='English name', max_length=100)),
                ('name_zh', models.CharField(help_text='Chinese name', max_length=100)),
                ('plan_type', models.CharField(
                    choices=[('free', 'Free'), ('pro', 'Pro'), ('pro_plus', 'Pro+ Enterprise')],
                    max_length=20,
                    unique=True
                )),
                ('description', models.TextField(blank=True)),
                ('description_en', models.TextField(blank=True, help_text='English description')),
                ('description_zh', models.TextField(blank=True, help_text='Chinese description')),
                ('price_monthly', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('price_yearly', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('currency', models.CharField(default='USD', max_length=3)),
                ('max_users', models.IntegerField(default=1, help_text='Maximum number of users')),
                ('max_companies', models.IntegerField(default=1, help_text='Maximum number of companies')),
                ('max_storage_gb', models.IntegerField(default=1, help_text='Maximum storage in GB')),
                ('max_documents', models.IntegerField(default=100, help_text='Maximum number of documents')),
                ('max_invoices_monthly', models.IntegerField(default=10, help_text='Maximum invoices per month')),
                ('max_employees', models.IntegerField(default=5, help_text='Maximum employees in HRMS')),
                ('max_projects', models.IntegerField(default=3, help_text='Maximum active projects')),
                ('has_ai_assistant', models.BooleanField(default=False)),
                ('has_advanced_analytics', models.BooleanField(default=False)),
                ('has_custom_reports', models.BooleanField(default=False)),
                ('has_api_access', models.BooleanField(default=False)),
                ('has_priority_support', models.BooleanField(default=False)),
                ('has_sso', models.BooleanField(default=False, help_text='Single Sign-On')),
                ('has_audit_logs', models.BooleanField(default=False)),
                ('has_data_export', models.BooleanField(default=True)),
                ('has_multi_currency', models.BooleanField(default=False)),
                ('has_custom_branding', models.BooleanField(default=False)),
                ('ai_queries_monthly', models.IntegerField(default=0, help_text='AI queries per month (0=unlimited)')),
                ('rag_documents', models.IntegerField(default=0, help_text='RAG knowledge base documents')),
                ('is_popular', models.BooleanField(default=False, help_text='Show as popular/recommended')),
                ('sort_order', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Subscription Plan',
                'verbose_name_plural': 'Subscription Plans',
                'ordering': ['sort_order', 'price_monthly'],
            },
        ),
        migrations.CreateModel(
            name='UserSubscription',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('status', models.CharField(
                    choices=[
                        ('active', 'Active'),
                        ('cancelled', 'Cancelled'),
                        ('expired', 'Expired'),
                        ('trial', 'Trial'),
                        ('past_due', 'Past Due')
                    ],
                    default='trial',
                    max_length=20
                )),
                ('billing_cycle', models.CharField(
                    choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')],
                    default='monthly',
                    max_length=10
                )),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('trial_end_date', models.DateField(blank=True, null=True)),
                ('next_billing_date', models.DateField(blank=True, null=True)),
                ('cancelled_at', models.DateTimeField(blank=True, null=True)),
                ('stripe_subscription_id', models.CharField(blank=True, max_length=100, null=True)),
                ('stripe_customer_id', models.CharField(blank=True, max_length=100, null=True)),
                ('plan', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='subscriptions',
                    to='users.subscriptionplan'
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subscription',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'User Subscription',
                'verbose_name_plural': 'User Subscriptions',
            },
        ),
    ]
