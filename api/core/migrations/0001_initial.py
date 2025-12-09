# Generated manually for tenant models

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Tenant',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Company/Organization name', max_length=200)),
                ('slug', models.SlugField(help_text='URL-friendly identifier', max_length=100, unique=True)),
                ('legal_name', models.CharField(blank=True, max_length=300)),
                ('tax_id', models.CharField(blank=True, help_text='VAT/GST/Tax ID', max_length=50)),
                ('industry', models.CharField(blank=True, max_length=100)),
                ('address_line1', models.CharField(blank=True, max_length=200)),
                ('address_line2', models.CharField(blank=True, max_length=200)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('state', models.CharField(blank=True, max_length=100)),
                ('postal_code', models.CharField(blank=True, max_length=20)),
                ('country', models.CharField(default='HK', max_length=100)),
                ('phone', models.CharField(blank=True, max_length=50)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('website', models.URLField(blank=True)),
                ('default_currency', models.CharField(default='HKD', max_length=3)),
                ('fiscal_year_start_month', models.PositiveSmallIntegerField(default=1, help_text='1=January')),
                ('timezone', models.CharField(default='Asia/Hong_Kong', max_length=50)),
                ('subscription_plan', models.CharField(choices=[('free', 'Free'), ('starter', 'Starter'), ('professional', 'Professional'), ('enterprise', 'Enterprise')], default='free', max_length=50)),
                ('subscription_status', models.CharField(choices=[('active', 'Active'), ('trial', 'Trial'), ('suspended', 'Suspended'), ('cancelled', 'Cancelled')], default='active', max_length=20)),
                ('max_users', models.PositiveIntegerField(default=3, help_text='Max users for plan')),
                ('logo_url', models.URLField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Tenant',
                'verbose_name_plural': 'Tenants',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='TenantMembership',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('role', models.CharField(choices=[('OWNER', 'OWNER'), ('ADMIN', 'ADMIN'), ('ACCOUNTANT', 'ACCOUNTANT'), ('VIEWER', 'VIEWER')], default='VIEWER', max_length=20)),
                ('custom_permissions', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('invited_at', models.DateTimeField(auto_now_add=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('invited_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invitations_sent', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='core.tenant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tenant_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Tenant Membership',
                'verbose_name_plural': 'Tenant Memberships',
                'ordering': ['tenant', '-role', 'user__email'],
                'unique_together': {('tenant', 'user')},
            },
        ),
        migrations.CreateModel(
            name='TenantInvitation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=254)),
                ('role', models.CharField(choices=[('OWNER', 'OWNER'), ('ADMIN', 'ADMIN'), ('ACCOUNTANT', 'ACCOUNTANT'), ('VIEWER', 'VIEWER')], default='VIEWER', max_length=20)),
                ('token', models.CharField(max_length=100, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('invited_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tenant_invitations_created', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='core.tenant')),
            ],
            options={
                'verbose_name': 'Tenant Invitation',
                'verbose_name_plural': 'Tenant Invitations',
                'ordering': ['-created_at'],
            },
        ),
    ]
