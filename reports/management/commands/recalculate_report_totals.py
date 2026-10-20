import json
from decimal import Decimal, ROUND_HALF_UP
from django.core.management.base import BaseCommand
from reports.models import Report


class Command(BaseCommand):
    help = 'Recalculates totalPesoNeto, promedioPorJaba, and diferenciaPeso for historical reports to ensure accounting consistency'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Inspect and print discrepancies without modifying the database',
        )
        parser.add_argument(
            '--carga',
            type=str,
            default=None,
            help='Target a specific carga/lote (e.g. UI-351)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_carga = options.get('carga')

        queryset = Report.objects.all().order_by('id')
        if target_carga:
            queryset = queryset.filter(lote=target_carga)

        total_reports = queryset.count()
        corrected = 0

        self.stdout.write(f"Evaluating {total_reports} reports (dry_run={dry_run})...")

        for report in queryset:
            changed = False
            totales = {}
            datos_generales = {}

            if report.totales_json:
                try:
                    totales = json.loads(report.totales_json)
                except Exception:
                    totales = {}

            if report.datosGenerales_json:
                try:
                    datos_generales = json.loads(report.datosGenerales_json)
                except Exception:
                    datos_generales = {}

            try:
                pb = Decimal(str(totales.get('totalPesoBruto', '0.0'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                pp = Decimal(str(totales.get('totalPesoParihuela', '0.0'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                tr = Decimal(str(totales.get('totalTara', '0.0'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                jabas = int(totales.get('totalJabas', 0) or 0)
            except Exception:
                continue

            if pb <= 0 or (pp <= 0 and tr <= 0):
                continue

            expected_neto = max(Decimal('0.00'), pb - pp - tr).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            current_neto_field = report.totalPesoNeto
            try:
                current_neto_json = Decimal(str(totales.get('totalPesoNeto', '0.0'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except Exception:
                current_neto_json = None

            if current_neto_field != expected_neto or current_neto_json != expected_neto:
                self.stdout.write(
                    f"Discrepancy in report {report.id} (lote: {report.lote}): "
                    f"current field={current_neto_field}, current json={current_neto_json} -> expected={expected_neto}"
                )
                report.totalPesoNeto = expected_neto
                totales['totalPesoNeto'] = str(expected_neto)
                changed = True

            if jabas > 0:
                expected_ppj = (expected_neto / Decimal(jabas)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                current_ppj = totales.get('promedioPorJaba')
                if str(current_ppj) != str(expected_ppj):
                    totales['promedioPorJaba'] = str(expected_ppj)
                    changed = True

            is_descarte = (
                datos_generales.get('tipoReporte') == 'descarte'
                or str(report.lote or '').startswith('DESC-')
                or str(datos_generales.get('carga', '')).startswith('DESC-')
            )
            if not is_descarte and datos_generales.get('pesoGuia') not in (None, ''):
                try:
                    peso_guia = Decimal(str(datos_generales['pesoGuia']))
                    expected_diff = (expected_neto - peso_guia).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    current_diff = datos_generales.get('diferenciaPeso')
                    if str(current_diff) != str(expected_diff):
                        self.stdout.write(
                            f"  diferenciaPeso in {report.lote}: {current_diff} -> {expected_diff}"
                        )
                        datos_generales['diferenciaPeso'] = str(expected_diff)
                        changed = True
                except Exception:
                    pass

            if changed:
                corrected += 1
                if not dry_run:
                    report.totales_json = json.dumps(totales)
                    report.datosGenerales_json = json.dumps(datos_generales)
                    report.save(update_fields=['totalPesoNeto', 'totales_json', 'datosGenerales_json'])

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed. {corrected} reports {'would be' if dry_run else 'were'} recalculated and updated."
            )
        )
