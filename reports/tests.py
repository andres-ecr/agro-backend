import json
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from tenants.models import Tenant
from reports.models import Report

User = get_user_model()


class ReportEditingTests(TestCase):
    def setUp(self):
        from inventory.models import Product, Campaign
        self.client = APIClient()
        self.tenant = Tenant.objects.create(name='Edit Site', code='EDIT')
        self.other = Tenant.objects.create(name='Other Site', code='OTHER')
        self.admin = User.objects.create_user(email='edit@agro.com', password='password123', role='admin', tenant=self.tenant)
        self.operator = User.objects.create_user(email='opedit@agro.com', password='password123', role='operator', tenant=self.tenant)
        product = Product.objects.create(name='Uva', code='EDIT-UVA', tenant=self.tenant)
        self.campaign = Campaign.objects.create(name='Edit Campaign', code='EDIT-C', product=product, tenant=self.tenant, status='active')
        self.report = Report.objects.create(id='EDIT-1', tenant=self.tenant, campaign=self.campaign, created_by=self.operator, producto='Uva', lote='OLD', datosGenerales_json=json.dumps({'producto': 'Uva', 'carga': 'OLD', 'legacyField': 'keep'}), registros_json='[]', totales_json='{}')
        self.payload = {'datosGenerales': {'producto': 'Uva', 'carga': 'NEW', 'productorCode': '001', 'fechaRecepcion': '2026-09-16'}, 'registros': [{'id': 'ROW-1', 'pesoBruto': '100.10', 'pesoParihuela': '10', 'tara': '5', 'pesoJaba': '0.5', 'jabas': 10}], 'totales': {'totalPesoNeto': 999}, 'status': 'verified'}

    def test_admin_update_persists_json_and_authoritative_totals(self):
        self.payload['expectedRevision'] = self.report.updated_at.isoformat()
        self.client.force_authenticate(self.admin)
        response = self.client.put('/reports/EDIT-1/', self.payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.report.refresh_from_db()
        self.assertEqual(self.report.lote, 'NEW')
        self.assertEqual(self.report.totalPesoNeto, Decimal('85.10'))
        self.assertEqual(self.report.totalJabas, 10)
        general = json.loads(self.report.datosGenerales_json)
        self.assertEqual(general['productorCode'], '001')
        self.assertEqual(general['legacyField'], 'keep')
        self.assertEqual(json.loads(self.report.registros_json)[0]['pesoNeto'], '85.10')
        self.assertEqual(self.report.created_by, self.operator)
        self.assertEqual(self.client.get('/reports/EDIT-1/').data['datosGenerales']['carga'], 'NEW')

    def test_update_permission_and_tenant_boundary(self):
        self.payload['expectedRevision'] = self.report.updated_at.isoformat()
        for role in ('operator', 'supervisor'):
            self.operator.role = role
            self.operator.save()
            self.client.force_authenticate(self.operator)
            self.assertEqual(self.client.patch('/reports/EDIT-1/', self.payload, format='json').status_code, 403)
        self.admin.tenant = self.other
        self.admin.save()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.put('/reports/EDIT-1/', self.payload, format='json').status_code, 404)
        self.admin.role = 'superadmin'
        self.admin.save()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.put('/reports/EDIT-1/', self.payload, format='json').status_code, 200)

    def test_invalid_values_and_immutable_fields_leave_report_unchanged(self):
        self.payload['expectedRevision'] = self.report.updated_at.isoformat()
        self.client.force_authenticate(self.admin)
        for change in ({'id': 'CHANGED'}, {'tenant': self.other.id}, {'created_by': self.admin.id}, {'campaign': self.campaign.id}, {'status': 'invalid'}):
            response = self.client.put('/reports/EDIT-1/', {**self.payload, **change}, format='json')
            self.assertEqual(response.status_code, 400, response.data)
        for field, value in [('pesoBruto', '-1'), ('jabas', 1.5), ('pesoParihuela', 'NaN'), ('tara', '200')]:
            record = {**self.payload['registros'][0], field: value}
            self.assertEqual(self.client.put('/reports/EDIT-1/', {**self.payload, 'registros': [record]}, format='json').status_code, 400)
        general = {**self.payload['datosGenerales'], 'fechaRecepcion': '2026-02-30'}
        self.assertEqual(self.client.put('/reports/EDIT-1/', {**self.payload, 'datosGenerales': general}, format='json').status_code, 400)
        self.report.refresh_from_db()
        self.assertEqual(self.report.lote, 'OLD')

    def test_product_change_requires_matching_campaign_and_rows_can_be_removed(self):
        self.payload['expectedRevision'] = self.report.updated_at.isoformat()
        self.client.force_authenticate(self.admin)
        general = {**self.payload['datosGenerales'], 'producto': 'Unknown'}
        self.assertEqual(self.client.put('/reports/EDIT-1/', {**self.payload, 'datosGenerales': general}, format='json').status_code, 400)
        response = self.client.put('/reports/EDIT-1/', {**self.payload, 'registros': []}, format='json')
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.totalPesoNeto, 0)

    def test_legacy_calendar_dates_and_numeric_record_ids_are_editable(self):
        general = {'producto': 'Uva', 'carga': 'OLD', 'fechaRecepcion': '19/09/2026', 'fechaCosecha': '29/02/2024'}
        self.report.datosGenerales_json = json.dumps(general)
        self.report.registros_json = json.dumps([{**self.payload['registros'][0], 'id': 1}])
        self.report.save()
        self.client.force_authenticate(self.admin)
        revision = self.client.get('/reports/EDIT-1/').data.get('revision', self.report.updated_at.isoformat())
        response = self.client.patch('/reports/EDIT-1/', {'status': 'verified', 'expectedRevision': revision}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.report.refresh_from_db()
        self.assertEqual(json.loads(self.report.datosGenerales_json)['fechaRecepcion'], '2026-09-19')
        self.assertEqual(json.loads(self.report.datosGenerales_json)['fechaCosecha'], '2024-02-29')
        self.assertEqual(json.loads(self.report.registros_json)[0]['id'], 1)
        for invalid in ('29/02/2023', '31/04/2026'):
            response = self.client.patch('/reports/EDIT-1/', {'datosGenerales': {'fechaCosecha': invalid}, 'expectedRevision': self.report.updated_at.isoformat()}, format='json')
            self.assertEqual(response.status_code, 400, response.data)

    def test_numeric_record_id_is_preserved_and_invalid_duplicates_are_rejected(self):
        self.client.force_authenticate(self.admin)
        revision = self.report.updated_at.isoformat()
        row = {**self.payload['registros'][0], 'id': 1}
        response = self.client.put('/reports/EDIT-1/', {**self.payload, 'expectedRevision': revision, 'registros': [row]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.report.refresh_from_db()
        self.assertEqual(json.loads(self.report.registros_json)[0]['id'], 1)
        for rows in ([row, row], [row, {**row, 'id': '1'}], [{**row, 'id': True}], [{**row, 'id': 1.5}], [{**row, 'id': ''}]):
            self.assertEqual(self.client.put('/reports/EDIT-1/', {**self.payload, 'expectedRevision': self.report.updated_at.isoformat(), 'registros': rows}, format='json').status_code, 400)

    def test_stale_admin_revision_does_not_overwrite_saved_weights(self):
        self.client.force_authenticate(self.admin)
        original = self.client.get('/reports/EDIT-1/').data
        revision = original.get('revision', self.report.updated_at.isoformat())
        first = {**self.payload, 'expectedRevision': revision, 'registros': [{**self.payload['registros'][0], 'pesoBruto': '200.10'}]}
        self.assertEqual(self.client.put('/reports/EDIT-1/', first, format='json').status_code, 200)
        second_admin = User.objects.create_user(email='secondedit@agro.com', password='password123', role='admin', tenant=self.tenant)
        self.client.force_authenticate(second_admin)
        stale = {**self.payload, 'expectedRevision': revision, 'datosGenerales': {**self.payload['datosGenerales'], 'observaciones': 'Stale admin observation'}}
        response = self.client.put('/reports/EDIT-1/', stale, format='json')
        self.assertEqual(response.status_code, 409, response.data)
        self.report.refresh_from_db()
        self.assertEqual(self.report.totalPesoNeto, Decimal('185.10'))
        self.assertNotIn('observaciones', json.loads(self.report.datosGenerales_json))
        self.assertEqual(self.client.patch('/reports/EDIT-1/', {'status': 'cancelled'}, format='json').status_code, 409)

    def test_preloaded_serializer_rechecks_revision_inside_atomic_save(self):
        from reports.serializers import ReportSerializer
        from rest_framework.exceptions import APIException
        revision = self.report.updated_at.isoformat()
        stale = ReportSerializer(self.report, data={**self.payload, 'expectedRevision': revision})
        stale.is_valid(raise_exception=True)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.put('/reports/EDIT-1/', {**self.payload, 'expectedRevision': revision, 'registros': []}, format='json').status_code, 200)
        with self.assertRaises(APIException) as conflict:
            stale.save()
        self.assertEqual(conflict.exception.status_code, 409)
        self.report.refresh_from_db()
        self.assertEqual(self.report.totalPesoNeto, 0)


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

        from inventory.models import Product, Campaign
        self.prod_uva = Product.objects.create(name='Uva', code='UVA', tenant=self.tenant1)
        self.camp_uva = Campaign.objects.create(
            name='Campaña Uva 2026',
            code='CAMP-UVA',
            product=self.prod_uva,
            tenant=self.tenant1,
            status='active'
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

    def test_superadmin_header_and_query_tenant_filtering(self):
        Report.objects.create(id='REP-SUPER-ICA', producto='Uva', lote='L-I', tenant=self.tenant1)
        Report.objects.create(id='REP-SUPER-CAS', producto='Palta', lote='L-C', tenant=self.tenant2)

        self.client.force_authenticate(user=self.superuser)

        # 1. Without header or param: Global view (both returned)
        res_global = self.client.get('/reports/')
        self.assertEqual(res_global.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in res_global.data.get('results', res_global.data)]
        self.assertIn('REP-SUPER-ICA', ids)
        self.assertIn('REP-SUPER-CAS', ids)

        # 2. With X-Tenant-ID header for Casma
        res_casma_hdr = self.client.get('/reports/', HTTP_X_TENANT_ID=str(self.tenant2.id))
        self.assertEqual(res_casma_hdr.status_code, status.HTTP_200_OK)
        casma_ids = [r['id'] for r in res_casma_hdr.data.get('results', res_casma_hdr.data)]
        self.assertIn('REP-SUPER-CAS', casma_ids)
        self.assertNotIn('REP-SUPER-ICA', casma_ids)

        # 3. With ?tenant= query param for Ica
        res_ica_param = self.client.get(f'/reports/?tenant={self.tenant1.id}')
        self.assertEqual(res_ica_param.status_code, status.HTTP_200_OK)
        ica_ids = [r['id'] for r in res_ica_param.data.get('results', res_ica_param.data)]
        self.assertIn('REP-SUPER-ICA', ica_ids)
        self.assertNotIn('REP-SUPER-CAS', ica_ids)

    def test_operator_cannot_override_tenant_via_header(self):
        Report.objects.create(id='REP-SEC-ICA', producto='Uva', lote='L-1', tenant=self.tenant1)
        Report.objects.create(id='REP-SEC-CAS', producto='Palta', lote='L-2', tenant=self.tenant2)

        # Operator of Ica tries to spoof header to Sede Casma
        self.client.force_authenticate(user=self.user_ica)
        res = self.client.get('/reports/', HTTP_X_TENANT_ID=str(self.tenant2.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in res.data.get('results', res.data)]
        self.assertIn('REP-SEC-ICA', ids)
        self.assertNotIn('REP-SEC-CAS', ids)

    def test_dashboard_metrics_with_tenant_header_for_superadmin(self):
        Report.objects.create(
            id='REP-MET-ICA',
            producto='Uva',
            lote='L-M1',
            totalPesoNeto=Decimal('100.0'),
            totalJabas=10,
            tenant=self.tenant1
        )
        Report.objects.create(
            id='REP-MET-CAS',
            producto='Palta',
            lote='L-M2',
            totalPesoNeto=Decimal('200.0'),
            totalJabas=20,
            tenant=self.tenant2
        )

        self.client.force_authenticate(user=self.superuser)

        # Scoped to Casma via X-Tenant-ID header
        res = self.client.get('/reports/dashboard_metrics/', HTTP_X_TENANT_ID=str(self.tenant2.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total_kilos'], 200.0)
        self.assertEqual(res.data['total_jabas'], 20)
        self.assertEqual(res.data['total_cargas'], 1)
        self.assertEqual(len(res.data['by_product']), 1)
        self.assertEqual(res.data['by_product'][0]['producto'], 'Palta')

    def test_dashboard_metrics_filters_by_clp_and_transportista(self):
        self.client.force_authenticate(user=self.superuser)
        Report.objects.create(
            id='REP-FILT-1',
            producto='Uva',
            lote='CRG-001',
            totalPesoNeto=Decimal('500.0'),
            totalJabas=50,
            datosGenerales_json=json.dumps({
                'clp': 'CLP-ICA-999',
                'empresaTransporte': 'Transportes del Sur'
            })
        )
        Report.objects.create(
            id='REP-FILT-2',
            producto='Palta',
            lote='CRG-002',
            totalPesoNeto=Decimal('300.0'),
            totalJabas=30,
            datosGenerales_json=json.dumps({
                'clp': 'CLP-CAS-888',
                'empresaTransporte': 'Transportes del Norte'
            })
        )

        # Filter by clp
        res_clp = self.client.get('/reports/dashboard_metrics/?clp=CLP-ICA-999')
        self.assertEqual(res_clp.status_code, status.HTTP_200_OK)
        self.assertTrue(res_clp.data['is_filtered'])
        self.assertEqual(res_clp.data['filtered_kilos'], 500.0)
        self.assertEqual(res_clp.data['filtered_cargas'], 1)

        # Filter by transportista
        res_trans = self.client.get('/reports/dashboard_metrics/?transportista=Norte')
        self.assertEqual(res_trans.status_code, status.HTTP_200_OK)
        self.assertTrue(res_trans.data['is_filtered'])
        self.assertEqual(res_trans.data['filtered_kilos'], 300.0)
        self.assertEqual(res_trans.data['filtered_cargas'], 1)

    def test_create_report_with_carga_only_sets_lote(self):
        self.client.force_authenticate(user=self.user_ica)
        payload = {
            'id': 'REP-CARGA-ONLY',
            'datosGenerales': {
                'producto': 'Uva',
                'carga': 'CRG-EXCLUSIVA-99',
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
        res = self.client.post('/reports/', data=payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        rep = Report.objects.get(id='REP-CARGA-ONLY')
        self.assertEqual(rep.lote, 'CRG-EXCLUSIVA-99')

    def test_create_report_fails_without_active_campaign(self):
        self.client.force_authenticate(user=self.user_ica)
        # Try creating report for 'Palta', which has no active campaign in tenant1
        payload = {
            'id': 'REP-PALTA-FAIL',
            'datosGenerales': {
                'producto': 'Palta',
                'carga': 'CRG-FAIL-01',
            },
            'registros': [{'jabas': 10, 'pesoBruto': 150.0, 'pesoParihuela': 20.0, 'pesoJaba': 1.5, 'tara': 35.0, 'pesoNeto': 115.0}],
            'totales': {'totalPesoBruto': '150.0', 'totalPesoNeto': '115.0', 'totalJabas': 10}
        }
        res = self.client.post('/reports/', data=payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No existe una campaña activa", str(res.data))

    def test_campaign_consolidated_report_and_close_and_purge(self):
        from inventory.models import Campaign
        # Create a report under camp_uva
        self.client.force_authenticate(user=self.user_ica)
        payload = {
            'id': 'REP-CAMP-TEST-1',
            'datosGenerales': {
                'producto': 'Uva',
                'variedad': 'Red Globe',
                'productor': 'Don Ricardo',
                'carga': 'CRG-CAMP-1',
            },
            'registros': [{'jabas': 20, 'pesoBruto': 300.0, 'pesoParihuela': 20.0, 'pesoJaba': 1.5, 'tara': 50.0, 'pesoNeto': 250.0}],
            'totales': {'totalPesoBruto': '300.0', 'totalPesoNeto': '250.0', 'totalJabas': 20}
        }
        res_create = self.client.post('/reports/', data=payload, format='json')
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)

        # 1. Consolidated report
        res_summary = self.client.get(f'/inventory/campaigns/{self.camp_uva.id}/consolidated_report/')
        self.assertEqual(res_summary.status_code, status.HTTP_200_OK)
        self.assertEqual(res_summary.data['total_kilos_netos'], 250.0)
        self.assertEqual(res_summary.data['total_jabas'], 20)
        self.assertEqual(res_summary.data['producers_breakdown'][0]['productor'], 'Don Ricardo')
        self.assertEqual(res_summary.data['varieties_breakdown'][0]['variedad'], 'Red Globe')

        # 2. Operator attempt to close gets 403 Forbidden
        res_op_close = self.client.post(f'/inventory/campaigns/{self.camp_uva.id}/close_campaign/')
        self.assertEqual(res_op_close.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Authenticate as plant admin
        admin_ica = User.objects.create_user(
            email='admin_ica@agro.com',
            password='password123',
            role='admin',
            tenant=self.tenant1
        )
        self.client.force_authenticate(user=admin_ica)

        # Admin close campaign
        res_close = self.client.post(f'/inventory/campaigns/{self.camp_uva.id}/close_campaign/')
        self.assertEqual(res_close.status_code, status.HTTP_200_OK)
        self.camp_uva.refresh_from_db()
        self.assertEqual(self.camp_uva.status, 'closed')
        self.assertIsNotNone(self.camp_uva.closed_summary)
        self.assertEqual(self.camp_uva.closed_summary['total_kilos_netos'], 250.0)

        # 4. Admin purge reports
        res_purge = self.client.post(f'/inventory/campaigns/{self.camp_uva.id}/purge_reports/')
        self.assertEqual(res_purge.status_code, status.HTTP_200_OK)
        self.assertEqual(res_purge.data['deleted_count'], 1)
        self.assertEqual(self.camp_uva.reports.count(), 0)
        # Snapshot still preserved
        self.assertEqual(self.camp_uva.closed_summary['total_kilos_netos'], 250.0)

