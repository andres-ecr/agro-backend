from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from tenants.models import Tenant

User = get_user_model()


class UserHierarchyAndRoleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant_ica = Tenant.objects.create(name='Sede Ica', code='ica')
        self.tenant_casma = Tenant.objects.create(name='Sede Casma', code='casma')

        self.superadmin = User.objects.create_user(
            email='super@agro.com',
            password='Password123!',
            first_name='Super',
            last_name='Admin',
            role='superadmin',
            tenant=self.tenant_ica,
            is_superuser=True,
            is_staff=True,
        )

        self.admin_ica = User.objects.create_user(
            email='admin.ica@agro.com',
            password='Password123!',
            first_name='Admin',
            last_name='Ica',
            role='admin',
            tenant=self.tenant_ica,
        )

        self.operator_ica = User.objects.create_user(
            email='op.ica@agro.com',
            password='Password123!',
            first_name='Operator',
            last_name='Ica',
            role='operator',
            tenant=self.tenant_ica,
        )

        self.operator_casma = User.objects.create_user(
            email='op.casma@agro.com',
            password='Password123!',
            first_name='Operator',
            last_name='Casma',
            role='operator',
            tenant=self.tenant_casma,
        )

    def test_token_obtain_pair_returns_role_and_tenant(self):
        response = self.client.post('/auth/token/', {
            'email': 'super@agro.com',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        user_data = response.data['user']
        self.assertEqual(user_data['role'], 'superadmin')
        self.assertTrue(user_data['is_superuser'])
        self.assertEqual(user_data['tenant']['code'], 'ica')

    def test_superadmin_user_list_all_and_filter_by_tenant(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get('/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        # Should return all users
        emails = [u['email'] for u in results]
        self.assertIn('super@agro.com', emails)
        self.assertIn('admin.ica@agro.com', emails)
        self.assertIn('op.ica@agro.com', emails)
        self.assertIn('op.casma@agro.com', emails)

        # Filter by tenant Casma
        response_filtered = self.client.get(f'/auth/users/?tenant={self.tenant_casma.id}')
        self.assertEqual(response_filtered.status_code, status.HTTP_200_OK)
        filtered_results = response_filtered.data.get('results', response_filtered.data)
        filtered_emails = [u['email'] for u in filtered_results]
        self.assertIn('op.casma@agro.com', filtered_emails)
        self.assertNotIn('op.ica@agro.com', filtered_emails)

    def test_admin_user_list_scoped_to_tenant_excluding_superadmin(self):
        self.client.force_authenticate(user=self.admin_ica)
        response = self.client.get('/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        emails = [u['email'] for u in results]
        self.assertNotIn('super@agro.com', emails)
        self.assertIn('admin.ica@agro.com', emails)
        self.assertIn('op.ica@agro.com', emails)
        self.assertNotIn('op.casma@agro.com', emails)

    def test_admin_cannot_create_superadmin(self):
        self.client.force_authenticate(user=self.admin_ica)
        response = self.client.post('/auth/users/', {
            'email': 'hacker@agro.com',
            'password': 'Password123!',
            'first_name': 'Hacker',
            'last_name': 'Super',
            'role': 'superadmin',
            'tenant': self.tenant_casma.id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_creates_operator_forces_own_tenant(self):
        self.client.force_authenticate(user=self.admin_ica)
        response = self.client.post('/auth/users/', {
            'email': 'new.operator@agro.com',
            'password': 'Password123!',
            'first_name': 'New',
            'last_name': 'Operator',
            'role': 'operator',
            'tenant': self.tenant_casma.id,  # Attempting to assign casma
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_user = User.objects.get(email='new.operator@agro.com')
        # Tenant must be forced to admin's tenant (Ica)
        self.assertEqual(new_user.tenant, self.tenant_ica)

    def test_admin_cannot_create_role_not_allowed_for_tenant(self):
        self.tenant_ica.allowed_roles = ['admin', 'operator']
        self.tenant_ica.save()
        self.client.force_authenticate(user=self.admin_ica)

        # Attempt to create supervisor
        response = self.client.post('/auth/users/', {
            'email': 'supervisor.ica@agro.com',
            'password': 'Password123!',
            'first_name': 'Supervisor',
            'last_name': 'Ica',
            'role': 'supervisor',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)

    def test_admin_cannot_update_role_to_disallowed_role(self):
        self.tenant_ica.allowed_roles = ['admin', 'operator']
        self.tenant_ica.save()
        self.client.force_authenticate(user=self.admin_ica)

        # Attempt to update operator to supervisor
        response = self.client.patch(f'/auth/users/{self.operator_ica.id}/', {
            'role': 'supervisor',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', response.data)
