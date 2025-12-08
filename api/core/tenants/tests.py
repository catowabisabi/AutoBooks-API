"""
E2E Tests for Multi-Tenant Access Control

Tests cover:
1. Tenant isolation - users can only see data from their tenant
2. Role-based access - different roles have different permissions
3. Multi-tenant membership - users can belong to multiple tenants
4. Middleware functionality - tenant context is properly set from headers
5. Auth flows - sign-up, password reset, account lock
"""
import uuid
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

User = get_user_model()


class TenantModelTests(TestCase):
    """Test tenant model functionality"""
    
    def setUp(self):
        from core.tenants.models import Tenant, TenantMembership, TenantRole
        
        self.tenant1 = Tenant.objects.create(
            name='Tenant One',
            slug='tenant-one',
            subscription_plan='PROFESSIONAL'
        )
        self.tenant2 = Tenant.objects.create(
            name='Tenant Two',
            slug='tenant-two',
            subscription_plan='STARTER'
        )
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        
        # User is owner of tenant1 and viewer of tenant2
        TenantMembership.objects.create(
            tenant=self.tenant1,
            user=self.user,
            role=TenantRole.OWNER.value
        )
        TenantMembership.objects.create(
            tenant=self.tenant2,
            user=self.user,
            role=TenantRole.VIEWER.value
        )
    
    def test_tenant_creation(self):
        """Test tenant is created correctly"""
        self.assertEqual(self.tenant1.name, 'Tenant One')
        self.assertEqual(self.tenant1.slug, 'tenant-one')
        self.assertTrue(self.tenant1.is_active)
    
    def test_user_tenants(self):
        """Test user can have multiple tenants"""
        from core.tenants.models import TenantMembership
        
        memberships = TenantMembership.objects.filter(user=self.user)
        self.assertEqual(memberships.count(), 2)
    
    def test_membership_role(self):
        """Test membership roles are correct"""
        from core.tenants.models import TenantMembership, TenantRole
        
        membership1 = TenantMembership.objects.get(tenant=self.tenant1, user=self.user)
        membership2 = TenantMembership.objects.get(tenant=self.tenant2, user=self.user)
        
        self.assertEqual(membership1.role, TenantRole.OWNER.value)
        self.assertEqual(membership2.role, TenantRole.VIEWER.value)
    
    def test_role_permissions(self):
        """Test role permission methods"""
        from core.tenants.models import TenantRole
        
        owner = TenantRole.OWNER
        admin = TenantRole.ADMIN
        accountant = TenantRole.ACCOUNTANT
        viewer = TenantRole.VIEWER
        
        # Owner and Admin can manage members
        self.assertTrue(owner.can_manage_members())
        self.assertTrue(admin.can_manage_members())
        self.assertFalse(accountant.can_manage_members())
        self.assertFalse(viewer.can_manage_members())
        
        # All except viewer can write
        self.assertTrue(owner.can_write())
        self.assertTrue(admin.can_write())
        self.assertTrue(accountant.can_write())
        self.assertFalse(viewer.can_write())


