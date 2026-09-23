from django.core.management.base import BaseCommand
from licensing.services import LicenseService


class Command(BaseCommand):
    help = 'Activa una clave de licencia en el servidor y sincroniza con AlchLab Licenses'

    def add_arguments(self, parser):
        parser.add_argument('serial_key', type=str, help='Clave de licencia (ej: ALCH-XXXX-XXXX-XXXX)')

    def handle(self, *args, **options):
        serial_key = options['serial_key']
        self.stdout.write(f"Intentando activar clave: {serial_key}...")

        is_valid, status, message, meta = LicenseService.activate_serial(serial_key)

        if is_valid:
            self.stdout.write(self.style.SUCCESS(f"[EXITO] {message} [Estado: {status}]"))
            if meta.get('lease_until'):
                self.stdout.write(f"   Lease valido hasta: {meta['lease_until']}")
        else:
            self.stdout.write(self.style.ERROR(f"[ERROR] {message} [Estado: {status}]"))

