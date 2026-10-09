from django.core.management.base import BaseCommand
from import_listado_csv import import_csv


class Command(BaseCommand):
    help = "Importa productores, códigos CLP y empresas de transporte desde un archivo LISTADO.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default=None,
            help="Ruta al archivo LISTADO.csv (si no se especifica, busca en data/LISTADO.csv)"
        )
        parser.add_argument(
            '--tenant',
            type=str,
            default="ica",
            help="Código de la sede a la que se asignarán los maestros (default: ica)"
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Simula la importación sin escribir en la base de datos"
        )

    def handle(self, *args, **options):
        file_path = options.get('file')
        tenant_code = options.get('tenant')
        dry_run = options.get('dry_run', False)

        import_csv(file_path=file_path, tenant_code=tenant_code, dry_run=dry_run)
        self.stdout.write(self.style.SUCCESS("Proceso de importación finalizado."))
