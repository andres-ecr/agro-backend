from datetime import timedelta
from django.test import TestCase, Client
from django.utils import timezone
from .models import LicenseState
from .services import LicenseService


class LicensingTests(TestCase):
    def setUp(self):
        LicenseState.objects.all().delete()
        self.client = Client()

    def test_unlicensed_state_blocks_api(self):
        state = LicenseState.get_instance()
        state.serial_key = ''
        state.is_perpetual = False
        state.save()

        is_valid, status, message, meta = LicenseService.check_license()
        self.assertFalse(is_valid)
        self.assertEqual(status, 'unlicensed')

        # Request to a protected API endpoint returns 402
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.json()['error'], 'LICENSE_SUSPENDED')

    def test_perpetual_license_allows_api_without_server(self):
        state = LicenseState.get_instance()
        state.is_perpetual = True
        state.serial_key = 'ALCH-PERPETUAL-KEY-TEST'
        state.save()

        is_valid, status, message, meta = LicenseService.check_license()
        self.assertTrue(is_valid)
        self.assertEqual(status, 'perpetual')
        self.assertTrue(meta['is_perpetual'])

    def test_offline_grace_period_within_48_hours(self):
        state = LicenseState.get_instance()
        state.serial_key = 'ALCH-TEST-KEY-1234'
        state.is_perpetual = False
        # Last heartbeat was 12 hours ago
        state.last_heartbeat_at = timezone.now() - timedelta(hours=12)
        state.grace_period_hours = 48
        state.save()

        is_valid, status, message, meta = LicenseService.check_license()
        self.assertTrue(is_valid)
        self.assertEqual(status, 'grace_period')
        self.assertGreater(meta.get('hours_remaining', 0), 30)

    def test_offline_grace_period_expired_after_48_hours(self):
        state = LicenseState.get_instance()
        state.serial_key = 'ALCH-TEST-KEY-1234'
        state.is_perpetual = False
        # Last heartbeat was 49 hours ago
        state.last_heartbeat_at = timezone.now() - timedelta(hours=49)
        state.grace_period_hours = 48
        state.save()

        is_valid, status, message, meta = LicenseService.check_license()
        self.assertFalse(is_valid)
        self.assertEqual(status, 'expired')

    def test_clock_tampering_detection(self):
        state = LicenseState.get_instance()
        state.serial_key = 'ALCH-TEST-KEY-1234'
        state.is_perpetual = False
        # Set monotonic timestamp to 10 hours in the future
        state.last_monotonic_timestamp = timezone.now() + timedelta(hours=10)
        state.save()

        is_valid, status, message, meta = LicenseService.check_license()
        self.assertFalse(is_valid)
        self.assertEqual(status, 'expired')
        self.assertTrue(meta.get('tampered', False))
