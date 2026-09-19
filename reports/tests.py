import json
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from tenants.models import Tenant
from reports.models import Report

User = get_user_model()


class ReportTenantAndFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant1 = Tenant.objects.create(name='Sede Ica', code='ICA')
        self.tenant2 = Tenant.objects.create(name='Sede Casma', code='CASMA')

        self.user_ica = User.objects.create_user(
            email='ica_op@agro.com',
            password='password123',
            first_name='Operador',
            last_name='Ica',
            role='operator',
            tenant=self.tenant1
        )
        self.user_casma = User.objects.create_user(
            email='casma_op@agro.com',
            password='password123',
            first_name='Operador',
            last_name='Casma',
            role='operator',
            tenant=self.tenant2
        )
        self.superuser = User.objects.create_superuser(
            email='super@agro.com',
            password='password123',
            first_name='Super',
            last_name='User'
        )

    def test_create_report_assigns_tenant_and_created_by(self):
        self.client.force_authenticate(user=self.user_ica)
        payload = {
            'id': 'REP-ICA-001',
            'datosGenerales': {
                'producto': 'Uva',
                'lote': 'L-001',
                'carga': 'CARGA-101',
                'clp': 'CLP-ICA-01'
            },
            'registros': [
                {'jabas': 10, 'pesoBruto': 150.0, 'pesoParihuela': 20.0, 'pesoJaba': 1.5, 'tara': 35.0, 'pesoNeto': 115.0}
            ],
            'totales': {
                'totalPesoBruto': '150.0',
                'totalPesoNeto': '115.0',
                'totalJabas': 10
            }
        }
        response = self.client.post('/reports/', data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        report = Report.objects.get(id='REP-ICA-001')
        self.assertEqual(report.tenant, self.tenant1)
        self.assertEqual(report.created_by, self.user_ica)

    def test_tenant_isolation_in_reports_list(self):
        # Create a report for tenant1 and one for tenant2
        Report.objects.create(
            id='REP-ICA-01',
            producto='Uva',
            lote='L-01',
            tenant=self.tenant1,
            created_by=self.user_ica,
            datosGenerales_json=json.dumps({'carga': 'CARGA-10', 'clp': 'CLP-01'})
        )
        Report.objects.create(
            id='REP-CAS-01',
            producto='Palta',
            lote='L-02',
            tenant=self.tenant2,
            created_by=self.user_casma,
            datosGenerales_json=json.dumps({'carga': 'CARGA-20', 'clp': 'CLP-02'})
        )

        # User ICA should only see REP-ICA-01
        self.client.force_authenticate(user=self.user_ica)
        res = self.client.get('/reports/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data.get('results', res.data)
        ids = [r['id'] for r in results]
        self.assertIn('REP-ICA-01', ids)
        self.assertNotIn('REP-CAS-01', ids)

        # Superuser should see both
        self.client.force_authenticate(user=self.superuser)
        res_super = self.client.get('/reports/')
        self.assertEqual(res_super.status_code, status.HTTP_200_OK)
        results_super = res_super.data.get('results', res_super.data)
        super_ids = [r['id'] for r in results_super]
        self.assertIn('REP-ICA-01', super_ids)
        self.assertIn('REP-CAS-01', super_ids)

    def test_filter_by_carga_and_clp(self):
        Report.objects.create(
            id='REP-FILTER-1',
            producto='Uva',
            lote='L-10',
            tenant=self.tenant1,
            datosGenerales_json=json.dumps({'carga': 'CARGA-999', 'clp': 'CLP-SPECIAL-1'})
        )
        Report.objects.create(
            id='REP-FILTER-2',
            producto='Uva',
            lote='L-11',
            tenant=self.tenant1,
            datosGenerales_json=json.dumps({'carga': 'CARGA-888', 'clp': 'CLP-OTHER'})
        )

        self.client.force_authenticate(user=self.superuser)

        # Filter by carga
        res_carga = self.client.get('/reports/?carga=999')
        self.assertEqual(res_carga.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in res_carga.data.get('results', res_carga.data)]
        self.assertIn('REP-FILTER-1', ids)
        self.assertNotIn('REP-FILTER-2', ids)

        # Filter by clp
        res_clp = self.client.get('/reports/?clp=SPECIAL')
        self.assertEqual(res_clp.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in res_clp.data.get('results', res_clp.data)]
        self.assertIn('REP-FILTER-1', ids)
        self.assertNotIn('REP-FILTER-2', ids)

    def test_dashboard_metrics(self):
        Report.objects.create(
            id='REP-DASH-1',
            producto='Palta',
            lote='L-D1',
            totalPesoNeto=Decimal('1500.5'),
            totalJabas=50,
            tenant=self.tenant1,
            created_by=self.user_ica,
            datosGenerales_json=json.dumps({
                'productor': 'Juan Perez',
                'placaVehiculo': 'ABC-123',
                'carga': 'CARGA-01'
            })
        )
        Report.objects.create(
            id='REP-DASH-2',
            producto='Palta',
            lote='L-D2',
            totalPesoNeto=Decimal('500.0'),
            totalJabas=20,
            tenant=self.tenant1,
            created_by=self.user_ica,
            datosGenerales_json=json.dumps({
                'productor': 'Maria Gomez',
                'placaVehiculo': 'XYZ-789',
                'carga': 'CARGA-02'
            })
        )
        Report.objects.create(
            id='REP-DASH-3',
            producto='Uva',
            lote='L-D3',
            totalPesoNeto=Decimal('2000.0'),
            totalJabas=80,
            tenant=self.tenant1,
            created_by=self.user_ica,
            datosGenerales_json=json.dumps({
                'productor': 'Carlos Ruiz',
                'placaVehiculo': 'DEF-456',
                'carga': 'CARGA-03'
            })
        )
        # Another tenant's report to verify isolation
        Report.objects.create(
            id='REP-DASH-OTHER',
            producto='Uva',
            lote='L-D4',
            totalPesoNeto=Decimal('9999.0'),
            totalJabas=999,
            tenant=self.tenant2,
            created_by=self.user_casma,
            datosGenerales_json=json.dumps({'productor': 'Other'})
        )

        self.client.force_authenticate(user=self.user_ica)
        response = self.client.get('/reports/dashboard_metrics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['kilos_hoy'], 4000.5)
        self.assertEqual(data['jabas_hoy'], 150)
        self.assertEqual(data['cargas_hoy'], 3)
        self.assertEqual(data['total_kilos'], 4000.5)
        self.assertEqual(data['total_jabas'], 150)
        self.assertEqual(data['total_cargas'], 3)

        # by_product check
        by_product = data['by_product']
        self.assertEqual(len(by_product), 2)
        products = {p['producto']: p for p in by_product}
        self.assertIn('Palta', products)
        self.assertIn('Uva', products)
        self.assertEqual(products['Palta']['kilos'], 2000.5)
        self.assertEqual(products['Palta']['jabas'], 70)
        self.assertEqual(products['Palta']['cargas'], 2)
        self.assertEqual(products['Uva']['kilos'], 2000.0)

        # recent_reports check
        recent = data['recent_reports']
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0]['productor'], 'Carlos Ruiz')
        self.assertEqual(recent[0]['placa'], 'DEF-456')
        self.assertEqual(recent[0]['carga'], 'CARGA-03')
