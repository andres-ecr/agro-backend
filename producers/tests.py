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
