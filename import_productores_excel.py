"""
Script de importación masiva de Productores y CLPs desde Excel (CODIGOS.xlsx).

Reglas de negocio:
- Cada fila representa un Productor con su respectivo CLP (1 a 1 por fila).
- El código del productor se forma con el prefijo 'CP-' y el número de fila 'N°' (ej: CP-1, CP-2, CP-1953).
- Todos los productores se asignan a la sede Casma (tenant 'casma').
- El departamento se descarta por ser innecesario según la definición del negocio.
- Incluye soporte para --dry-run (modo prueba sin escribir en BD) y --limit N.

Uso:
    python import_productores_excel.py [--file RUTA_EXCEL] [--tenant casma] [--dry-run] [--limit N]
"""

import os
import sys
import re
import argparse
from decimal import Decimal

# Configurar encoding UTF-8 en stdout para terminales Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Setup Django si se ejecuta como script independiente
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()

import openpyxl
from django.db import transaction
from tenants.models import Tenant
from producers.models import Producer, ProducerCLP


def clean_text(val):
    if val is None:
        return ''
    s = str(val).strip()
    s = re.sub(r'\s+', ' ', s)
    return s


def resolve_excel_path(candidate_path=None):
    if candidate_path and os.path.exists(candidate_path):
        return candidate_path

    paths = [
        os.path.join(BASE_DIR, 'data', 'CODIGOS.xlsx'),
        os.path.join(os.path.expanduser('~'), 'Downloads', 'CODIGOS.xlsx'),
        os.path.join(BASE_DIR, 'CODIGOS.xlsx'),
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return os.path.join(BASE_DIR, 'data', 'CODIGOS.xlsx')


def import_excel(file_path=None, tenant_code='casma', dry_run=False, limit=None):
    excel_path = resolve_excel_path(file_path)

    print("==================================================================")
    print("   IMPORTACIÓN DE PRODUCTORES DESDE EXCEL (CP-X)")
    print(f"   Archivo:       {excel_path}")
    print(f"   Sede / Tenant: {tenant_code}")
    print(f"   Modo Dry-Run:  {'SÍ (Simulación en memoria sin guardar)' if dry_run else 'NO (Guardando en BD)'}")
    if limit:
        print(f"   Límite:        {limit} filas")
    print("==================================================================")

    if not os.path.exists(excel_path):
        print(f"\n[ERROR] No se encontró el archivo Excel en: {excel_path}")
        return False

    try:
        tenant = Tenant.objects.get(code=tenant_code)
    except Tenant.DoesNotExist:
        print(f"\n[ERROR] No existe la sede con código '{tenant_code}'.")
        print(f"Sedes disponibles: {[t.code for t in Tenant.objects.all()]}")
        return False

    print(f"\n[1/3] Abriendo y leyendo '{os.path.basename(excel_path)}'...")
    wb = openpyxl.load_workbook(excel_path, read_only=True)
    sheet_name = 'Hoja1' if 'Hoja1' in wb.sheetnames else wb.sheetnames[0]
    ws = wb[sheet_name]

    rows_iter = ws.iter_rows(values_only=True)
    try:
        headers = next(rows_iter)
    except StopIteration:
        print("[ERROR] El archivo Excel está completamente vacío.")
        return False

    all_data = list(rows_iter)
    total_filas = len(all_data)
    if limit and limit > 0:
        all_data = all_data[:limit]

    print(f"[OK] Hoja '{sheet_name}' leída. Total filas detectadas: {total_filas}. A procesar: {len(all_data)}")
    print(f"\n[2/3] Procesando e importando registros a Sede {tenant.name} ({tenant.code})...")

    # Pre-cargar cachés para verificación de duplicados y protección de registros existentes
    existing_codes = set(Producer.objects.values_list('code', flat=True))
    existing_clps = set(ProducerCLP.objects.values_list('code', flat=True)) | set(
        Producer.objects.exclude(clp__isnull=True).exclude(clp='').values_list('clp', flat=True)
    )

    print(f"  -> Verificación previa: {len(existing_codes)} códigos y {len(existing_clps)} CLPs ya existentes en BD.")

    producers_created = 0
    producers_skipped = 0
    clps_created = 0
    errors = 0

    with transaction.atomic():
        for idx, row in enumerate(all_data, start=1):
            try:
                # Columnas: N°, COD. DE PRODUCTOR, PRODUCTOR, LUGAR DE PRODUCION, DISTRITO, PROVINCIA, DEPARTAMENTO
                raw_n = row[0] if len(row) > 0 else None
                raw_clp = row[1] if len(row) > 1 else ''
                raw_prod = row[2] if len(row) > 2 else ''
                raw_lugar = row[3] if len(row) > 3 else ''
                raw_dist = row[4] if len(row) > 4 else ''
                raw_prov = row[5] if len(row) > 5 else ''

                if raw_n is None or str(raw_n).strip() == '':
                    continue

                # Código con prefijo CP- (ej: CP-1, CP-2, etc.)
                clean_n = str(raw_n).strip()
                if clean_n.endswith('.0'):
                    clean_n = clean_n[:-2]
                prod_code = f"CP-{clean_n}"

                prod_name = clean_text(raw_prod).upper()
                clp_code = clean_text(raw_clp).upper()
                lugar = clean_text(raw_lugar)
                distrito = clean_text(raw_dist).upper()
                provincia = clean_text(raw_prov).upper()

                # Normalización de dirección
                address_parts = []
                if lugar and lugar != '—' and lugar != '-':
                    address_parts.append(lugar)
                if distrito:
                    address_parts.append(distrito)
                if provincia and provincia != distrito:
                    address_parts.append(provincia)
                address = ', '.join(address_parts)

                if not prod_name or not clp_code:
                    print(f"  [ALERTA] Fila {idx}: Faltan datos esenciales. N°={clean_n}, CLP='{clp_code}', Prod='{prod_name}'")
                    errors += 1
                    continue

                # ==============================================================
                # REGLAS DE PROTECCIÓN: SALTEAR SI YA EXISTE EN BD
                # ==============================================================
                # 1. Si el código CLP ya existe en BD (ej. productores ya registrados en planta)
                if clp_code in existing_clps:
                    print(f"  [SKIP] CLP '{clp_code}' ({prod_name}) ya existe en BD. Omitiendo fila {clean_n}.")
                    producers_skipped += 1
                    continue

                # 2. Si el código CP-X ya está ocupado en la BD
                if prod_code in existing_codes:
                    print(f"  [SKIP] Código '{prod_code}' ya está asignado en BD. Omitiendo fila {clean_n} ({prod_name}) para no sobreescribir.")
                    producers_skipped += 1
                    continue

                if not dry_run:
                    # 1. Crear Productor
                    producer = Producer.objects.create(
                        code=prod_code,
                        name=prod_name,
                        clp=clp_code,
                        address=address or lugar or distrito,
                        tenant=tenant,
                    )
                    producers_created += 1

                    # 2. Crear CLP del Productor
                    ProducerCLP.objects.create(
                        producer=producer,
                        code=clp_code,
                        lugar_produccion=lugar if lugar != '—' else '',
                        distrito=distrito,
                        is_active=True,
                    )
                    clps_created += 1

                    # Actualizar cachés en memoria
                    existing_codes.add(prod_code)
                    existing_clps.add(clp_code)

                else:
                    # Simulación
                    producers_created += 1
                    clps_created += 1
                    existing_codes.add(prod_code)
                    existing_clps.add(clp_code)

                # Progreso visual cada 250 filas
                if idx % 250 == 0 or idx == len(all_data):
                    print(f"  -> Progreso: {idx}/{len(all_data)} procesados ({prod_code} - {prod_name[:35]}...)")

            except Exception as e:
                print(f"  [ERROR] Fila {idx}: Falló la importación: {e}")
                errors += 1

        if dry_run:
            print("\n[MODO DRY-RUN] Revertiendo cualquier cambio simulado...")
            transaction.set_rollback(True)

    print("\n==================================================================")
    print("   RESUMEN DE IMPORTACIÓN DE PRODUCTORES")
    print(f"   Total filas evaluadas: {len(all_data)}")
    if not dry_run:
        print(f"   Productores creados:   {producers_created}")
        print(f"   Productores salteados: {producers_skipped}")
        print(f"   CLPs creados:          {clps_created}")
    else:
        print(f"   Productores simulados: {producers_created}")
        print(f"   Productores salteados: {producers_skipped}")
        print(f"   CLPs simulados:        {clps_created}")
    print(f"   Errores u omitidos:    {errors}")
    print("==================================================================")
    return True
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Importar productores y CLPs desde Excel (CODIGOS.xlsx)")
    parser.add_argument('--file', help="Ruta al archivo Excel (.xlsx)")
    parser.add_argument('--tenant', default='casma', help="Código de la sede (default: casma)")
    parser.add_argument('--dry-run', action='store_true', help="Ejecutar simulación sin guardar en la BD")
    parser.add_argument('--limit', type=int, default=None, help="Límite de filas a importar (para pruebas)")
    args = parser.parse_args()

    import_excel(
        file_path=args.file,
        tenant_code=args.tenant,
        dry_run=args.dry_run,
        limit=args.limit
    )