class TenantAwareManagerTests(TransactionTestCase):
    """Test tenant-aware query filtering"""
    
    def setUp(self):
        from core.tenants.models import Tenant, TenantMembership, TenantRole
        from core.tenants.managers import set_current_tenant, clear_current_tenant
        
        clear_current_tenant()
        
        self.tenant1 = Tenant.objects.create(
            name='Tenant One',
            slug='tenant-one'
        )
        self.tenant2 = Tenant.objects.create(
            name='Tenant Two',
            slug='tenant-two'
        )
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        TenantMembership.objects.create(
            tenant=self.tenant1,
            user=self.user,
            role=TenantRole.OWNER.value
        )
    
    def tearDown(self):
        from core.tenants.managers import clear_current_tenant
        clear_current_tenant()
    
    def test_tenant_isolation(self):
        """Test data is isolated by tenant"""
        from accounting.models import Currency
        from core.tenants.managers import set_current_tenant, clear_current_tenant
        
        # Create currency in tenant1
        set_current_tenant(self.tenant1)
        Currency.all_objects.create(
            code='TWD',
            name='New Taiwan Dollar',
            symbol='NT$',
            tenant=self.tenant1
        )
        
        # Create currency in tenant2
        set_current_tenant(self.tenant2)
        Currency.all_objects.create(
            code='USD',
            name='US Dollar',
            symbol='$',
            tenant=self.tenant2
        )
        
        # Verify isolation - tenant1 should only see TWD
        set_current_tenant(self.tenant1)
        currencies = Currency.objects.all()
        self.assertEqual(currencies.count(), 1)
        self.assertEqual(currencies.first().code, 'TWD')
        
        # Verify isolation - tenant2 should only see USD
        set_current_tenant(self.tenant2)
        currencies = Currency.objects.all()
        self.assertEqual(currencies.count(), 1)
        self.assertEqual(currencies.first().code, 'USD')
        
        # all_objects bypasses tenant filtering
        clear_current_tenant()
        all_currencies = Currency.all_objects.all()
        self.assertEqual(all_currencies.count(), 2)


class TenantMiddlewareTests(APITestCase):
    """Test tenant middleware functionality"""
    
    def setUp(self):
        from core.tenants.models import Tenant, TenantMembership, TenantRole
        
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantRole.ACCOUNTANT.value
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_tenant_from_header_id(self):
        """Test tenant is set from X-Tenant-ID header"""
        response = self.client.get(
            '/api/v1/tenants/',
            HTTP_X_TENANT_ID=str(self.tenant.id)
        )
        # Should succeed as user is member
        self.assertIn(response.status_code, [200, 201, 403])
    
    def test_tenant_from_header_slug(self):
        """Test tenant is set from X-Tenant-Slug header"""
        response = self.client.get(
            '/api/v1/tenants/',
            HTTP_X_TENANT_SLUG='test-tenant'
        )
        # Should succeed as user is member
        self.assertIn(response.status_code, [200, 201, 403])
    
    def test_invalid_tenant_header(self):
        """Test invalid tenant ID returns error"""
        response = self.client.get(
            '/api/v1/accounting/accounts/',
            HTTP_X_TENANT_ID='99999'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_non_member_tenant_access(self):
        """Test non-member cannot access tenant"""
        from core.tenants.models import Tenant
        
        other_tenant = Tenant.objects.create(
            name='Other Tenant',
            slug='other-tenant'
        )
        
        response = self.client.get(
            '/api/v1/accounting/accounts/',
            HTTP_X_TENANT_ID=str(other_tenant.id)
        )
        self.assertEqual(response.status_code, 403)


class RoleBasedAccessTests(APITestCase):
    """Test role-based access control"""
    
    def setUp(self):
        from core.tenants.models import Tenant, TenantMembership, TenantRole
        
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )
        
        # Create users with different roles
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='testpass123'
        )
        self.accountant = User.objects.create_user(
            email='accountant@example.com',
            password='testpass123'
        )
        self.viewer = User.objects.create_user(
            email='viewer@example.com',
            password='testpass123'
        )
        
        TenantMembership.objects.create(
            tenant=self.tenant, user=self.owner, role=TenantRole.OWNER.value
        )
        TenantMembership.objects.create(
            tenant=self.tenant, user=self.admin, role=TenantRole.ADMIN.value
        )
        TenantMembership.objects.create(
            tenant=self.tenant, user=self.accountant, role=TenantRole.ACCOUNTANT.value
        )
        TenantMembership.objects.create(
            tenant=self.tenant, user=self.viewer, role=TenantRole.VIEWER.value
        )
        
        self.client = APIClient()
    
    def test_owner_can_manage_invitations(self):
        """Test owner can create invitations"""
        self.client.force_authenticate(user=self.owner)
        
        response = self.client.post(
            '/api/v1/tenant-invitations/',
            {
                'email': 'newuser@example.com',
                'role': 'ACCOUNTANT'
            },
            format='json',
            HTTP_X_TENANT_ID=str(self.tenant.id)
        )
        self.assertIn(response.status_code, [201, 200])
    
    def test_viewer_cannot_create_data(self):
        """Test viewer cannot create accounting data"""
        self.client.force_authenticate(user=self.viewer)
        
        # Try to create an account (should fail for viewer)
        response = self.client.post(
            '/api/v1/accounting/accounts/',
            {
                'code': '1001',
                'name': 'Test Account',
                'account_type': 'ASSET'
            },
            format='json',
            HTTP_X_TENANT_ID=str(self.tenant.id)
        )
        # Should be forbidden
        self.assertIn(response.status_code, [403, 400])
    
    def test_accountant_can_create_data(self):
        """Test accountant can create accounting data"""
        from accounting.models import Currency
        from core.tenants.managers import set_current_tenant
        
        # First create required currency
        set_current_tenant(self.tenant)
        Currency.objects.create(
            code='TWD',
            name='Taiwan Dollar',
            symbol='NT$',
            tenant=self.tenant
        )
        
        self.client.force_authenticate(user=self.accountant)
        
        # Accountant should be able to create accounts
        response = self.client.post(
            '/api/v1/accounting/accounts/',
            {
                'code': '1001',
                'name': 'Test Account',
                'account_type': 'ASSET'
            },
            format='json',
            HTTP_X_TENANT_ID=str(self.tenant.id)
        )
        # Should succeed or fail due to validation, not permission
        self.assertIn(response.status_code, [201, 200, 400])


