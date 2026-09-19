import os
import django
import json
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils import timezone
from tenants.models import Tenant
from inventory.models import Product, ProductVariety
from producers.models import Producer, ProducerCLP
from transporte.models import TransportCompany, Driver, Vehicle
from reports.models import Report
from users.models import User

casma = Tenant.objects.get(code='casma')
admin_casma = User.objects.filter(email='admin.casma@agro.com').first() or User.objects.filter(role='superadmin').first()

# 1. Products & Varieties
mango, _ = Product.objects.get_or_create(
    tenant=casma,
    code='CAS-MANGO-01',
    defaults={'name': 'Mango', 'product_type': 'raw', 'unit': 'kg', 'description': 'Mango fresco de exportación para Sede Casma'}
)
for v_name in ['KENT', 'HADEN', 'TOMMY ATKINS', 'EDWARD']:
    ProductVariety.objects.get_or_create(product=mango, name=v_name)

palta_cas, _ = Product.objects.get_or_create(
    tenant=casma,
    code='CAS-PALTA-01',
    defaults={'name': 'Palta', 'product_type': 'raw', 'unit': 'kg', 'description': 'Palta fresca para Sede Casma'}
)
for v_name in ['HASS', 'FUERTE']:
    ProductVariety.objects.get_or_create(product=palta_cas, name=v_name)

# 2. Producers & CLPs
producers_data = [
    {
        'name': 'Agrícola Casma Valle Verde S.A.C.',
        'code': 'PROD-CAS-01',
        'ruc': '20601234567',
        'address': 'Valle de Casma Km 375, Áncash',
        'phone': '+51 943 112 233',
        'clps': [
            {'code': 'CLP-CAS-001', 'lugar': 'Sector Huambacho'},
            {'code': 'CLP-CAS-002', 'lugar': 'Sector Tabón'},
        ]
    },
    {
        'name': 'Fundo San Rafael de Casma S.A.C.',
        'code': 'PROD-CAS-02',
        'ruc': '20543219876',
        'address': 'Fundo San Rafael Sector B, Casma',
        'phone': '+51 943 445 566',
        'clps': [
            {'code': 'CLP-CAS-003', 'lugar': 'Sector Sechín Alto'},
        ]
    },
    {
        'name': 'Agroexportadora del Valle Casma E.I.R.L.',
        'code': 'PROD-CAS-03',
        'ruc': '20498765432',
        'address': 'Carretera Casma - Huaraz Km 12',
        'phone': '+51 943 778 899',
        'clps': [
            {'code': 'CLP-CAS-004', 'lugar': 'Sector Mojeque'},
        ]
    },
]

for p_info in producers_data:
    p_obj, _ = Producer.objects.update_or_create(
        tenant=casma,
        code=p_info['code'],
        defaults={
            'name': p_info['name'],
            'address': p_info['address'],
            'phone': p_info['phone'],
            'created_by': admin_casma,
        }
    )
    for c in p_info['clps']:
        ProducerCLP.objects.get_or_create(
            producer=p_obj,
            code=c['code'],
            defaults={'lugar_produccion': c['lugar']}
        )

# 3. Transport Companies, Drivers, Vehicles
tc1, _ = TransportCompany.objects.update_or_create(
    tenant=casma,
    ruc='20601234567',
    defaults={
        'razon_social': 'Transportes del Norte Casma S.A.C.',
        'address': 'Av. Panamericana Norte 450, Casma',
        'phone': '+51 943 889 900',
    }
)
d1, _ = Driver.objects.get_or_create(company=tc1, license_number='Q12345678', defaults={'name': 'Carlos Mendoza'})
d2, _ = Driver.objects.get_or_create(company=tc1, license_number='H34567890', defaults={'name': 'Luis Alva'})
v1, _ = Vehicle.objects.get_or_create(company=tc1, plate='ABC-789', defaults={'brand_model': 'Volvo FMX 440'})
v2, _ = Vehicle.objects.get_or_create(company=tc1, plate='C1A-234', defaults={'brand_model': 'Mercedes-Benz Actros'})

tc2, _ = TransportCompany.objects.update_or_create(
    tenant=casma,
    ruc='20512398741',
    defaults={
        'razon_social': 'Logística y Carga Áncash S.A.C.',
        'address': 'Zona Industrial Casma Lote 4',
        'phone': '+51 943 223 344',
    }
)
d3, _ = Driver.objects.get_or_create(company=tc2, license_number='Q87654321', defaults={'name': 'Raúl Sánchez'})
v3, _ = Vehicle.objects.get_or_create(company=tc2, plate='M1N-567', defaults={'brand_model': 'Scania G410'})

