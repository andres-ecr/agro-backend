from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .services import LicenseService
from .models import LicenseState


class LicenseStatusView(APIView):
    """
    Publicly or authenticated readable endpoint to inspect current local license status.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        is_valid, lic_status, message, meta = LicenseService.check_license()
        state = LicenseState.get_instance()

        masked_key = ''
        if state.serial_key:
            parts = state.serial_key.split('-')
            masked_key = f"{parts[0]}-****-****-{parts[-1]}" if len(parts) > 2 else '****'

        return Response({
            'valid': is_valid,
            'status': lic_status,
            'message': message,
            'serialKey': masked_key,
            'machineId': state.machine_id,
            'customerName': state.customer_name,
            'isPerpetual': state.is_perpetual,
            'leaseUntil': state.lease_until.isoformat() if state.lease_until else None,
            'lastHeartbeatAt': state.last_heartbeat_at.isoformat() if state.last_heartbeat_at else None,
            'gracePeriodHours': state.grace_period_hours,
            'lastSyncError': state.last_sync_error,
            'meta': meta,
        })


class LicenseActivateView(APIView):
    """
    Sets a new serial key and immediately validates against the license server.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serial_key = request.data.get('serialKey') or request.data.get('serial_key')
        if not serial_key:
            return Response(
                {'error': 'Se requiere el campo serialKey.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_valid, lic_status, message, meta = LicenseService.activate_serial(serial_key)

        return Response({
            'valid': is_valid,
            'status': lic_status,
            'message': message,
            'meta': meta,
        }, status=status.HTTP_200_OK if is_valid else status.HTTP_400_BAD_REQUEST)


class LicenseSyncView(APIView):
    """
    Forces an immediate remote heartbeat synchronization.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        is_valid, lic_status, message, meta = LicenseService.sync_heartbeat(force=True)

        return Response({
            'valid': is_valid,
            'status': lic_status,
            'message': message,
            'meta': meta,
        })
