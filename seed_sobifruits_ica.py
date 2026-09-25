import os
import sys
import json
import time
from decimal import Decimal
from datetime import datetime, timezone

import django

# Setup Django if run directly
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()

from django.contrib.auth import get_user_model
from tenants.models import Organization, Tenant
from inventory.models import Product, ProductVariety
from producers.models import Producer, ProducerCLP
from transporte.models import TransportCompany, Driver, Vehicle
from reports.models import Report

User = get_user_model()


def seed_sobifruits_ica():
    print("=== STARTING SEEDING FOR SOBIFRUITS SEDE ICA ===")

    # -------------------------------------------------------------
    # 1. Organization & Tenants
    # -------------------------------------------------------------
    org, _ = Organization.objects.get_or_create(
        code='sobifruits',
        defaults={
            'name': 'Sobifruits S.A.C.',
            'ruc': '20601234567',
            'address': 'Panamericana Sur Km 300, Ica, Perú',
            'is_active': True,
        }
    )
    print(f"[OK] Organization: {org.name} ({org.code})")

    ica, _ = Tenant.objects.get_or_create(
        code='ica',
        defaults={
            'name': 'Sede Ica',
            'organization': org,
            'ruc': '20601234567',
            'address': 'Carretera Panamericana Sur Km 305, Subtanjalla, Ica',
            'allowed_roles': ['admin', 'operator', 'supervisor'],
            'is_active': True,
        }
    )
    if ica.organization != org:
        ica.organization = org
        ica.save()
    print(f"[OK] Tenant: {ica.name} ({ica.code}) -> Org: {ica.organization.name}")

    casma, _ = Tenant.objects.get_or_create(
        code='casma',
        defaults={
            'name': 'Sede Casma',
            'organization': org,
            'ruc': '20601234568',
            'address': 'Valle de Casma Km 375, Casma, Áncash',
            'allowed_roles': ['admin', 'operator', 'supervisor'],
            'is_active': True,
        }
    )
    if casma.organization != org:
        casma.organization = org
        casma.save()
    print(f"[OK] Tenant: {casma.name} ({casma.code}) -> Org: {casma.organization.name}")

    # -------------------------------------------------------------
    # 2. Products & Varieties (Sede Ica)
    # -------------------------------------------------------------
    # Delete any products in Sede Ica that are not UVA, PALTA, or GRANADA
    deleted_products, _ = Product.objects.filter(tenant=ica).exclude(
        code__in=['UVA', 'PALTA', 'GRANADA']
    ).delete()
    if deleted_products:
        print(f"[OK] Deleted {deleted_products} obsolete products for Sede Ica")

    # Uva
    uva, _ = Product.objects.update_or_create(
        tenant=ica,
        code='UVA',
        defaults={
            'name': 'Uva',
            'unit': 'kg',
            'product_type': 'finished',
            'description': 'Uva de mesa para exportación e industrial'
        }
    )
    uva_varieties = ['RED GLOBE', 'SUGRAONE', 'THOMSON', 'ALLISON', 'SWEET GLOBE']
    uva.varieties.exclude(name__in=uva_varieties).delete()
    for v_name in uva_varieties:
        ProductVariety.objects.get_or_create(product=uva, name=v_name, defaults={'code': v_name.replace(' ', '_')})
    print(f"[OK] Product: {uva.name} ({uva.code}) -> Varieties: {[v.name for v in uva.varieties.all()]}")

    # Palta
    palta, _ = Product.objects.update_or_create(
        tenant=ica,
        code='PALTA',
        defaults={
            'name': 'Palta',
            'unit': 'kg',
            'product_type': 'finished',
            'description': 'Palta Hass de exportación'
        }
    )
    palta.varieties.exclude(name='HASS').delete()
    ProductVariety.objects.get_or_create(product=palta, name='HASS', defaults={'code': 'HASS'})
    print(f"[OK] Product: {palta.name} ({palta.code}) -> Varieties: {[v.name for v in palta.varieties.all()]}")

    # Granada
    granada, _ = Product.objects.update_or_create(
        tenant=ica,
        code='GRANADA',
        defaults={
            'name': 'Granada',
            'unit': 'kg',
            'product_type': 'finished',
            'description': 'Granada Wonderful de exportación'
        }
    )
    granada.varieties.exclude(name='WONDERFUL').delete()
    ProductVariety.objects.get_or_create(product=granada, name='WONDERFUL', defaults={'code': 'WONDERFUL'})
    print(f"[OK] Product: {granada.name} ({granada.code}) -> Varieties: {[v.name for v in granada.varieties.all()]}")

    # -------------------------------------------------------------
    # 3. Producers with CLPs
    # -------------------------------------------------------------
    producers_data = [
        {
            'code': 'PROD-ICA-01',
            'name': 'Agrícola Don Ricardo S.A.C.',
            'ruc': '20452367891',
            'address': 'Sector La Venta S/N, Santiago, Ica',
            'clps': [
                {'code': 'CLP-ICA-001', 'lugar_produccion': 'Sector La Venta', 'distrito': 'Santiago'},
                {'code': 'CLP-ICA-002', 'lugar_produccion': 'Fundo Santa Rita', 'distrito': 'Los Aquijes'},
            ]
        },
        {
            'code': 'PROD-ICA-02',
            'name': 'Fundo Santa Elena S.A.C.',
            'ruc': '20512893456',
            'address': 'Carretera Villacurí Km 285, Salas Guadalupe, Ica',
            'clps': [
                {'code': 'CLP-ICA-003', 'lugar_produccion': 'Sector Villacurí', 'distrito': 'Salas Guadalupe'},
            ]
        },
        {
            'code': 'PROD-ICA-03',
            'name': 'Agrícola La Venta S.A.C.',
            'ruc': '20398456123',
            'address': 'Valle de Santiago Parcela 42, Santiago, Ica',
            'clps': [
                {'code': 'CLP-ICA-004', 'lugar_produccion': 'Sector Santiago', 'distrito': 'Santiago'},
            ]
        },
        {
            'code': 'PROD-ICA-04',
            'name': 'Exportadora Agrícola Ica S.A.C.',
            'ruc': '20603456789',
            'address': 'Av. Los Maestros 520, La Tinguiña, Ica',
            'clps': [
                {'code': 'CLP-ICA-005', 'lugar_produccion': 'Sector Tinguiña', 'distrito': 'La Tinguiña'},
            ]
        },
    ]

    for p_info in producers_data:
        prod, _ = Producer.objects.update_or_create(
            code=p_info['code'],
            defaults={
                'name': p_info['name'],
                'clp': p_info['clps'][0]['code'],
                'address': f"RUC: {p_info['ruc']} - {p_info['address']}",
                'tenant': ica,
            }
        )
        # Add CLPs
        for clp_info in p_info['clps']:
            ProducerCLP.objects.update_or_create(
                producer=prod,
                code=clp_info['code'],
                defaults={
                    'lugar_produccion': clp_info['lugar_produccion'],
                    'distrito': clp_info.get('distrito', ''),
                    'is_active': True,
                }
            )
        print(f"[OK] Producer: {prod.name} ({prod.code}) -> CLPs: {[c.code for c in prod.clp_list.all()]}")

    # -------------------------------------------------------------
    # 4. Transport Companies, Drivers & Vehicles
    # -------------------------------------------------------------
    # Transport Company 1: Transportes Ica Express S.A.C.
    tc1, _ = TransportCompany.objects.update_or_create(
        ruc='20558192110',
        defaults={
            'razon_social': 'Transportes Ica Express S.A.C.',
            'tenant': ica,
            'address': 'Av. Cutervo 450, Ica',
            'phone': '056-234567',
            'is_active': True,
        }
    )
    # Drivers for TC1
    d1, _ = Driver.objects.update_or_create(
        company=tc1,
        license_number='H29509595',
        defaults={'name': 'Willian Valdivia', 'is_active': True}
    )
    d2, _ = Driver.objects.update_or_create(
        company=tc1,
        license_number='Q45892130',
        defaults={'name': 'Jorge Huamán', 'is_active': True}
    )
    # Vehicles for TC1
    v1, _ = Vehicle.objects.update_or_create(
        company=tc1,
        plate='VOLVO-V2U-839',
        defaults={'brand_model': 'Volvo FH 460', 'is_active': True}
    )
    v2, _ = Vehicle.objects.update_or_create(
        company=tc1,
        plate='MERCEDES-AYZ-789',
        defaults={'brand_model': 'Mercedes-Benz Actros', 'is_active': True}
    )
    print(f"[OK] Transport: {tc1.razon_social} -> Drivers: {[d.name for d in tc1.drivers.all()]}, Vehicles: {[v.plate for v in tc1.vehicles.all()]}")

    # Transport Company 2: Logística y Carga del Sur S.A.C.
    tc2, _ = TransportCompany.objects.update_or_create(
        ruc='20489234561',
        defaults={
            'razon_social': 'Logística y Carga del Sur S.A.C.',
            'tenant': ica,
            'address': 'Panamericana Sur Km 298, Subtanjalla, Ica',
            'phone': '056-218945',
            'is_active': True,
        }
    )
    # Driver for TC2
    d3, _ = Driver.objects.update_or_create(
        company=tc2,
        license_number='Q12345678',
        defaults={'name': 'Carlos Mendoza', 'is_active': True}
    )
    # Vehicle for TC2
    v3, _ = Vehicle.objects.update_or_create(
        company=tc2,
        plate='SCANIA-T4X-123',
        defaults={'brand_model': 'Scania R500', 'is_active': True}
    )
    print(f"[OK] Transport: {tc2.razon_social} -> Drivers: {[d.name for d in tc2.drivers.all()]}, Vehicles: {[v.plate for v in tc2.vehicles.all()]}")

    # -------------------------------------------------------------
    # 5. Reports (Recepción y Pesaje)
    # -------------------------------------------------------------
    # Verify existing 30 reports for Ica
    existing_ica_reports = Report.objects.filter(tenant=ica)
    print(f"Existing reports in Sede Ica: {existing_ica_reports.count()}")

    for r in existing_ica_reports:
        # Validate/fix JSON if empty or malformed
        try:
            dg = json.loads(r.datosGenerales_json) if r.datosGenerales_json else {}
        except Exception:
            dg = {}
        try:
            reg = json.loads(r.registros_json) if r.registros_json else []
        except Exception:
            reg = []
        try:
            tot = json.loads(r.totales_json) if r.totales_json else {}
        except Exception:
            tot = {}

        changed = False
        if not r.datosGenerales_json or not dg:
            dg = {
                'producto': r.producto or 'UVA',
                'variedad': 'RED GLOBE',
                'responsable': 'OPERARIO ICA',
                'lote': r.lote or 'U-01',
                'productor': 'Agrícola Don Ricardo S.A.C.',
                'clp': 'CLP-ICA-001',
            }
            r.datosGenerales_json = json.dumps(dg)
            changed = True

        if not r.totales_json or not tot:
            tot = {
                'totalPesoBruto': str(r.totalPesoBruto or Decimal('10000.0')),
                'totalPesoParihuela': '160.0',
                'totalTara': '1200.0',
                'totalJabas': r.totalJabas or 800,
                'totalPesoNeto': str(r.totalPesoNeto or Decimal('8640.0')),
                'promedioPorJaba': '10.80'
            }
            r.totales_json = json.dumps(tot)
            changed = True

        if not r.registros_json or not reg:
            reg = [
                {
                    'id': 1,
                    'pesoBruto': str(r.totalPesoBruto or Decimal('10000.0')),
                    'pesoParihuela': '160.0',
                    'tara': '1200.0',
                    'jabas': r.totalJabas or 800,
                    'pesoNeto': str(r.totalPesoNeto or Decimal('8640.0')),
                    'pesoJaba': '1.5'
                }
            ]
            r.registros_json = json.dumps(reg)
            changed = True

        if changed:
            r.save()

    print("[OK] All existing Ica reports validated and ensured complete JSON.")

    # Seed 5 realistic new reports
    user_ica = User.objects.filter(email='operario.ica@agro.com').first() or User.objects.filter(role='superadmin').first()

    new_reports_specs = [
        {
            'id': 'report_20260919_crg001',
            'carga': 'CRG-2026-001',
            'guia': 'TICR-0002101',
            'producto': 'Uva',
            'producto_code': 'UVA',
            'variedad': 'RED GLOBE',
            'lote': 'U-2026-01',
            'productor': 'Agrícola Don Ricardo S.A.C.',
            'clp': 'CLP-ICA-001',
            'distrito': 'Sector La Venta - Santiago, Ica',
            'empresaTransporte': 'Transportes Ica Express S.A.C.-20558192110',
            'conductor': 'Willian Valdivia',
            'licencia': 'H29509595',
            'placa': 'VOLVO-V2U-839',
            'num_pallets': 10,
            'jabas_per_pallet': 50,
            'peso_jaba': Decimal('1.5'),
            'parihuela_wt': Decimal('12.0'),
            'avg_neto_jaba': Decimal('13.2'),
            'fecha': '19/09/2026',
        },
        {
            'id': 'report_20260919_crg002',
            'carga': 'CRG-2026-002',
            'guia': 'TICR-0002102',
            'producto': 'Uva',
            'producto_code': 'UVA',
            'variedad': 'SWEET GLOBE',
            'lote': 'U-2026-02',
            'productor': 'Agrícola Don Ricardo S.A.C.',
            'clp': 'CLP-ICA-002',
            'distrito': 'Fundo Santa Rita - Santiago, Ica',
            'empresaTransporte': 'Transportes Ica Express S.A.C.-20558192110',
            'conductor': 'Jorge Huamán',
            'licencia': 'Q45892130',
            'placa': 'MERCEDES-AYZ-789',
            'num_pallets': 12,
            'jabas_per_pallet': 50,
            'peso_jaba': Decimal('1.5'),
            'parihuela_wt': Decimal('12.0'),
            'avg_neto_jaba': Decimal('13.5'),
            'fecha': '19/09/2026',
        },
        {
            'id': 'report_20260919_crg003',
            'carga': 'CRG-2026-003',
            'guia': 'TICR-0002103',
            'producto': 'Palta',
            'producto_code': 'PALTA',
            'variedad': 'HASS',
            'lote': 'P-2026-01',
            'productor': 'Fundo Santa Elena S.A.C.',
            'clp': 'CLP-ICA-003',
            'distrito': 'Sector Villacurí - Salas Guadalupe, Ica',
            'empresaTransporte': 'Logística y Carga del Sur S.A.C.-20489234561',
            'conductor': 'Carlos Mendoza',
            'licencia': 'Q12345678',
            'placa': 'SCANIA-T4X-123',
            'num_pallets': 8,
            'jabas_per_pallet': 40,
            'peso_jaba': Decimal('1.8'),
            'parihuela_wt': Decimal('15.0'),
            'avg_neto_jaba': Decimal('18.0'),
            'fecha': '18/09/2026',
        },
        {
            'id': 'report_20260919_crg004',
            'carga': 'CRG-2026-004',
            'guia': 'TICR-0002104',
            'producto': 'Granada',
            'producto_code': 'GRANADA',
            'variedad': 'WONDERFUL',
            'lote': 'G-2026-01',
            'productor': 'Agrícola La Venta S.A.C.',
            'clp': 'CLP-ICA-004',
            'distrito': 'Sector Santiago - Santiago, Ica',
            'empresaTransporte': 'Transportes Ica Express S.A.C.-20558192110',
            'conductor': 'Willian Valdivia',
            'licencia': 'H29509595',
            'placa': 'VOLVO-V2U-839',
            'num_pallets': 10,
            'jabas_per_pallet': 45,
            'peso_jaba': Decimal('1.6'),
            'parihuela_wt': Decimal('14.0'),
            'avg_neto_jaba': Decimal('14.5'),
            'fecha': '18/09/2026',
        },
        {
            'id': 'report_20260919_crg005',
            'carga': 'CRG-2026-005',
            'guia': 'TICR-0002105',
            'producto': 'Uva',
            'producto_code': 'UVA',
            'variedad': 'RED GLOBE',
            'lote': 'U-2026-03',
            'productor': 'Exportadora Agrícola Ica S.A.C.',
            'clp': 'CLP-ICA-005',
            'distrito': 'Sector Tinguiña - La Tinguiña, Ica',
            'empresaTransporte': 'Logística y Carga del Sur S.A.C.-20489234561',
            'conductor': 'Carlos Mendoza',
            'licencia': 'Q12345678',
            'placa': 'SCANIA-T4X-123',
            'num_pallets': 10,
            'jabas_per_pallet': 50,
            'peso_jaba': Decimal('1.5'),
            'parihuela_wt': Decimal('12.0'),
            'avg_neto_jaba': Decimal('13.0'),
            'fecha': '17/09/2026',
        },
    ]

    for spec in new_reports_specs:
        registros = []
        total_peso_bruto = Decimal('0.0')
        total_peso_parihuela = Decimal('0.0')
        total_tara = Decimal('0.0')
        total_jabas = 0
        total_peso_neto = Decimal('0.0')

        for i in range(1, spec['num_pallets'] + 1):
            jabas = spec['jabas_per_pallet']
            peso_jaba = spec['peso_jaba']
            tara = jabas * peso_jaba
            parihuela = spec['parihuela_wt']
            # Realistic slight variation per pallet (+/- 1-2 kg)
            variation = Decimal(str((i % 5) - 2)) * Decimal('0.5')
            peso_neto = (jabas * spec['avg_neto_jaba']) + variation
            peso_bruto = peso_neto + parihuela + tara

            total_peso_bruto += peso_bruto
            total_peso_parihuela += parihuela
            total_tara += tara
            total_jabas += jabas
            total_peso_neto += peso_neto

            registros.append({
                'id': i,
                'pesoBruto': str(round(peso_bruto, 1)),
                'pesoParihuela': str(round(parihuela, 1)),
                'tara': str(round(tara, 1)),
                'jabas': jabas,
                'pesoNeto': str(round(peso_neto, 1)),
                'pesoJaba': str(round(peso_jaba, 2))
            })

        avg_per_jaba = round(total_peso_neto / Decimal(total_jabas), 2) if total_jabas > 0 else Decimal('0.0')

        totales = {
            'totalPesoBruto': str(round(total_peso_bruto, 1)),
            'totalPesoParihuela': str(round(total_peso_parihuela, 1)),
            'totalTara': str(round(total_tara, 1)),
            'totalJabas': total_jabas,
            'totalPesoNeto': str(round(total_peso_neto, 1)),
            'promedioPorJaba': str(avg_per_jaba)
        }

        datos_generales = {
            'producto': spec['producto_code'],
            'variedad': spec['variedad'],
            'responsable': 'WILLIAN VALDIVIA' if 'Willian' in spec['conductor'] else 'CARLOS MENDOZA',
            'lote': spec['lote'],
            'productor': spec['productor'],
            'clp': spec['clp'],
            'carga': spec['carga'],
            'guiaPrincipal': spec['guia'],
            'fechaCosecha': spec['fecha'],
            'fechaRecepcion': spec['fecha'],
            'fechaProceso': spec['fecha'],
            'datosTransporte': spec['placa'],
            'placa': spec['placa'],
            'placaVehiculo': spec['placa'],
            'empresaTransporte': spec['empresaTransporte'],
            'conductor': spec['conductor'],
            'licencia': spec['licencia'],
            'distrito': spec['distrito'],
            'observaciones': f'Carga {spec["carga"]} ingresada con control de calidad conforme.'
        }

        report, created = Report.objects.update_or_create(
            id=spec['id'],
            defaults={
                'producto': spec['producto_code'],
                'lote': spec['lote'],
                'timestamp': int(time.time() * 1000),
                'incrementLote': False,
                'status': 'completed',
                'created_by': user_ica,
                'tenant': ica,
                'registros_json': json.dumps(registros),
                'datosGenerales_json': json.dumps(datos_generales),
                'totales_json': json.dumps(totales),
                'totalPesoBruto': round(total_peso_bruto, 1),
                'totalPesoNeto': round(total_peso_neto, 1),
                'totalJabas': total_jabas,
            }
        )
        action = "Created" if created else "Updated"
        print(f"[OK] {action} Report {report.id} ({spec['carga']}): {spec['producto']} {spec['variedad']} - Net: {totales['totalPesoNeto']} kg, Jabas: {totales['totalJabas']}")

    print("\n=== SEEDING COMPLETED SUCCESSFULLY ===")


if __name__ == '__main__':
    seed_sobifruits_ica()
