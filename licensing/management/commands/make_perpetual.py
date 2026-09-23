from django.core.management.base import BaseCommand
from licensing.services import LicenseService


class Command(BaseCommand):
    help = 'Convierte la instalación local en Licencia Perpetua (Liquidación 100% completada)'

    def handle(self, *args, **options):
        success, message = LicenseService.make_perpetual()
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("[EXITO] LICENCIA PERPETUA ACTIVADA"))
        self.stdout.write(self.style.SUCCESS(f"   {message}"))
        self.stdout.write("   El sistema no requerira validacion remota ni conexion a internet.")
        self.stdout.write(self.style.SUCCESS("=" * 60))
