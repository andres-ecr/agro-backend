import json
from django.core.management.base import BaseCommand
from django.db import transaction
from reports.models import Report


class Command(BaseCommand):
    help = 'Sanitize descarte reports by removing invalid pesoGuia and diferenciaPeso fields from datosGenerales_json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the cleanup without modifying the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.stdout.write(self.style.NOTICE(f"Iniciando saneamiento de reportes de descarte (dry_run={dry_run})..."))

        count_total = 0
        count_descartes = 0
        count_cleaned = 0

        with transaction.atomic():
            for report in Report.objects.all():
                count_total += 1
                if not report.datosGenerales_json:
                    continue

                try:
                    data = json.loads(report.datosGenerales_json)
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"Ignorando reporte {report.id}: JSON no válido ({exc})"))
                    continue

                is_descarte = (
                    data.get('tipoReporte') == 'descarte'
                    or str(report.lote or '').startswith('DESC-')
                    or str(data.get('carga') or '').startswith('DESC-')
                    or str(data.get('lote') or '').startswith('DESC-')
                )

                if is_descarte:
                    count_descartes += 1
                    had_peso_guia = 'pesoGuia' in data
                    had_diff_peso = 'diferenciaPeso' in data

                    if had_peso_guia or had_diff_peso:
                        data.pop('pesoGuia', None)
                        data.pop('diferenciaPeso', None)
                        if not dry_run:
                            report.datosGenerales_json = json.dumps(data)
                            report.save(update_fields=['datosGenerales_json'])
                        count_cleaned += 1
                        self.stdout.write(
                            f"[{'SIMULADO' if dry_run else 'CORREGIDO'}] Reporte {report.id} ({report.lote}): "
                            f"removido pesoGuia={had_peso_guia}, diferenciaPeso={had_diff_peso}"
                        )

            if dry_run:
                self.stdout.write(self.style.WARNING("Modo simulación (dry-run): rollback de cambios."))
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"Proceso finalizado. Total analizados: {count_total}, Descartes detectados: {count_descartes}, Corregidos: {count_cleaned}"
        ))
