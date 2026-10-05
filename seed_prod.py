"""
Script de inicialización y reinicio de producción (Clean Slate).

Restaura la base de datos de producción al estado base operativo limpio:
1. Elimina datos operacionales de prueba (reportes de pesaje, movimientos de inventario,
   campañas de prueba, responsables temporales y registros huérfanos).
2. Configura la Organización principal (Sobifruits S.A.C.) y Sedes (Ica y Casma).
3. Configura el catálogo oficial de productos y variedades por sede.
4. Inicializa las campañas activas 2026 oficiales listas para que los operarios pesen fruta.
5. Configura los usuarios oficiales del sistema (Superadmin, Administradores y Operarios)
   con las credenciales de CREDENTIALS.md y el panel Dev Quick Login.
6. Permite opcionalmente cargar maestros base (productores y transportistas) con --with-masters.

Uso:
    python seed_prod.py [--with-masters] [--password MI_CLAVE]
    python manage.py reset_prod_base [--with-masters] [--password MI_CLAVE]
"""

import os
import sys
import argparse
from datetime import date

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
from django.contrib.auth import get_user_model
from django.utils import timezone
from tenants.models import Organization, Tenant
from inventory.models import Product, ProductVariety, Campaign, InventoryMovement, InventoryItem, Warehouse
from producers.models import Producer, ProducerCLP
from transporte.models import TransportCompany, Driver, Vehicle
from reports.models import Report, ReportAttachment, Responsable

User = get_user_model()