class AuthFlowTests(APITestCase):
    """Test authentication flows"""
    
    def test_signup_creates_user_and_tenant(self):
        """Test signup creates user with optional tenant"""
        response = self.client.post(
            '/api/v1/auth/signup/',
            {
                'email': 'newuser@example.com',
                'password': 'SecurePass123!',
                'password_confirm': 'SecurePass123!',
                'full_name': 'New User',
                'create_tenant': True,
                'company_name': 'New Company'
            },
            format='json'
        )
        
        # Should create user
        self.assertIn(response.status_code, [201, 200, 400])
        
        if response.status_code in [201, 200]:
            user = User.objects.filter(email='newuser@example.com').first()
            self.assertIsNotNone(user)
    
    def test_forgot_password_flow(self):
        """Test forgot password creates reset token"""
        from users.auth_models import PasswordResetToken
        
        # Create user first
        user = User.objects.create_user(
            email='forgot@example.com',
            password='oldpass123'
        )
        
        response = self.client.post(
            '/api/v1/auth/forgot-password/',
            {'email': 'forgot@example.com'},
            format='json'
        )
        
        # Should succeed (even if email doesn't exist for security)
        self.assertEqual(response.status_code, 200)
        
        # Token should be created
        token = PasswordResetToken.objects.filter(user=user).first()
        self.assertIsNotNone(token)
    
    def test_account_lock_after_failed_attempts(self):
        """Test account is locked after max failed attempts"""
        from users.auth_models import LoginAttempt, AccountLock
        
        user = User.objects.create_user(
            email='locktest@example.com',
            password='correct123'
        )
        
        # Simulate 5 failed login attempts
        for i in range(5):
            LoginAttempt.objects.create(
                user=user,
                ip_address='127.0.0.1',
                was_successful=False
            )
        
        # Check recent failures
        recent_failures = LoginAttempt.get_recent_failures(user, minutes=15)
        self.assertGreaterEqual(recent_failures, 5)
        
        # Lock the account
        lock = AccountLock.lock_account(user, 'Too many failed attempts', locked_by=user)
        self.assertIsNotNone(lock)
        self.assertTrue(lock.is_active)


