from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from tenants.models import Tenant
from transporte.models import TransportCompany, Driver, Vehicle

User = get_user_model()


class TransporteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(name='Sede Ica', code='ica')
        self.user = User.objects.create_user(
            email='driver_admin@agro.com',
            password='password123',
            first_name='Admin',
            last_name='Transporte',
            tenant=self.tenant,
            role='admin'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_transport_company_nested(self):
        payload = {
            'tenant': self.tenant.id,
            'ruc': '20555666777',
            'razon_social': 'Transportes del Sur SAC',
            'phone': '999888777',
            'drivers': [
                {'name': 'Juan Perez', 'license_number': 'Q12345678'},
                {'name': 'Carlos Gomez', 'license_number': 'Q87654321'},
            ],
            'vehicles': [
                {'plate': 'ABC-123', 'brand_model': 'Volvo FH16'},
                {'plate': 'XYZ-789', 'brand_model': 'Scania R500'},
            ]
        }
        response = self.client.post('/transporte/companies/', data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TransportCompany.objects.count(), 1)
        self.assertEqual(Driver.objects.count(), 2)
        self.assertEqual(Vehicle.objects.count(), 2)

        company = TransportCompany.objects.first()
        self.assertEqual(company.drivers.count(), 2)
        self.assertEqual(company.vehicles.count(), 2)
        self.assertEqual(response.data['tenant_name'], 'Sede Ica')

    def test_direct_driver_and_vehicle_endpoints(self):
        company = TransportCompany.objects.create(
            tenant=self.tenant,
            ruc='20123456789',
            razon_social='Logistica Andina'
        )
        # Create driver directly
        driver_resp = self.client.post('/transporte/drivers/', {
            'company': company.id,
            'name': 'Mario Vargas',
            'license_number': 'M00112233'
        })
        self.assertEqual(driver_resp.status_code, status.HTTP_201_CREATED)

        # Create vehicle directly
        veh_resp = self.client.post('/transporte/vehicles/', {
            'company': company.id,
            'plate': 'V1B-456',
            'brand_model': 'Mercedes-Benz Actros'
        })
        self.assertEqual(veh_resp.status_code, status.HTTP_201_CREATED)

        # Test all endpoint
        resp_all = self.client.get('/transporte/companies/all/')
        self.assertEqual(resp_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_all.data), 1)
        self.assertEqual(len(resp_all.data[0]['drivers']), 1)
        self.assertEqual(len(resp_all.data[0]['vehicles']), 1)
