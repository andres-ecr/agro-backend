from django.core.management.base import BaseCommand
from seed_prod import reset_production_to_base


class Command(BaseCommand):
    help = "Reinicia la base de datos a modo base de producción limpio (0 datos de prueba)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            type=str,
            default=None,
            help='Contraseña inicial para los usuarios oficiales.'
        )

    def handle(self, *args, **options):
        password = options.get('password', None)
        reset_production_to_base(default_password=password)
        self.stdout.write(self.style.SUCCESS("Comando reset_prod_base completado exitosamente."))
