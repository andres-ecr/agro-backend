"""
Script de importación de Productores, CLPs y Transportistas desde CSV (LISTADO.csv).

Limpia y procesa automáticamente:
- PRODUCTOR: separa el nombre del código (elimina el '/' o sufijo numérico).
- CÓDIGO INTERNO: asigna el código interno (1, 2, 4.1, 4.2, 30.1, etc.).
- CAMPO: asigna la dirección y lugar de producción.
- CLP: normaliza y asigna el código oficial de lugar de producción.
- CAMIÓN: separa marca y placa con formato normalizado (ej. VOLVO V2U-839).
- CHOFER / BREVETE: separa el nombre del chofer y su número de brevete.
- RAZÓN SOCIAL TRANSPORTISTA: crea o vincula la empresa de transporte.

Uso:
    python import_listado_csv.py [--file RUTA_CSV] [--tenant ica] [--dry-run]
"""

import os
import sys
import csv
import re
import argparse

# Configurar encoding UTF-8 en stdout para terminales Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup Django si se ejecuta como script independiente
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()

from django.db import transaction
from tenants.models import Tenant
from producers.models import Producer, ProducerCLP
from transporte.models import TransportCompany, Driver, Vehicle


def clean_plate(raw_plate):
    """Normaliza placas peruanas a formato XXX-XXX cuando corresponda."""
    if not raw_plate:
        return ''
    p = raw_plate.strip().upper().replace(' ', '')
    m = re.match(r'^([A-Z0-9]{3})-?([A-Z0-9]{3,4})$', p)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return p


def clean_truck(camion_str):
    """Separa y normaliza marca y placa desde el texto de camión."""
    if not camion_str:
        return ('', '')
    raw = camion_str.strip()
    brand = ''
    plate = ''

    if '/' in raw:
        parts = [p.strip() for p in raw.split('/', 1)]
        brand = parts[0]
        plate = clean_plate(parts[1])
    else:
        parts = raw.split(None, 1)
        if len(parts) == 2:
            brand = parts[0]
            plate = clean_plate(parts[1])
        else:
            plate = clean_plate(raw)

    return (brand.upper(), plate)


def clean_driver(chofer_str):
    """Separa nombre de chofer y número de licencia/brevete."""
    if not chofer_str:
        return ('', '')
    raw = chofer_str.strip()
    name = ''
    license_num = ''

    if '/' in raw:
        parts = [p.strip() for p in raw.split('/', 1)]
        name = parts[0]
        license_num = parts[1].replace(' ', '').upper()
    elif '-' in raw:
        parts = [p.strip() for p in raw.rsplit('-', 1)]
        name = parts[0]
        license_num = parts[1].replace(' ', '').upper()
    else:
        name = raw

    name = re.sub(r'\s+', ' ', name).strip().upper()
    return (name, license_num)


def clean_clp(clp_str):
    """Normaliza códigos CLP."""
    if not clp_str:
        return ''
    c = re.sub(r'\s+', '', clp_str)
    m = re.match(r'^(\d{3})(\d{5})-(\d{2})$', c)
    if m:
        c = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return c


def clean_producer(raw_prod, cod_interno):
    """Limpia el nombre del productor y extrae su código interno."""
    raw_prod = raw_prod.strip()
    code = cod_interno.strip()
    name = raw_prod

    if '/' in raw_prod:
        parts = [p.strip() for p in raw_prod.split('/', 1)]
        name = parts[0]
        if not code:
            code = parts[1]
    else:
        if code and name.endswith(code):
            name = name[:-len(code)].strip()

    name = re.sub(r'\s+', ' ', name).strip().upper()
    name = name.rstrip(' .')
    return (code, name)


def resolve_csv_path(given_path):
    """Resuelve la ruta del CSV buscando en la ruta dada o en data/LISTADO.csv."""
    if given_path and os.path.exists(given_path):
        return given_path
    local_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'LISTADO.csv')
    if os.path.exists(local_data):
        return local_data
    return given_path