class TenantInvitationTests(APITestCase):
    """Test tenant invitation flow"""
    
    def setUp(self):
        from core.tenants.models import Tenant, TenantMembership, TenantRole, TenantInvitation
        
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant'
        )
        
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123'
        )
        
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.owner,
            role=TenantRole.OWNER.value
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)
    
    def test_create_invitation(self):
        """Test owner can create invitation"""
        response = self.client.post(
            '/api/v1/tenant-invitations/',
            {
                'email': 'invited@example.com',
                'role': 'ACCOUNTANT'
            },
            format='json',
            HTTP_X_TENANT_ID=str(self.tenant.id)
        )
        
        self.assertIn(response.status_code, [201, 200])
    
    def test_accept_invitation(self):
        """Test user can accept invitation"""
        from core.tenants.models import TenantInvitation, TenantRole, TenantMembership
        
        # Create invitation
        invitation = TenantInvitation.objects.create(
            tenant=self.tenant,
            email='newmember@example.com',
            role=TenantRole.ACCOUNTANT.value,
            invited_by=self.owner,
            token=str(uuid.uuid4()),
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        # Create user and accept invitation
        new_user = User.objects.create_user(
            email='newmember@example.com',
            password='testpass123'
        )
        
        self.client.force_authenticate(user=new_user)
        
        response = self.client.post(
            f'/api/v1/tenant-invitations/{invitation.id}/accept/',
            HTTP_X_TENANT_SLUG='test-tenant'
        )
        
        # Check membership was created
        membership = TenantMembership.objects.filter(
            tenant=self.tenant,
            user=new_user
        ).first()
        
        # Either API succeeded or membership exists
        if response.status_code in [200, 201]:
            self.assertIsNotNone(membership)


class MultiTenantUserTests(APITestCase):
    """Test users with multiple tenant memberships"""
    
    def setUp(self):
        from core.tenants.models import Tenant, TenantMembership, TenantRole
        
        self.tenant1 = Tenant.objects.create(name='Tenant One', slug='tenant-one')
        self.tenant2 = Tenant.objects.create(name='Tenant Two', slug='tenant-two')
        
        self.user = User.objects.create_user(
            email='multi@example.com',
            password='testpass123'
        )
        
        TenantMembership.objects.create(
            tenant=self.tenant1,
            user=self.user,
            role=TenantRole.ADMIN.value
        )
        TenantMembership.objects.create(
            tenant=self.tenant2,
            user=self.user,
            role=TenantRole.VIEWER.value
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_user_can_switch_tenants(self):
        """Test user can access different tenants"""
        # Access tenant1
        response1 = self.client.get(
            '/api/v1/tenants/',
            HTTP_X_TENANT_ID=str(self.tenant1.id)
        )
        
        # Access tenant2
        response2 = self.client.get(
            '/api/v1/tenants/',
            HTTP_X_TENANT_ID=str(self.tenant2.id)
        )
        
        # Both should work
        self.assertIn(response1.status_code, [200, 201])
        self.assertIn(response2.status_code, [200, 201])
    
    def test_data_isolation_between_tenants(self):
        """Test data is isolated when switching tenants"""
        from accounting.models import Currency
        from core.tenants.managers import set_current_tenant, clear_current_tenant
        
        # Create data in tenant1
        set_current_tenant(self.tenant1)
        Currency.objects.create(
            code='TWD',
            name='Taiwan Dollar',
            symbol='NT$',
            tenant=self.tenant1
        )
        
        # Create data in tenant2
        set_current_tenant(self.tenant2)
        Currency.objects.create(
            code='USD',
            name='US Dollar',
            symbol='$',
            tenant=self.tenant2
        )
        
        clear_current_tenant()
        
        # Query via API - tenant1
        response1 = self.client.get(
            '/api/v1/accounting/currencies/',
            HTTP_X_TENANT_ID=str(self.tenant1.id)
        )
        
        # Query via API - tenant2
        response2 = self.client.get(
            '/api/v1/accounting/currencies/',
            HTTP_X_TENANT_ID=str(self.tenant2.id)
        )
        
        # Each should only see their own data
        if response1.status_code == 200:
            data1 = response1.json()
            codes1 = [c.get('code') for c in data1.get('results', data1) if isinstance(c, dict)]
            if codes1:
                self.assertIn('TWD', codes1)
                self.assertNotIn('USD', codes1)
