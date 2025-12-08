"""
Seed tenant demo data for the Wisematic ERP system.
This command creates sample tenant data for testing multi-tenant functionality.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import uuid

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed tenant demo data for testing multi-tenant functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing tenant data before seeding',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from core.tenants.models import Tenant, TenantMembership, TenantInvitation, TenantRole
        
        if options['clear']:
            self.stdout.write('Clearing existing tenant data...')
            TenantInvitation.objects.all().delete()
            TenantMembership.objects.all().delete()
            Tenant.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing tenant data cleared.'))
        
        self.stdout.write('Seeding tenant data...\n')
        
        # Create demo tenants
        tenants = self._create_tenants()
        
        # Create demo users if not exist
        users = self._create_users()
        
        # Create tenant memberships
        self._create_memberships(tenants, users)
        
        # Create sample invitations
        self._create_invitations(tenants, users)
        
        # Migrate existing accounting data to first tenant
        self._migrate_accounting_data(tenants)
        
        self.stdout.write(self.style.SUCCESS('\n✅ Tenant demo data seeded successfully!'))

    def _create_tenants(self):
        """Create demo tenants"""
        from core.tenants.models import Tenant
        
        self.stdout.write('Creating demo tenants...')
        
        demo_tenants = [
            {
                'name': 'Wisematic Corp',
                'slug': 'wisematic',
                'subscription_plan': 'ENTERPRISE',
                'settings': {
                    'default_currency': 'TWD',
                    'fiscal_year_start_month': 1,
                    'timezone': 'Asia/Taipei',
                    'language': 'zh-TW',
                },
                'contact_email': 'admin@wisematic.com',
                'contact_phone': '+886-2-1234-5678',
                'address': '台北市信義區信義路五段7號',
            },
            {
                'name': 'TechStart Inc',
                'slug': 'techstart',
                'subscription_plan': 'PROFESSIONAL',
                'settings': {
                    'default_currency': 'USD',
                    'fiscal_year_start_month': 1,
                    'timezone': 'America/Los_Angeles',
                    'language': 'en',
                },
                'contact_email': 'admin@techstart.io',
                'contact_phone': '+1-555-1234',
                'address': '123 Tech Blvd, San Francisco, CA 94107',
            },
            {
                'name': '東方會計事務所',
                'slug': 'dongfang-cpa',
                'subscription_plan': 'PROFESSIONAL',
                'settings': {
                    'default_currency': 'TWD',
                    'fiscal_year_start_month': 1,
                    'timezone': 'Asia/Taipei',
                    'language': 'zh-TW',
                },
                'contact_email': 'contact@dongfang-cpa.tw',
                'contact_phone': '+886-2-8765-4321',
                'address': '台北市大安區敦化南路一段100號',
            },
            {
                'name': 'Demo Startup',
                'slug': 'demo-startup',
                'subscription_plan': 'STARTER',
                'settings': {
                    'default_currency': 'TWD',
                    'fiscal_year_start_month': 7,
                    'timezone': 'Asia/Taipei',
                    'language': 'zh-TW',
                },
                'contact_email': 'hello@demo-startup.com',
                'contact_phone': '+886-9-1234-5678',
                'address': '新北市板橋區中山路一段200號',
            },
        ]
        
        tenants = []
        for tenant_data in demo_tenants:
            tenant, created = Tenant.objects.get_or_create(
                slug=tenant_data['slug'],
                defaults=tenant_data
            )
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f'  - {tenant.name} ({status})')
            tenants.append(tenant)
        
        return tenants

    def _create_users(self):
        """Create demo users for tenant testing"""
        self.stdout.write('Creating demo users...')
        
        demo_users = [
            {
                'email': 'owner@wisematic.com',
                'full_name': '王大明',
                'is_staff': True,
                'is_superuser': True,
                'role': 'ADMIN',
            },
            {
                'email': 'admin@wisematic.com',
                'full_name': '李小華',
                'is_staff': True,
                'role': 'ADMIN',
            },
            {
                'email': 'accountant@wisematic.com',
                'full_name': '陳會計',
                'is_staff': True,
                'role': 'USER',
            },
            {
                'email': 'viewer@wisematic.com',
                'full_name': '張觀察',
                'is_staff': False,
                'role': 'USER',
            },
            {
                'email': 'owner@techstart.io',
                'full_name': 'John Smith',
                'is_staff': True,
                'role': 'ADMIN',
            },
            {
                'email': 'developer@techstart.io',
                'full_name': 'Jane Developer',
                'is_staff': False,
                'role': 'USER',
            },
            {
                'email': 'multi-tenant@example.com',
                'full_name': '多租戶測試',
                'is_staff': True,
                'role': 'USER',
            },
        ]
        
        users = []
        for user_data in demo_users:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'full_name': user_data.get('full_name', ''),
                    'is_staff': user_data.get('is_staff', False),
                    'is_superuser': user_data.get('is_superuser', False),
                    'role': user_data.get('role', 'USER'),
                    'email_verified': True,
                }
            )
            if created:
                user.set_password('demo1234')
                user.save()
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f'  - {user.email} ({status})')
            users.append(user)
        
        return users

    def _create_memberships(self, tenants, users):
        """Create tenant memberships"""
        from core.tenants.models import TenantMembership, TenantRole
        
        self.stdout.write('Creating tenant memberships...')
        
        # Get users by email for easier reference
        user_map = {u.email: u for u in users}
        tenant_map = {t.slug: t for t in tenants}
        
        memberships_data = [
            # Wisematic Corp
            {'tenant': 'wisematic', 'user': 'owner@wisematic.com', 'role': TenantRole.OWNER},
            {'tenant': 'wisematic', 'user': 'admin@wisematic.com', 'role': TenantRole.ADMIN},
            {'tenant': 'wisematic', 'user': 'accountant@wisematic.com', 'role': TenantRole.ACCOUNTANT},
            {'tenant': 'wisematic', 'user': 'viewer@wisematic.com', 'role': TenantRole.VIEWER},
            {'tenant': 'wisematic', 'user': 'multi-tenant@example.com', 'role': TenantRole.ACCOUNTANT},
            
            # TechStart Inc
            {'tenant': 'techstart', 'user': 'owner@techstart.io', 'role': TenantRole.OWNER},
            {'tenant': 'techstart', 'user': 'developer@techstart.io', 'role': TenantRole.VIEWER},
            {'tenant': 'techstart', 'user': 'multi-tenant@example.com', 'role': TenantRole.ADMIN},
            
            # 東方會計事務所
            {'tenant': 'dongfang-cpa', 'user': 'admin@wisematic.com', 'role': TenantRole.OWNER},
            {'tenant': 'dongfang-cpa', 'user': 'accountant@wisematic.com', 'role': TenantRole.ACCOUNTANT},
            
            # Demo Startup
            {'tenant': 'demo-startup', 'user': 'multi-tenant@example.com', 'role': TenantRole.OWNER},
        ]
        
        for membership_data in memberships_data:
            tenant = tenant_map.get(membership_data['tenant'])
            user = user_map.get(membership_data['user'])
            
            if tenant and user:
                membership, created = TenantMembership.objects.get_or_create(
                    tenant=tenant,
                    user=user,
                    defaults={'role': membership_data['role'].value}
                )
                status = 'Created' if created else 'Already exists'
                self.stdout.write(f'  - {user.email} → {tenant.name} ({membership_data["role"].value}) ({status})')

    def _create_invitations(self, tenants, users):
        """Create sample pending invitations"""
        from core.tenants.models import TenantInvitation, TenantRole
        
        self.stdout.write('Creating sample invitations...')
        
        tenant_map = {t.slug: t for t in tenants}
        user_map = {u.email: u for u in users}
        
        invitations_data = [
            {
                'tenant': 'wisematic',
                'email': 'newemployee@example.com',
                'role': TenantRole.ACCOUNTANT,
                'invited_by': 'owner@wisematic.com',
            },
            {
                'tenant': 'techstart',
                'email': 'contractor@example.com',
                'role': TenantRole.VIEWER,
                'invited_by': 'owner@techstart.io',
            },
        ]
        
        for inv_data in invitations_data:
            tenant = tenant_map.get(inv_data['tenant'])
            invited_by = user_map.get(inv_data['invited_by'])
            
            if tenant and invited_by:
                invitation, created = TenantInvitation.objects.get_or_create(
                    tenant=tenant,
                    email=inv_data['email'],
                    defaults={
                        'role': inv_data['role'].value,
                        'invited_by': invited_by,
                        'token': str(uuid.uuid4()),
                        'expires_at': timezone.now() + timedelta(days=7),
                    }
                )
                status = 'Created' if created else 'Already exists'
                self.stdout.write(f'  - {inv_data["email"]} → {tenant.name} ({status})')

    def _migrate_accounting_data(self, tenants):
        """Migrate existing accounting data to the first tenant"""
        self.stdout.write('Migrating existing accounting data to default tenant...')
        
        if not tenants:
            self.stdout.write(self.style.WARNING('  No tenants available, skipping migration.'))
            return
        
        default_tenant = tenants[0]  # Wisematic Corp
        
        # Import all accounting models
        try:
            from accounting.models import (
                FiscalYear, AccountingPeriod, Currency, TaxRate,
                Account, JournalEntry, Contact, Invoice, Payment,
                Expense, BankStatement, BankTransaction, APIKeyStore
            )
            
            models_to_migrate = [
                (FiscalYear, 'fiscal_years'),
                (AccountingPeriod, 'accounting_periods'),
                (Currency, 'currencies'),
                (TaxRate, 'tax_rates'),
                (Account, 'accounts'),
                (JournalEntry, 'journal_entries'),
                (Contact, 'contacts'),
                (Invoice, 'invoices'),
                (Payment, 'payments'),
                (Expense, 'expenses'),
                (BankStatement, 'bank_statements'),
                (BankTransaction, 'bank_transactions'),
                (APIKeyStore, 'api_keys'),
            ]
            
            for model, label in models_to_migrate:
                try:
                    # Use all_objects to bypass tenant filtering
                    count = model.all_objects.filter(tenant__isnull=True).update(tenant=default_tenant)
                    if count > 0:
                        self.stdout.write(f'  - Migrated {count} {label} to {default_tenant.name}')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  - Could not migrate {label}: {str(e)}'))
            
            self.stdout.write(self.style.SUCCESS(f'  Accounting data migration complete.'))
            
        except ImportError as e:
            self.stdout.write(self.style.WARNING(f'  Could not import accounting models: {str(e)}'))