def reset_production_to_base(default_password=None):
    if not default_password:
        default_password = os.environ.get('DEFAULT_USER_PASSWORD', 'agro123')

    print("==================================================================")
    print("   REINICIANDO BASE DE DATOS A MODO BASE DE PRODUCCION")
    print("==================================================================")

    with transaction.atomic():
        # -------------------------------------------------------------
        # 1. PURGA DE DATOS OPERACIONALES DE PRUEBA
        # -------------------------------------------------------------
        print("\n[1/5] Purgando datos operacionales y maestros de prueba...")

        del_attachments, _ = ReportAttachment.objects.all().delete()
        del_reports, _ = Report.objects.all().delete()
        del_movements, _ = InventoryMovement.objects.all().delete()
        del_items, _ = InventoryItem.objects.all().delete()
        del_campaigns, _ = Campaign.objects.all().delete()
        del_responsables, _ = Responsable.objects.all().delete()

        del_vehicles, _ = Vehicle.objects.all().delete()
        del_drivers, _ = Driver.objects.all().delete()
        del_transporters, _ = TransportCompany.objects.all().delete()
        del_clps, _ = ProducerCLP.objects.all().delete()
        del_producers, _ = Producer.objects.all().delete()

        print(f"  - Reportes de pesaje eliminados: {del_reports} (adjuntos: {del_attachments})")
        print(f"  - Movimientos e ítems de inventario eliminados: {del_movements} movs, {del_items} items")
        print(f"  - Campañas previas eliminadas: {del_campaigns}")
        print(f"  - Responsables de PC compartida limpiados: {del_responsables}")
        print(f"  - Productores de prueba eliminados: {del_producers} (CLPs: {del_clps})")
        print(f"  - Transportistas de prueba eliminados: {del_transporters} empresas, {del_drivers} choferes, {del_vehicles} vehiculos")
        print("  --> Catálogo de Productores y Transportistas limpio en CERO: listo para registro real en balanza/planta.")

        # -------------------------------------------------------------
        # 2. ORGANIZACION Y SEDES (TENANTS)
        # -------------------------------------------------------------
        print("\n[2/5] Configurando Organización y Sedes operativas...")

        org, _ = Organization.objects.update_or_create(
            code='sobifruits',
            defaults={
                'name': 'Sobifruits S.A.C.',
                'ruc': '20601234567',
                'address': 'Panamericana Sur Km 300, Subtanjalla, Ica, Perú',
                'is_active': True,
            }
        )
        print(f"  [OK] Organización: {org.name} (RUC: {org.ruc})")

        ica, _ = Tenant.objects.update_or_create(
            code='ica',
            defaults={
                'name': 'Sede Ica',
                'organization': org,
                'ruc': '20601234567',
                'address': 'Carretera Panamericana Sur Km 300, Subtanjalla, Ica',
                'allowed_roles': ['admin', 'operator'],
                'show_units': False,
                'is_active': True,
            }
        )
        if ica.organization_id != org.id:
            ica.organization = org
            ica.save()
        print(f"  [OK] Sede: {ica.name} ({ica.code}) -> Org: {org.name}")

        casma, _ = Tenant.objects.update_or_create(
            code='casma',
            defaults={
                'name': 'Sede Casma',
                'organization': org,
                'ruc': '20601234568',
                'address': 'Valle de Casma Km 375, Casma, Áncash',
                'allowed_roles': ['admin', 'operator'],
                'show_units': False,
                'is_active': True,
            }
        )
        if casma.organization_id != org.id:
            casma.organization = org
            casma.save()
        print(f"  [OK] Sede: {casma.name} ({casma.code}) -> Org: {org.name}")

        # -------------------------------------------------------------
        # 3. CATALOGO OFICIAL DE PRODUCTOS Y VARIEDADES
        # -------------------------------------------------------------
        print("\n[3/5] Configurando productos y variedades oficiales...")

        # Sede Ica
        ica_products = [
            {
                'code': 'UVA',
                'name': 'Uva',
                'unit': 'kg',
                'description': 'Uva de mesa para exportación e industrial',
                'varieties': ['RED GLOBE', 'SUGRAONE', 'THOMSON', 'ALLISON', 'SWEET GLOBE'],
                'campaign_name': 'Campaña Uva 2026',
                'campaign_code': 'CAMP-ICA-UVA-2026',
            },
            {
                'code': 'PALTA',
                'name': 'Palta',
                'unit': 'kg',
                'description': 'Palta Hass para exportación',
                'varieties': ['HASS'],
                'campaign_name': 'Campaña Palta 2026',
                'campaign_code': 'CAMP-ICA-PALTA-2026',
            },
            {
                'code': 'GRANADA',
                'name': 'Granada',
                'unit': 'kg',
                'description': 'Granada Wonderful de exportación',
                'varieties': ['WONDERFUL'],
                'campaign_name': 'Campaña Granada 2026',
                'campaign_code': 'CAMP-ICA-GRANADA-2026',
            },
        ]

        # Eliminar productos huérfanos o fuera de las sedes oficiales
        Product.objects.exclude(tenant__in=[ica, casma]).delete()

        # Eliminar productos no oficiales de Ica
        Product.objects.filter(tenant=ica).exclude(code__in=[p['code'] for p in ica_products]).delete()

        created_ica_products = {}
        for p_info in ica_products:
            prod, _ = Product.objects.update_or_create(
                tenant=ica,
                code=p_info['code'],
                defaults={
                    'name': p_info['name'],
                    'unit': p_info['unit'],
                    'product_type': 'finished',
                    'description': p_info['description'],
                }
            )
            # Sincronizar variedades
            prod.varieties.exclude(name__in=p_info['varieties']).delete()
            for v_name in p_info['varieties']:
                ProductVariety.objects.get_or_create(
                    product=prod,
                    name=v_name,
                    defaults={'code': v_name.replace(' ', '_'), 'is_active': True}
                )
            created_ica_products[p_info['code']] = (prod, p_info)
            print(f"  [OK] Sede Ica -> {prod.name}: {[v.name for v in prod.varieties.all()]}")

        # Sede Casma
        casma_products = [
            {
                'code': 'MANGO',
                'name': 'Mango',
                'unit': 'kg',
                'description': 'Mango para exportación del valle de Casma',
                'varieties': ['KENT', 'HADEN', 'TOMMY ATKINS', 'EDWARD'],
                'campaign_name': 'Campaña Mango 2026',
                'campaign_code': 'CAMP-CAS-MANGO-2026',
            },
            {
                'code': 'PALTA-CAS',
                'name': 'Palta',
                'unit': 'kg',
                'description': 'Palta Hass y Fuerte para exportación Casma',
                'varieties': ['HASS', 'FUERTE'],
                'campaign_name': 'Campaña Palta Casma 2026',
                'campaign_code': 'CAMP-CAS-PALTA-2026',
            },
        ]

        # Eliminar productos no oficiales de Casma
        Product.objects.filter(tenant=casma).exclude(code__in=[p['code'] for p in casma_products]).delete()

        created_casma_products = {}
        for p_info in casma_products:
            prod, _ = Product.objects.update_or_create(
                tenant=casma,
                code=p_info['code'],
                defaults={
                    'name': p_info['name'],
                    'unit': p_info['unit'],
                    'product_type': 'finished',
                    'description': p_info['description'],
                }
            )
            # Sincronizar variedades
            prod.varieties.exclude(name__in=p_info['varieties']).delete()
            for v_name in p_info['varieties']:
                ProductVariety.objects.get_or_create(
                    product=prod,
                    name=v_name,
                    defaults={'code': v_name.replace(' ', '_'), 'is_active': True}
                )
            created_casma_products[p_info['code']] = (prod, p_info)
            print(f"  [OK] Sede Casma -> {prod.name}: {[v.name for v in prod.varieties.all()]}")

        # -------------------------------------------------------------
        # 4. USUARIOS OFICIALES DE PRODUCCION
        # -------------------------------------------------------------
        print("\n[4/5] Configurando usuarios oficiales del sistema...")

        users_payload = [
            # Superadministradores Globales
            {
                'email': 'superadmin@agro.com',
                'first_name': 'Administrador',
                'last_name': 'General SaaS',
                'role': User.ROLE_SUPERADMIN,
                'tenant': None,
                'organization': None,
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'email': 'sadpvndv@gmail.com',
                'first_name': 'Soporte',
                'last_name': 'Técnico Plataforma',
                'role': User.ROLE_SUPERADMIN,
                'tenant': None,
                'organization': None,
                'is_staff': True,
                'is_superuser': True,
            },
            # Sede Ica
            {
                'email': 'admin.ica@agro.com',
                'first_name': 'Administrador',
                'last_name': 'Sede Ica',
                'role': User.ROLE_ADMIN,
                'tenant': ica,
                'organization': org,
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'email': 'operario.ica@agro.com',
                'first_name': 'Operario',
                'last_name': 'Balanza Ica',
                'role': User.ROLE_OPERATOR,
                'tenant': ica,
                'organization': org,
                'is_staff': False,
                'is_superuser': False,
            },
            # Sede Casma
            {
                'email': 'admin.casma@agro.com',
                'first_name': 'Administrador',
                'last_name': 'Sede Casma',
                'role': User.ROLE_ADMIN,
                'tenant': casma,
                'organization': org,
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'email': 'operario.casma@agro.com',
                'first_name': 'Operario',
                'last_name': 'Balanza Casma',
                'role': User.ROLE_OPERATOR,
                'tenant': casma,
                'organization': org,
                'is_staff': False,
                'is_superuser': False,
            },
            # Alias @sobifruits.com para compatibilidad
            {
                'email': 'admin.ica@sobifruits.com',
                'first_name': 'Administrador',
                'last_name': 'Sede Ica',
                'role': User.ROLE_ADMIN,
                'tenant': ica,
                'organization': org,
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'email': 'operario.ica@sobifruits.com',
                'first_name': 'Operario',
                'last_name': 'Balanza Ica',
                'role': User.ROLE_OPERATOR,
                'tenant': ica,
                'organization': org,
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        created_users = {}
        for u_data in users_payload:
            user, created = User.objects.get_or_create(
                email=u_data['email'],
                defaults={
                    'first_name': u_data['first_name'],
                    'last_name': u_data['last_name'],
                    'role': u_data['role'],
                    'tenant': u_data['tenant'],
                    'organization': u_data['organization'],
                    'is_staff': u_data['is_staff'],
                    'is_superuser': u_data['is_superuser'],
                    'is_active': True,
                }
            )
            if not created:
                user.first_name = u_data['first_name']
                user.last_name = u_data['last_name']
                user.role = u_data['role']
                user.tenant = u_data['tenant']
                user.organization = u_data['organization']
                user.is_staff = u_data['is_staff']
                user.is_superuser = u_data['is_superuser']
                user.is_active = True

            user.set_password(default_password)
            user.save()
            created_users[u_data['email']] = user
            tenant_label = user.tenant.name if user.tenant else 'Global'
            print(f"  [OK] Usuario: {user.email:<28} | Rol: {user.role:<10} | Sede: {tenant_label}")

        # -------------------------------------------------------------
        # 5. CAMPAÑAS ACTIVAS OFICIALES 2026
        # -------------------------------------------------------------
        print("\n[5/5] Aperturando campañas oficiales 2026 (listas para pesaje)...")

        today = timezone.now().date()
        admin_ica_user = created_users.get('admin.ica@agro.com')
        admin_casma_user = created_users.get('admin.casma@agro.com')

        # Campañas Ica
        for code, (prod, p_info) in created_ica_products.items():
            camp, _ = Campaign.objects.update_or_create(
                tenant=ica,
                product=prod,
                status='active',
                defaults={
                    'name': p_info['campaign_name'],
                    'code': p_info['campaign_code'],
                    'start_date': today,
                    'created_by': admin_ica_user,
                    'observations': f"Campaña oficial activa 2026 para {prod.name} en Sede Ica.",
                }
            )
            print(f"  [OK] Campaña Activa: {camp.name} ({camp.code}) -> Producto: {prod.name}")

        # Campañas Casma
        for code, (prod, p_info) in created_casma_products.items():
            camp, _ = Campaign.objects.update_or_create(
                tenant=casma,
                product=prod,
                status='active',
                defaults={
                    'name': p_info['campaign_name'],
                    'code': p_info['campaign_code'],
                    'start_date': today,
                    'created_by': admin_casma_user,
                    'observations': f"Campaña oficial activa 2026 para {prod.name} en Sede Casma.",
                }
            )
            print(f"  [OK] Campaña Activa: {camp.name} ({camp.code}) -> Producto: {prod.name}")

    print("\n==================================================================")
    print("   PRODUCCIÓN REINICIADA EXITOSAMENTE (MODO BASE)")
    print("   - Reportes históricos: 0 (listo para pesaje real desde cero)")
    print("   - Productores y Transportistas: 0 (limpios para registro real en balanza)")
    print("   - Catálogo de Frutas y Variedades configurado")
    print("   - Campañas activas 2026 aperturadas para cada producto")
    print("   - Usuarios oficiales listos con contraseña configurada")
    print("==================================================================")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Reiniciar base de datos a modo producción base limpio.")
    parser.add_argument(
        '--password',
        type=str,
        default=None,
        help='Contraseña por defecto para los usuarios (por defecto: agro123 o env DEFAULT_USER_PASSWORD).'
    )
    args = parser.parse_args()

    reset_production_to_base(default_password=args.password)