# 4. Correct Existing 6 Reports for Casma (change Uva/Granada to Mango/Palta)
casma_existing_reports = Report.objects.filter(tenant=casma)
casma_products_pool = [
    ('MANGO', 'KENT', 'PROD-CAS-01', 'Agrícola Casma Valle Verde S.A.C.', 'CLP-CAS-001', 'Sector Huambacho'),
    ('MANGO', 'TOMMY ATKINS', 'PROD-CAS-02', 'Fundo San Rafael de Casma S.A.C.', 'CLP-CAS-003', 'Sector Sechín Alto'),
    ('PALTA', 'HASS', 'PROD-CAS-01', 'Agrícola Casma Valle Verde S.A.C.', 'CLP-CAS-002', 'Sector Tabón'),
    ('PALTA', 'FUERTE', 'PROD-CAS-03', 'Agroexportadora del Valle Casma E.I.R.L.', 'CLP-CAS-004', 'Sector Mojeque'),
    ('MANGO', 'HADEN', 'PROD-CAS-01', 'Agrícola Casma Valle Verde S.A.C.', 'CLP-CAS-001', 'Sector Huambacho'),
    ('MANGO', 'KENT', 'PROD-CAS-02', 'Fundo San Rafael de Casma S.A.C.', 'CLP-CAS-003', 'Sector Sechín Alto'),
]

for idx, rep in enumerate(casma_existing_reports[:6]):
    p_name, v_name, pr_code, pr_name, clp_code, sector = casma_products_pool[idx % len(casma_products_pool)]
    rep.producto = p_name
    lote_code = f'{p_name[0]}-CAS-{idx+1:03d}'
    rep.lote = lote_code
    
    # Update JSON
    dg = rep.datosGenerales_json
    if isinstance(dg, str):
        try:
            dg = json.loads(dg)
        except Exception:
            dg = {}
    elif not isinstance(dg, dict):
        dg = {}

    dg['producto'] = p_name
    dg['variedad'] = v_name
    dg['productor'] = pr_name
    dg['productorCode'] = pr_code
    dg['clp'] = clp_code
    dg['lugarProduccion'] = sector
    dg['distrito'] = 'CASMA - ANCASH'
    dg['empresaTransporte'] = 'Transportes del Norte Casma S.A.C. - 20601234567'
    dg['conductor'] = 'Carlos Mendoza'
    dg['licencia'] = 'Q12345678'
    dg['placaVehiculo'] = 'ABC-789'
    rep.datosGenerales_json = json.dumps(dg)
    rep.save()

# 5. Add 5 New Recent Reports for Sede Casma
today = timezone.now()
recent_batches = [
    {
        'producto': 'MANGO',
        'variedad': 'KENT',
        'carga': 'CRG-CAS-001',
        'lote': 'M-CAS-101',
        'productor': 'Agrícola Casma Valle Verde S.A.C.',
        'productorCode': 'PROD-CAS-01',
        'clp': 'CLP-CAS-001',
        'lugarProduccion': 'Sector Huambacho',
        'transportista': 'Transportes del Norte Casma S.A.C. - 20601234567',
        'conductor': 'Carlos Mendoza',
        'licencia': 'Q12345678',
        'placa': 'ABC-789',
        'jabas': 480,
        'pesoBruto': 11840.0,
        'tara': 960.0,
        'pesoNeto': 10880.0,
        'date_offset_hours': 3,
    },
    {
        'producto': 'PALTA',
        'variedad': 'HASS',
        'carga': 'CRG-CAS-002',
        'lote': 'P-CAS-102',
        'productor': 'Fundo San Rafael de Casma S.A.C.',
        'productorCode': 'PROD-CAS-02',
        'clp': 'CLP-CAS-003',
        'lugarProduccion': 'Sector Sechín Alto',
        'transportista': 'Logística y Carga Áncash S.A.C. - 20512398741',
        'conductor': 'Raúl Sánchez',
        'licencia': 'Q87654321',
        'placa': 'M1N-567',
        'jabas': 400,
        'pesoBruto': 9800.0,
        'tara': 800.0,
        'pesoNeto': 9000.0,
        'date_offset_hours': 8,
    },
    {
        'producto': 'MANGO',
        'variedad': 'TOMMY ATKINS',
        'carga': 'CRG-CAS-003',
        'lote': 'M-CAS-103',
        'productor': 'Agroexportadora del Valle Casma E.I.R.L.',
        'productorCode': 'PROD-CAS-03',
        'clp': 'CLP-CAS-004',
        'lugarProduccion': 'Sector Mojeque',
        'transportista': 'Transportes del Norte Casma S.A.C. - 20601234567',
        'conductor': 'Luis Alva',
        'licencia': 'H34567890',
        'placa': 'C1A-234',
        'jabas': 520,
        'pesoBruto': 12900.0,
        'tara': 1040.0,
        'pesoNeto': 11860.0,
        'date_offset_hours': 24,
    },
    {
        'producto': 'PALTA',
        'variedad': 'FUERTE',
        'carga': 'CRG-CAS-004',
        'lote': 'P-CAS-104',
        'productor': 'Agrícola Casma Valle Verde S.A.C.',
        'productorCode': 'PROD-CAS-01',
        'clp': 'CLP-CAS-002',
        'lugarProduccion': 'Sector Tabón',
        'transportista': 'Transportes del Norte Casma S.A.C. - 20601234567',
        'conductor': 'Carlos Mendoza',
        'licencia': 'Q12345678',
        'placa': 'ABC-789',
        'jabas': 350,
        'pesoBruto': 8550.0,
        'tara': 700.0,
        'pesoNeto': 7850.0,
        'date_offset_hours': 36,
    },
    {
        'producto': 'MANGO',
        'variedad': 'HADEN',
        'carga': 'CRG-CAS-005',
        'lote': 'M-CAS-105',
        'productor': 'Fundo San Rafael de Casma S.A.C.',
        'productorCode': 'PROD-CAS-02',
        'clp': 'CLP-CAS-003',
        'lugarProduccion': 'Sector Sechín Alto',
        'transportista': 'Logística y Carga Áncash S.A.C. - 20512398741',
        'conductor': 'Raúl Sánchez',
        'licencia': 'Q87654321',
        'placa': 'M1N-567',
        'jabas': 460,
        'pesoBruto': 11200.0,
        'tara': 920.0,
        'pesoNeto': 10280.0,
        'date_offset_hours': 48,
    },
]

