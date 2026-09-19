from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from tenants.models import Tenant
from users.serializers import UserProfileSerializer, CustomTokenObtainPairSerializer

User = get_user_model()


class TenantTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant_ica = Tenant.objects.create(
            name='Sede Ica',
            code='ica',
            ruc='20111111111',
            allowed_roles=['admin', 'operator']
        )
        self.tenant_casma = Tenant.objects.create(
            name='Sede Casma',
            code='casma',
            ruc='20222222222',
            allowed_roles=['admin', 'operator']
        )
        self.superadmin = User.objects.create_user(
            email='super@example.com',
            password='password123',
            first_name='Super',
            last_name='Admin',
            role='superadmin',
            is_superuser=True,
            is_staff=True,
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            first_name='Test',
            last_name='User',
            tenant=self.tenant_ica,
            role='admin'
        )

    def test_tenant_creation_and_str(self):
        self.assertEqual(str(self.tenant_ica), 'Sede Ica (ica)')
        self.assertEqual(Tenant.objects.count(), 2)
        self.assertEqual(self.tenant_ica.allowed_roles, ['admin', 'operator'])

    def test_superadmin_tenant_list_api(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get('/tenants/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 2)

    def test_superadmin_tenant_all_action(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get('/tenants/all/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_regular_admin_sees_only_own_tenant(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/tenants/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['code'], 'ica')

    def test_regular_admin_cannot_create_or_modify_tenant(self):
        self.client.force_authenticate(user=self.user)
        # Attempt to create
        create_resp = self.client.post('/tenants/', {'name': 'New Sede', 'code': 'new'})
        self.assertEqual(create_resp.status_code, status.HTTP_403_FORBIDDEN)
        # Attempt to update
        update_resp = self.client.patch(f'/tenants/{self.tenant_ica.id}/', {'name': 'Hacked Name'})
        self.assertEqual(update_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_superadmin_can_create_and_update_tenant(self):
        self.client.force_authenticate(user=self.superadmin)
        create_resp = self.client.post('/tenants/', {
            'name': 'Sede Piura',
            'code': 'piura',
            'ruc': '20333333333',
            'allowed_roles': ['admin', 'operator']
        }, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_resp.data['allowed_roles'], ['admin', 'operator'])

        update_resp = self.client.patch(f'/tenants/{self.tenant_ica.id}/', {
            'allowed_roles': ['admin', 'operator', 'supervisor']
        }, format='json')
        self.assertEqual(update_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(update_resp.data['allowed_roles'], ['admin', 'operator', 'supervisor'])

    def test_user_profile_serializer_includes_tenant(self):
        serializer = UserProfileSerializer(self.user)
        self.assertIsNotNone(serializer.data.get('tenant'))
        self.assertEqual(serializer.data['tenant']['code'], 'ica')
        self.assertEqual(serializer.data['tenant']['name'], 'Sede Ica')
        self.assertEqual(serializer.data['tenant']['id'], self.tenant_ica.id)

    def test_token_serializer_includes_tenant(self):
        serializer = CustomTokenObtainPairSerializer()
        serializer.user = self.user
        data = serializer.validate({'email': self.user.email, 'password': 'password123'})
        self.assertIn('user', data)
        self.assertIn('tenant', data['user'])
        self.assertEqual(data['user']['tenant']['code'], 'ica')
