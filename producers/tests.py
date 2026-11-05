from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from producers.models import Producer, ProducerCLP

User = get_user_model()


class ProducerCLPTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='producer_admin@agro.com',
            password='password123',
            first_name='Producer',
            last_name='Admin',
            role='admin'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_producer_with_clp_list(self):
        payload = {
            'code': 'PROD-001',
            'name': 'Fundo San Jose',
            'clp': 'CLP-PRINCIPAL',
            'clp_list': [
                {'code': 'CLP-001', 'lugar_produccion': 'Lote Norte', 'distrito': 'Los Aquijes'},
                {'code': 'CLP-002', 'lugar_produccion': 'Lote Sur', 'distrito': 'Santiago'},
            ]
        }
        response = self.client.post('/producers/', data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Producer.objects.count(), 1)
        self.assertEqual(ProducerCLP.objects.count(), 2)

        producer = Producer.objects.first()
        self.assertEqual(producer.clp_list.count(), 2)
        clp1 = producer.clp_list.get(code='CLP-001')
        self.assertEqual(clp1.lugar_produccion, 'Lote Norte')
        self.assertEqual(clp1.distrito, 'Los Aquijes')

    def test_update_producer_clp_list(self):
        producer = Producer.objects.create(code='PROD-002', name='Agricola Verde')
        clp1 = ProducerCLP.objects.create(producer=producer, code='CLP-A', lugar_produccion='Sector 1', distrito='Ica')
        clp2 = ProducerCLP.objects.create(producer=producer, code='CLP-B', lugar_produccion='Sector 2', distrito='Parcona')

        # Update: keep CLP-A (update name and distrito), remove CLP-B, add CLP-C
        payload = {
            'code': 'PROD-002',
            'name': 'Agricola Verde SAC',
            'clp_list': [
                {'id': clp1.id, 'code': 'CLP-A-MOD', 'lugar_produccion': 'Sector 1 Modificado', 'distrito': 'Subtanjalla'},
                {'code': 'CLP-C', 'lugar_produccion': 'Sector Nuevo', 'distrito': 'La Tinguiña'},
            ]
        }
        response = self.client.put(f'/producers/{producer.id}/', data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        producer.refresh_from_db()
        self.assertEqual(producer.name, 'Agricola Verde SAC')
        self.assertEqual(producer.clp_list.count(), 2)
        clp_a_mod = producer.clp_list.get(code='CLP-A-MOD')
        self.assertEqual(clp_a_mod.distrito, 'Subtanjalla')
        clp_c = producer.clp_list.get(code='CLP-C')
        self.assertEqual(clp_c.distrito, 'La Tinguiña')

    def test_list_producers_includes_clp_list(self):
        producer = Producer.objects.create(code='PROD-003', name='Valle Hermoso')
        ProducerCLP.objects.create(producer=producer, code='CLP-VH1', lugar_produccion='Fundo 1', distrito='Pachacutec')

        response = self.client.get('/producers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        item = [p for p in results if p['code'] == 'PROD-003'][0]
        self.assertIn('clp_list', item)
        self.assertEqual(len(item['clp_list']), 1)
        self.assertEqual(item['clp_list'][0]['code'], 'CLP-VH1')
        self.assertEqual(item['clp_list'][0]['distrito'], 'Pachacutec')

    def test_clp_tonnage_quota_initialization_and_admin_vs_operator_permissions(self):
        # 1. Operator creates producer with CLP and total tonnage
        operator = User.objects.create_user(
            email='op_prod@agro.com', password='password123', role='operator'
        )
        self.client.force_authenticate(user=operator)
        payload = {
            'code': 'PROD-OP-1',
            'name': 'Fundo Operator',
            'clp_list': [
                {'code': 'CLP-OP-1', 'lugar_produccion': 'Lote 1', 'distrito': 'Ica', 'tonelaje_total': 50000}
            ]
        }
        res = self.client.post('/producers/', data=payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        clp = ProducerCLP.objects.get(code='CLP-OP-1')
        self.assertEqual(float(clp.tonelaje_total), 50000.0)
        # Saldo automatically initialized to total
        self.assertEqual(float(clp.tonelaje_saldo), 50000.0)
        self.assertEqual(clp.tonelaje_total_tn, 50.0)
        self.assertEqual(clp.tonelaje_saldo_tn, 50.0)

        # 2. Operator attempts to tamper directly with saldo_restante -> ignored
        update_payload = {
            'code': 'PROD-OP-1',
            'name': 'Fundo Operator',
            'clp_list': [
                {'id': clp.id, 'code': 'CLP-OP-1', 'tonelaje_total': 50000, 'tonelaje_saldo': 999999}
            ]
        }
        res_update = self.client.put(f"/producers/{clp.producer_id}/", data=update_payload, format='json')
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)
        clp.refresh_from_db()
        self.assertEqual(float(clp.tonelaje_saldo), 50000.0)

        # 3. Operator increases total (ampliacion de cupo SENASA) -> delta applies to saldo
        ampliacion_payload = {
            'code': 'PROD-OP-1',
            'name': 'Fundo Operator',
            'clp_list': [
                {'id': clp.id, 'code': 'CLP-OP-1', 'tonelaje_total': 70000}
            ]
        }
        self.client.put(f"/producers/{clp.producer_id}/", data=ampliacion_payload, format='json')
        clp.refresh_from_db()
        self.assertEqual(float(clp.tonelaje_total), 70000.0)
        self.assertEqual(float(clp.tonelaje_saldo), 70000.0)

        # 4. Admin edits saldo directly (for manual corrections)
        self.client.force_authenticate(user=self.user)
        admin_payload = {
            'code': 'PROD-OP-1',
            'name': 'Fundo Operator',
            'clp_list': [
                {'id': clp.id, 'code': 'CLP-OP-1', 'tonelaje_total': 70000, 'tonelaje_saldo': 42000.50}
            ]
        }
        res_admin = self.client.put(f"/producers/{clp.producer_id}/", data=admin_payload, format='json')
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        clp.refresh_from_db()
        self.assertEqual(float(clp.tonelaje_saldo), 42000.50)

    def test_clp_tonnage_excel_number_parsing(self):
        """Verifica que números con formato Excel (coma para miles, punto para decimales) se guarden como 100000 y no como 100"""
        self.client.force_authenticate(user=self.user)
        payload = {
            'code': 'PROD-EXCEL',
            'name': 'Fundo Excel Format',
            'clp_list': [
                {
                    'code': 'CLP-EX-1',
                    'tonelaje_total': '100,000',
                    'tonelaje_saldo': '100,000.00'
                },
                {
                    'code': 'CLP-EX-2',
                    'tonelaje_total': '100.000',
                    'tonelaje_saldo': '50,000.50'
                }
            ]
        }
        res = self.client.post('/producers/', data=payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        clp1 = ProducerCLP.objects.get(code='CLP-EX-1')
        self.assertEqual(float(clp1.tonelaje_total), 100000.0)
        self.assertEqual(float(clp1.tonelaje_saldo), 100000.0)
        
        clp2 = ProducerCLP.objects.get(code='CLP-EX-2')
        self.assertEqual(float(clp2.tonelaje_total), 100000.0)
        self.assertEqual(float(clp2.tonelaje_saldo), 50000.50)

    def test_clp_saldo_defaults_to_total_when_zero_or_empty(self):
        """Verifica que si el saldo restante es 0 o no se especifica, se iguale al total a menos que se indique un saldo específico"""
        self.client.force_authenticate(user=self.user)
        payload = {
            'code': 'PROD-AUTO-SALDO',
            'name': 'Fundo Auto Saldo',
            'clp_list': [
                {
                    'code': 'CLP-AUTO-1',
                    'tonelaje_total': '100,000',
                    'tonelaje_saldo': '0'  # Ponen 0 -> debe heredar 100,000
                },
                {
                    'code': 'CLP-AUTO-2',
                    'tonelaje_total': '80,000',
                    'tonelaje_saldo': '30,000'  # Saldo específico -> se respeta 30,000
                }
            ]
        }
        res = self.client.post('/producers/', data=payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        clp1 = ProducerCLP.objects.get(code='CLP-AUTO-1')
        self.assertEqual(float(clp1.tonelaje_total), 100000.0)
        self.assertEqual(float(clp1.tonelaje_saldo), 100000.0)

        clp2 = ProducerCLP.objects.get(code='CLP-AUTO-2')
        self.assertEqual(float(clp2.tonelaje_total), 80000.0)
        self.assertEqual(float(clp2.tonelaje_saldo), 30000.0)

    def test_clp_consumed_weight_active_campaign(self):
        """Verifica que /producers/clp-consumed-weight/ calcule el peso neto consumido solo de la campaña activa excluyendo descartes"""
        import json
        from decimal import Decimal
        from inventory.models import Campaign, Product
        from reports.models import Report
        from tenants.models import Tenant

        tenant = Tenant.objects.create(name='Sede Ica Test', code='ICA-TEST')
        self.user.tenant = tenant
        self.user.save()

        product = Product.objects.create(name='Uva Test', code='UVA-TEST', tenant=tenant)
        active_campaign = Campaign.objects.create(
            name='Campaña Uva 2026',
            status=Campaign.STATUS_ACTIVE,
            product=product,
            tenant=tenant
        )
        closed_campaign = Campaign.objects.create(
            name='Campaña Uva 2025',
            status=Campaign.STATUS_CLOSED,
            product=product,
            tenant=tenant
        )

        producer = Producer.objects.create(
            code='72',
            name='INOFUENTE GUERRA CARLOS GREGORIO',
            tenant=tenant
        )
        clp = ProducerCLP.objects.create(
            producer=producer,
            code='024-39573-01',
            lugar_produccion='Fundo Villafuerte',
            tonelaje_total=Decimal('100000.00'),
            tonelaje_saldo=Decimal('100000.00')
        )

        # Recepción 1 en campaña activa: 12,129.90 kg
        Report.objects.create(
            id='rep-001',
            producto='Uva Test',
            lote='UI-396',
            totalPesoNeto=Decimal('12129.90'),
            tenant=tenant,
            campaign=active_campaign,
            datosGenerales_json=json.dumps({
                'clp': '024-39573-01',
                'productorCode': '72',
                'productor': 'INOFUENTE GUERRA CARLOS GREGORIO',
                'tipoReporte': 'normal'
            })
        )

        # Recepción 2 en campaña activa: 11,343.10 kg
        Report.objects.create(
            id='rep-002',
            producto='Uva Test',
            lote='UI-390',
            totalPesoNeto=Decimal('11343.10'),
            tenant=tenant,
            campaign=active_campaign,
            datosGenerales_json=json.dumps({
                'clp': '024-39573-01',
                'productorCode': '72',
                'productor': 'INOFUENTE GUERRA CARLOS GREGORIO',
                'tipoReporte': 'normal'
            })
        )

        # Descarte en campaña activa: 500 kg (no debe contarse)
        Report.objects.create(
            id='rep-desc-001',
            producto='Uva Test',
            lote='DESC-UI-396',
            totalPesoNeto=Decimal('500.00'),
            tenant=tenant,
            campaign=active_campaign,
            datosGenerales_json=json.dumps({
                'clp': '024-39573-01',
                'productorCode': '72',
                'productor': 'INOFUENTE GUERRA CARLOS GREGORIO',
                'tipoReporte': 'descarte',
                'reporteOrigenId': 'rep-001'
            })
        )

        # Recepción en campaña CERRADA: 5,000 kg (no debe contarse)
        Report.objects.create(
            id='rep-old-001',
            producto='Uva Test',
            lote='UI-OLD-1',
            totalPesoNeto=Decimal('5000.00'),
            tenant=tenant,
            campaign=closed_campaign,
            datosGenerales_json=json.dumps({
                'clp': '024-39573-01',
                'productorCode': '72',
                'productor': 'INOFUENTE GUERRA CARLOS GREGORIO',
                'tipoReporte': 'normal'
            })
        )

        # 1. Consulta sin CLP -> 400
        res_bad = self.client.get('/producers/clp-consumed-weight/')
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Consulta con CLP y total -> 2 recepciones, 23,473.00 kg consumidos, saldo 76,527.00 kg
        res = self.client.get(
            f'/producers/clp-consumed-weight/?clp=024-39573-01&producer_id={producer.id}&total_kg=100000'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['receptions_count'], 2)
        self.assertAlmostEqual(res.data['consumed_kg'], 23473.0, places=2)
        self.assertAlmostEqual(res.data['suggested_saldo_kg'], 76527.0, places=2)
        self.assertIn('Campaña Uva 2026', res.data['campaign_name'])

        # 3. Guardar el productor con el saldo recalculado
        update_payload = {
            'code': '72',
            'name': 'INOFUENTE GUERRA CARLOS GREGORIO',
            'clp_list': [
                {
                    'id': clp.id,
                    'code': '024-39573-01',
                    'tonelaje_total': '100,000',
                    'tonelaje_saldo': '76,527',
                    'is_custom_saldo': True
                }
            ]
        }
        res_update = self.client.put(f'/producers/{producer.id}/', data=update_payload, format='json')
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)
        clp.refresh_from_db()
        self.assertEqual(float(clp.tonelaje_saldo), 76527.0)