created_count = 0
for b in recent_batches:
    r_id = f"casma_{b['carga'].lower()}_{int(today.timestamp())}"
    created_dt = today - timedelta(hours=b['date_offset_hours'])
    
    j1 = b['jabas'] // 2
    j2 = b['jabas'] - j1
    pb1 = b['pesoBruto'] / 2
    pb2 = b['pesoBruto'] - pb1
    t1 = b['tara'] / 2
    t2 = b['tara'] - t1
    pn1 = pb1 - t1
    pn2 = pb2 - t2
    
    registros = [
        {
            'id': f"reg-1-{b['carga']}",
            'jabas': j1,
            'pesoJaba': 2.0,
            'pesoBruto': pb1,
            'pesoParihuela': 0,
            'tara': t1,
            'pesoNeto': pn1,
            'hora': '10:30',
        },
        {
            'id': f"reg-2-{b['carga']}",
            'jabas': j2,
            'pesoJaba': 2.0,
            'pesoBruto': pb2,
            'pesoParihuela': 0,
            'tara': t2,
            'pesoNeto': pn2,
            'hora': '10:45',
        }
    ]
    
    totales = {
        'totalJabas': b['jabas'],
        'totalPesoBruto': b['pesoBruto'],
        'totalTara': b['tara'],
        'totalPesoNeto': b['pesoNeto'],
        'totalParihuela': 0,
        'promedioPorJaba': round(b['pesoNeto'] / b['jabas'], 2),
    }
    
    dg = {
        'fecha': created_dt.strftime('%Y-%m-%d'),
        'hora': created_dt.strftime('%H:%M'),
        'producto': b['producto'],
        'variedad': b['variedad'],
        'lote': b['lote'],
        'carga': b['carga'],
        'tipoReporte': 'normal',
        'productor': b['productor'],
        'productorCode': b['productorCode'],
        'clp': b['clp'],
        'lugarProduccion': b['lugarProduccion'],
        'distrito': 'CASMA - ANCASH',
        'guiaPrincipal': f"GR-CAS-{b['carga'][-3:]}",
        'guiaRemision': f"TGR-00{b['carga'][-3:]}",
        'empresaTransporte': b['transportista'],
        'conductor': b['conductor'],
        'licencia': b['licencia'],
        'placaVehiculo': b['placa'],
        'responsable': 'Carlos Mendoza (Operario Balanza)',
        'observaciones': f"Recepción conforme de {b['producto']} {b['variedad']} en Planta Casma.",
    }
    
    Report.objects.update_or_create(
        id=r_id,
        defaults={
            'tenant': casma,
            'created_by': admin_casma,
            'producto': b['producto'],
            'lote': b['lote'],
            'incrementLote': False,
            'status': 'completed',
            'totalJabas': b['jabas'],
            'totalPesoBruto': b['pesoBruto'],
            'totalPesoNeto': b['pesoNeto'],
            'datosGenerales_json': json.dumps(dg),
            'registros_json': json.dumps(registros),
            'totales_json': json.dumps(totales),
            'created_at': created_dt,
            'timestamp': int(created_dt.timestamp() * 1000),
        }
    )
    created_count += 1

print(f"Successfully seeded Casma: 3 producers, 2 transport companies, 6 updated legacy reports, and {created_count} new recent reports!")
print("Total Casma reports now:", Report.objects.filter(tenant=casma).count())
print("Casma products in reports:", set(Report.objects.filter(tenant=casma).values_list('producto', flat=True)))
