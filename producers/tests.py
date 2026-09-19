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
                {'code': 'CLP-001', 'lugar_produccion': 'Lote Norte'},
                {'code': 'CLP-002', 'lugar_produccion': 'Lote Sur'},
            ]
        }
        response = self.client.post('/producers/', data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Producer.objects.count(), 1)
        self.assertEqual(ProducerCLP.objects.count(), 2)

        producer = Producer.objects.first()
        self.assertEqual(producer.clp_list.count(), 2)
        codes = list(producer.clp_list.values_list('code', flat=True))
        self.assertIn('CLP-001', codes)
        self.assertIn('CLP-002', codes)

    def test_update_producer_clp_list(self):
        producer = Producer.objects.create(code='PROD-002', name='Agricola Verde')
        clp1 = ProducerCLP.objects.create(producer=producer, code='CLP-A', lugar_produccion='Sector 1')
        clp2 = ProducerCLP.objects.create(producer=producer, code='CLP-B', lugar_produccion='Sector 2')

        # Update: keep CLP-A (update name), remove CLP-B, add CLP-C
        payload = {
            'code': 'PROD-002',
            'name': 'Agricola Verde SAC',
            'clp_list': [
                {'id': clp1.id, 'code': 'CLP-A-MOD', 'lugar_produccion': 'Sector 1 Modificado'},
                {'code': 'CLP-C', 'lugar_produccion': 'Sector Nuevo'},
            ]
        }
        response = self.client.put(f'/producers/{producer.id}/', data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        producer.refresh_from_db()
        self.assertEqual(producer.name, 'Agricola Verde SAC')
        self.assertEqual(producer.clp_list.count(), 2)
        codes = list(producer.clp_list.values_list('code', flat=True))
        self.assertIn('CLP-A-MOD', codes)
        self.assertIn('CLP-C', codes)
        self.assertNotIn('CLP-B', codes)

    def test_list_producers_includes_clp_list(self):
        producer = Producer.objects.create(code='PROD-003', name='Valle Hermoso')
        ProducerCLP.objects.create(producer=producer, code='CLP-VH1')

        response = self.client.get('/producers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        item = [p for p in results if p['code'] == 'PROD-003'][0]
        self.assertIn('clp_list', item)
        self.assertEqual(len(item['clp_list']), 1)
        self.assertEqual(item['clp_list'][0]['code'], 'CLP-VH1')
