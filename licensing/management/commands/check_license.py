from django.core.management.base import BaseCommand
from licensing.services import LicenseService
from licensing.models import LicenseState


class Command(BaseCommand):
    help = 'Inspecciona el estado de la licencia local y la huella de la maquina'

    def handle(self, *args, **options):
        state = LicenseState.get_instance()
        is_valid, status, message, meta = LicenseService.check_license()

        self.stdout.write("=" * 60)
        self.stdout.write("DIAGNOSTICO DE LICENCIA ON-PREMISE")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Clave Serial         : {state.serial_key or 'Sin asignar'}")
        self.stdout.write(f"Identificador Maquina: {state.machine_id}")
        self.stdout.write(f"Cliente Registrado   : {state.customer_name or 'N/A'}")
        self.stdout.write(f"Estado de Validacion : {status.upper()}")
        self.stdout.write(f"Autorizado a operar  : {'SI' if is_valid else 'NO'}")
        self.stdout.write(f"Es Perpetua          : {'SI' if state.is_perpetual else 'NO'}")
        self.stdout.write(f"Vencimiento de Lease : {state.lease_until or 'N/A'}")
        self.stdout.write(f"Ultimo Heartbeat     : {state.last_heartbeat_at or 'N/A'}")
        self.stdout.write(f"Horas de Gracia      : {state.grace_period_hours} horas")
        if state.last_sync_error:
            self.stdout.write(f"Ultima Advertencia   : {state.last_sync_error}")
        self.stdout.write("=" * 60)