def import_csv(file_path=None, tenant_code='ica', dry_run=False):
    file_path = resolve_csv_path(file_path)
    print("==================================================================")
    print("   IMPORTACIÓN DE MAESTROS DESDE CSV")
    print(f"   Archivo: {file_path}")
    print(f"   Sede / Tenant: {tenant_code}")
    print(f"   Modo Dry-Run: {'SÍ (Sin cambios)' if dry_run else 'NO (Guardando en BD)'}")
    print("==================================================================")

    if not os.path.exists(file_path):
        print(f"\n[ERROR] El archivo '{file_path}' no existe.")
        return

    try:
        tenant = Tenant.objects.get(code=tenant_code)
    except Tenant.DoesNotExist:
        print(f"\n[ERROR] No existe la sede con código '{tenant_code}'.")
        print(f"Sedes disponibles: {[t.code for t in Tenant.objects.all()]}")
        return

    with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f, delimiter=';')
        rows = list(reader)

    if not rows:
        print("[ERROR] El archivo CSV está vacío.")
        return

    print(f"\n[1/3] Parseando {len(rows) - 1} filas del CSV...")

    producers_created = 0
    clps_created = 0
    transport_created = 0
    drivers_created = 0
    vehicles_created = 0

    transporters_cache = {}

    with transaction.atomic():
        for idx, r in enumerate(rows[1:], start=2):
            if not r or not any(field.strip() for field in r):
                continue

            raw_prod = r[0] if len(r) > 0 else ''
            campo = r[1].strip() if len(r) > 1 else ''
            clp = r[2].strip() if len(r) > 2 else ''
            camion = r[4].strip() if len(r) > 4 else ''
            transp = r[5].strip() if len(r) > 5 else ''
            chofer = r[6].strip() if len(r) > 6 else ''
            cod_interno = r[7].strip() if len(r) > 7 else ''

            prod_code, prod_name = clean_producer(raw_prod, cod_interno)
            clean_c = clean_clp(clp)
            truck_brand, truck_plate = clean_truck(camion)
            driver_name, driver_lic = clean_driver(chofer)

            if not prod_code or not prod_name:
                print(f"  [ALERTA] Fila {idx}: No se pudo determinar código o nombre. Ignorando: {r}")
                continue

            # 1. Productor
            if not dry_run:
                producer, _ = Producer.objects.update_or_create(
                    code=prod_code,
                    tenant=tenant,
                    defaults={
                        'name': prod_name,
                        'clp': clean_c,
                        'address': campo,
                    }
                )
                producers_created += 1

                # 2. Producer CLP
                if clean_c:
                    ProducerCLP.objects.update_or_create(
                        producer=producer,
                        code=clean_c,
                        defaults={
                            'lugar_produccion': campo,
                            'distrito': campo.split('-')[-1].strip() if '-' in campo else '',
                            'is_active': True,
                        }
                    )
                    clps_created += 1
            else:
                producers_created += 1
                if clean_c:
                    clps_created += 1

            # 3. Transportista, Vehículo y Chofer (si la fila tiene datos de transporte)
            company_name = transp.strip().upper()
            if not company_name and (truck_plate or driver_name):
                company_name = f"TRANSPORTE PARTICULAR - {driver_name or truck_plate}"

            if company_name and (truck_plate or driver_name):
                if not dry_run:
                    if company_name not in transporters_cache:
                        # Generar RUC de referencia determinístico si no se tiene en el CSV
                        safe_ruc_id = f"RUC-T{len(transporters_cache) + 1:04d}"
                        tc, created_tc = TransportCompany.objects.get_or_create(
                            tenant=tenant,
                            razon_social=company_name,
                            defaults={
                                'ruc': safe_ruc_id,
                                'is_active': True,
                            }
                        )
                        transporters_cache[company_name] = tc
                        if created_tc:
                            transport_created += 1
                    else:
                        tc = transporters_cache[company_name]

                    # Vehículo
                    if truck_plate:
                        v, created_v = Vehicle.objects.get_or_create(
                            company=tc,
                            plate=truck_plate,
                            defaults={
                                'brand_model': truck_brand,
                                'is_active': True,
                            }
                        )
                        if created_v:
                            vehicles_created += 1

                    # Chofer
                    if driver_name and driver_lic:
                        d, created_d = Driver.objects.get_or_create(
                            company=tc,
                            license_number=driver_lic,
                            defaults={
                                'name': driver_name,
                                'is_active': True,
                            }
                        )
                        if created_d:
                            drivers_created += 1
                else:
                    if company_name not in transporters_cache:
                        transporters_cache[company_name] = True
                        transport_created += 1
                    if truck_plate:
                        vehicles_created += 1
                    if driver_name and driver_lic:
                        drivers_created += 1

            status_icon = "[OK]" if not dry_run else "[PREVIEW]"
            t_detail = f" | Transp: {company_name[:20]} ({truck_plate})" if truck_plate else ""
            print(f"  {status_icon} Fila {idx:2d} -> Cod: {prod_code:<6} | Productor: {prod_name:<38} | CLP: {clean_c:<15}{t_detail}")

        if dry_run:
            transaction.set_rollback(True)

    print("\n==================================================================")
    print("   RESUMEN DE IMPORTACIÓN")
    print(f"   - Productores procesados: {producers_created}")
    print(f"   - Códigos CLP creados:    {clps_created}")
    print(f"   - Empresas de Transporte: {transport_created}")
    print(f"   - Vehículos / Camiones:   {vehicles_created}")
    print(f"   - Choferes registrados:   {drivers_created}")
    print("==================================================================")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Importar catálogo de productores y transporte desde LISTADO.csv.")
    parser.add_argument(
        '--file',
        type=str,
        default=r"C:\Users\Panda\Downloads\LISTADO.csv",
        help="Ruta absoluta al archivo CSV."
    )
    parser.add_argument(
        '--tenant',
        type=str,
        default="ica",
        help="Código de la sede a la que se asignarán los maestros (por defecto: ica)."
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Simula la importación y muestra el parseo en consola sin escribir en la base de datos."
    )
    args = parser.parse_args()

    import_csv(file_path=args.file, tenant_code=args.tenant, dry_run=args.dry_run)
