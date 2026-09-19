from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from .models import Product, ProductVariety
from .serializers import ProductSerializer

User = get_user_model()


class ProductVarietyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='password123',
            first_name='Test',
            last_name='User',
            role='supervisor'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.product = Product.objects.create(
            name='Test Fruit',
            code='TF01',
            product_type=Product.TYPE_FINISHED,
            unit=Product.UNIT_KG,
            created_by=self.user
        )

    def test_product_variety_model(self):
        variety = ProductVariety.objects.create(
            product=self.product,
            name='Variety A',
            code='VAR-A'
        )
        self.assertEqual(str(variety), 'Test Fruit - Variety A')
        self.assertTrue(variety.is_active)

    def test_product_serializer_create_with_string_varieties(self):
        data = {
            'name': 'Pecana',
            'code': 'PEC-01',
            'product_type': 'finished',
            'unit': 'kg',
            'varieties': ['Mahan', 'Stuart']
        }
        serializer = ProductSerializer(data=data, context={'request': type('Req', (), {'user': self.user})()})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()

        self.assertEqual(product.varieties.count(), 2)
        variety_names = list(product.varieties.values_list('name', flat=True))
        self.assertIn('Mahan', variety_names)
        self.assertIn('Stuart', variety_names)

    def test_product_serializer_create_with_dict_varieties(self):
        data = {
            'name': 'Manzana',
            'code': 'MNZ-01',
            'product_type': 'finished',
            'unit': 'kg',
            'varieties': [
                {'name': 'Royal Gala', 'code': 'RG'},
                {'name': 'Fuji', 'code': 'FJ'}
            ]
        }
        serializer = ProductSerializer(data=data, context={'request': type('Req', (), {'user': self.user})()})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        product = serializer.save()

        self.assertEqual(product.varieties.count(), 2)
        rg = product.varieties.get(name='Royal Gala')
        self.assertEqual(rg.code, 'RG')

    def test_product_serializer_update_sync_varieties(self):
        # Initial varieties
        ProductVariety.objects.create(product=self.product, name='Old Variety 1')
        ProductVariety.objects.create(product=self.product, name='Old Variety 2')

        update_data = {
            'name': 'Test Fruit Updated',
            'code': 'TF01',
            'varieties': ['Old Variety 1', 'New Variety 3']
        }
        serializer = ProductSerializer(
            instance=self.product,
            data=update_data,
            partial=True,
            context={'request': type('Req', (), {'user': self.user})()}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_product = serializer.save()

        variety_names = list(updated_product.varieties.values_list('name', flat=True))
        self.assertEqual(len(variety_names), 2)
        self.assertIn('Old Variety 1', variety_names)
        self.assertIn('New Variety 3', variety_names)
        self.assertNotIn('Old Variety 2', variety_names)

    def test_api_list_products_includes_varieties(self):
        ProductVariety.objects.create(product=self.product, name='Variety Alpha')
        response = self.client.get('/inventory/products/')
        self.assertEqual(response.status_code, 200)
        results = response.data.get('results', response.data)
        prod_data = next((p for p in results if p['id'] == self.product.id), None)
        self.assertIsNotNone(prod_data)
        self.assertIn('varieties', prod_data)
        self.assertEqual(len(prod_data['varieties']), 1)
        self.assertEqual(prod_data['varieties'][0]['name'], 'Variety Alpha')


class TenantScopedProductTests(TestCase):
    def setUp(self):
        from tenants.models import Tenant
        self.tenant_ica = Tenant.objects.create(name='Sede Ica', code='ica')
        self.tenant_casma = Tenant.objects.create(name='Sede Casma', code='casma')

        self.user_ica = User.objects.create_user(
            email='ica_user@example.com',
            password='password123',
            role='supervisor',
            tenant=self.tenant_ica
        )
        self.user_casma = User.objects.create_user(
            email='casma_user@example.com',
            password='password123',
            role='supervisor',
            tenant=self.tenant_casma
        )
        self.superadmin = User.objects.create_user(
            email='superadmin@example.com',
            password='password123',
            role='superadmin',
            is_superuser=True
        )

        self.prod_ica = Product.objects.create(
            name='Palta Ica',
            code='PALTA',
            tenant=self.tenant_ica,
            created_by=self.user_ica
        )
        self.prod_casma = Product.objects.create(
            name='Palta Casma',
            code='PALTA',
            tenant=self.tenant_casma,
            created_by=self.user_casma
        )

    def test_same_code_different_tenants(self):
        """Verify that same code can exist across different tenants"""
        self.assertEqual(self.prod_ica.code, self.prod_casma.code)
        self.assertNotEqual(self.prod_ica.tenant, self.prod_casma.tenant)

    def test_tenant_user_sees_only_own_products(self):
        client = APIClient()
        client.force_authenticate(user=self.user_ica)
        response = client.get('/inventory/products/')
        self.assertEqual(response.status_code, 200)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.prod_ica.id)

    def test_superadmin_sees_all_or_filtered_by_header(self):
        client = APIClient()
        client.force_authenticate(user=self.superadmin)
        
        # All products
        response = client.get('/inventory/products/')
        self.assertEqual(response.status_code, 200)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 2)

        # Filtered by X-Tenant-ID header
        response = client.get('/inventory/products/', HTTP_X_TENANT_ID=str(self.tenant_ica.id))
        self.assertEqual(response.status_code, 200)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.prod_ica.id)

    def test_create_product_assigns_tenant_automatically(self):
        client = APIClient()
        client.force_authenticate(user=self.user_casma)
        data = {
            'name': 'Mango Casma',
            'code': 'MANGO-01',
            'product_type': 'finished',
            'unit': 'kg',
            'varieties': ['KENT']
        }
        response = client.post('/inventory/products/', data=data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['tenant'], self.tenant_casma.id)
