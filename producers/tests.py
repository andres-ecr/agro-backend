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
