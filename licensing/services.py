import json
import logging
import socket
import urllib.request
import urllib.error
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import LicenseState

logger = logging.getLogger(__name__)

# Default License Server URL (can be overridden in settings.py or .env)
DEFAULT_LICENSE_SERVER = getattr(
    settings,
    'ALCHLAB_LICENSE_SERVER_URL',
    'http://localhost:3001'
)


class LicenseService:
    @staticmethod
    def get_state():
        return LicenseState.get_instance()

    @classmethod
    def check_license(cls, force_sync=False):
        """
        Evaluates the local license state, lease validity, and offline grace timer.
        Returns:
            is_valid (bool): True if system is authorized to process requests.
            status (str): 'active', 'grace_period', 'suspended', 'expired', 'unlicensed'
            message (str): Human-readable status description.
            meta (dict): Additional information (hours remaining, machineId, etc.)
        """
        state = cls.get_state()
        now = timezone.now()

        # 1. PERPETUAL OVERRIDE: If customer completed all milestone payments,
        # the software operates indefinitely without any remote calls.
        if state.is_perpetual:
            return True, 'perpetual', 'Licencia perpetua activa.', {
                'is_perpetual': True,
                'customer_name': state.customer_name,
                'serial_key': state.serial_key,
                'machine_id': state.machine_id,
            }

        # 2. Check if a serial key is configured
        if not state.serial_key:
            return False, 'unlicensed', 'No se ha configurado una clave de licencia en este servidor.', {
                'is_perpetual': False,
                'machine_id': state.machine_id,
            }

        # 3. ANTI-CLOCK-TAMPERING: Ensure system clock was not wound backward
        if state.last_monotonic_timestamp and now < state.last_monotonic_timestamp:
            # Clock was rolled back!
            logger.error("Tampering detected: system clock is earlier than last recorded timestamp.")
            state.status = 'expired'
            state.last_sync_error = "Manipulación de reloj del sistema detectada."
            state.save()
            return False, 'expired', 'Se detectó manipulación en el reloj del sistema operativo. Regularice la hora del servidor.', {
                'tampered': True,
                'machine_id': state.machine_id,
            }

        # Update monotonic forward timestamp
        state.last_monotonic_timestamp = now

        # 4. Check if current lease is active and fresh
        lease_valid = state.lease_until and now < state.lease_until
        recent_heartbeat = state.last_heartbeat_at and (now - state.last_heartbeat_at).total_seconds() < 3600

        # If lease is valid and heartbeat was checked within the last hour, pass immediately without network call
        if lease_valid and recent_heartbeat and not force_sync:
            return True, state.status, 'Licencia activa.', {
                'lease_until': state.lease_until.isoformat() if state.lease_until else None,
                'machine_id': state.machine_id,
            }

        # 5. Heartbeat check against remote license server
        return cls.sync_heartbeat(state, force=force_sync)

    @classmethod
    def sync_heartbeat(cls, state=None, force=False):
        """
        Attempts to contact the remote AlchLab License Server to renew the lease using standard urllib.
        Falls back to offline grace period (48h) if connection is unavailable.
        """
        if state is None:
            state = cls.get_state()

        now = timezone.now()
        server_url = getattr(settings, 'ALCHLAB_LICENSE_SERVER_URL', DEFAULT_LICENSE_SERVER).rstrip('/')
        endpoint = f"{server_url}/api/licenses/heartbeat"

        hostname = socket.gethostname() or 'Agro-ERP-Server'
        payload = {
            'serialKey': state.serial_key,
            'machineId': state.machine_id,
            'hostname': hostname,
            'appVersion': '1.0.0',
        }
        json_data = json.dumps(payload).encode('utf-8')

        req = urllib.request.Request(
            endpoint,
            data=json_data,
            headers={'Content-Type': 'application/json', 'User-Agent': 'Agro-ERP-Client/1.0'}
        )

        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                status_code = response.getcode()
                raw_body = response.read().decode('utf-8')
                data = json.loads(raw_body) if raw_body else {}

                if status_code == 200 and data.get('valid'):
                    # Successful heartbeat! Update lease
                    state.status = 'active'
                    state.customer_name = data.get('customerName', state.customer_name)
                    state.grace_period_hours = data.get('gracePeriodHours', 48)

                    if data.get('leaseUntil'):
                        state.lease_until = parse_datetime(data['leaseUntil'])
                    else:
                        state.lease_until = now + timedelta(hours=state.grace_period_hours)

                    state.last_heartbeat_at = now
                    state.cached_token = data.get('token', '')
                    state.last_sync_error = ''
                    state.save()

                    return True, 'active', 'Lease de licencia renovado exitosamente.', {
                        'lease_until': state.lease_until.isoformat() if state.lease_until else None,
                        'grace_period_hours': state.grace_period_hours,
                        'customer_name': state.customer_name,
                        'machine_id': state.machine_id,
                    }

        except urllib.error.HTTPError as http_err:
            try:
                error_body = http_err.read().decode('utf-8')
                data = json.loads(error_body)
            except Exception:
                data = {}

            if http_err.code in (400, 403, 404):
                remote_status = data.get('status', 'suspended')
                state.status = remote_status
                state.lease_until = now # Expire lease immediately
                state.last_sync_error = data.get('message', 'Licencia suspendida por el servidor.')
                state.save()

                return False, remote_status, state.last_sync_error, {
                    'server_rejected': True,
                    'status': remote_status,
                    'machine_id': state.machine_id,
                }
            else:
                state.last_sync_error = f"HTTP Error {http_err.code}: {http_err.reason}"
                state.save()

        except Exception as exc:
            # NETWORK OR SERVER UNAVAILABLE: Evaluate offline grace period!
            logger.warning(f"Could not reach license server ({endpoint}): {exc}. Checking offline grace period.")
            state.last_sync_error = f"Sin conexión con servidor de licencias ({str(exc)[:100]})"

        # Offline fallback logic
        grace_seconds = state.grace_period_hours * 3600
        elapsed_seconds = (now - state.last_heartbeat_at).total_seconds() if state.last_heartbeat_at else grace_seconds + 1

        if elapsed_seconds <= grace_seconds:
            # Still inside the 48-hour offline window!
            remaining_hours = max(0, int((grace_seconds - elapsed_seconds) / 3600))
            state.status = 'grace_period'
            state.save()

            return True, 'grace_period', f"Operando en modo de gracia offline ({remaining_hours} horas restantes).", {
                'in_grace_period': True,
                'hours_remaining': remaining_hours,
                'machine_id': state.machine_id,
                'last_heartbeat_at': state.last_heartbeat_at.isoformat() if state.last_heartbeat_at else None,
            }
        else:
            # Exceeded 48 hours without connecting to internet/server
            state.status = 'expired'
            state.save()

            return False, 'expired', f"Se agotó el período de gracia offline de {state.grace_period_hours} horas. Conecte el servidor a internet para reactivar.", {
                'grace_expired': True,
                'machine_id': state.machine_id,
            }

    @classmethod
    def activate_serial(cls, serial_key):
        """Sets a new serial key and performs immediate validation."""
        state = cls.get_state()
        state.serial_key = serial_key.strip().upper()
        state.is_perpetual = False
        state.save()
        return cls.sync_heartbeat(state, force=True)

    @classmethod
    def make_perpetual(cls):
        """Disables remote checks permanently (100% paid in full)."""
        state = cls.get_state()
        state.is_perpetual = True
        state.status = 'active'
        state.lease_until = None
        state.save()
        return True, "Licencia convertida a Perpetua de forma permanente."
