import os
import sys
import django

# Setup Django environment if run as standalone script
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


def seed_production():
    """
    Clean Production Initializer for Sobifruits:
    - Creates Organization & Sedes (Ica and Casma).
    - Sets up standard fruit catalogs and varieties for scale weighing.
    - Sets up clean production users (Admin, Operario, Superadmin).
    - Guarantees 0 reports, 0 test transport companies, and 0 dummy producers
      so production starts clean without history or abandoned test data.
    """
    print("==========================================================")
    print("🌱 INICIANDO CONFIGURACIÓN DE PRODUCCIÓN (CLEAN SLATE)")
    print("==========================================================")

    # 1. PURGE TEST OPERATIONAL DATA (Zero Usage State)
    # -------------------------------------------------------------
    deleted_reports, _ = Report.objects.all().delete()
    deleted_vehicles, _ = Vehicle.objects.all().delete()
    deleted_drivers, _ = Driver.objects.all().delete()
    deleted_transporters, _ = TransportCompany.objects.all().delete()
    deleted_clps, _ = ProducerCLP.objects.all().delete()
    deleted_producers, _ = Producer.objects.all().delete()

    print(f"[OK] Reportes limpiados: {deleted_reports} (CERO reportes en producción)")
    print(f"[OK] Transportistas limpiados: {deleted_transporters} empresas, {deleted_drivers} choferes, {deleted_vehicles} vehículos")
    print(f"[OK] Productores limpiados: {deleted_producers} productores, {deleted_clps} CLPs")

    # 2. ORGANIZATION & TENANTS (Sedes)
    # -------------------------------------------------------------
    org, _ = Organization.objects.update_or_create(
        code='sobifruits',
        defaults={
            'name': 'Sobifruits S.A.C.',
            'ruc': '20601234567',
            'address': 'Panamericana Sur Km 300, Ica, Perú',
            'is_active': True,
        }
    )
    print(f"[OK] Organización: {org.name} ({org.code})")

    ica, _ = Tenant.objects.update_or_create(
        code='ica',
        defaults={
            'name': 'Sede Ica',
            'organization': org,
            'ruc': '20601234567',
            'address': 'Panamericana Sur Km 300, Subtanjalla, Ica',
            'allowed_roles': ['admin', 'operator', 'supervisor'],
            'show_units': False,
            'is_active': True,
        }
    )
    ica.show_units = False
    ica.save()
    print(f"[OK] Sede: {ica.name} ({ica.code}) [show_units={ica.show_units}] -> Org: {org.name}")

    casma, _ = Tenant.objects.update_or_create(
        code='casma',
        defaults={
            'name': 'Sede Casma',
            'organization': org,
            'ruc': '20601234568',
            'address': 'Valle de Casma Km 375, Casma, Áncash',
            'allowed_roles': ['admin', 'operator', 'supervisor'],
            'show_units': False,
            'is_active': True,
        }
    )
    casma.show_units = False
    casma.save()
    print(f"[OK] Sede: {casma.name} ({casma.code}) [show_units={casma.show_units}] -> Org: {org.name}")

    # 3. PRODUCTS & VARIETIES (Ready for scale operator)
    # -------------------------------------------------------------
    # Sede Ica
    ica_products = [
        {
            'code': 'UVA',
            'name': 'Uva',
            'unit': 'kg',
            'varieties': ['RED GLOBE', 'SUGRAONE', 'THOMSON', 'ALLISON', 'SWEET GLOBE'],
        },
        {
            'code': 'PALTA',
            'name': 'Palta',
            'unit': 'kg',
            'varieties': ['HASS'],
        },
        {
            'code': 'GRANADA',
            'name': 'Granada',
            'unit': 'kg',
            'varieties': ['WONDERFUL'],
        },
    ]

    for p_info in ica_products:
        prod, _ = Product.objects.update_or_create(
            tenant=ica,
            code=p_info['code'],
            defaults={
                'name': p_info['name'],
                'unit': p_info['unit'],
                'product_type': 'finished',
                'description': f"{p_info['name']} para exportación e industrial",
            }
        )
        prod.varieties.exclude(name__in=p_info['varieties']).delete()
        for v in p_info['varieties']:
            ProductVariety.objects.get_or_create(
                product=prod,
                name=v,
                defaults={'code': v.replace(' ', '_')}
            )
        print(f"[OK] Producto Ica: {prod.name} -> Variedades: {[v.name for v in prod.varieties.all()]}")

    # Sede Casma
    casma_products = [
        {
            'code': 'MANGO',
            'name': 'Mango',
            'unit': 'kg',
            'varieties': ['KENT', 'HADEN', 'TOMMY ATKINS', 'EDWARD'],
        },
        {
            'code': 'PALTA-CAS',
            'name': 'Palta',
            'unit': 'kg',
            'varieties': ['HASS', 'FUERTE'],
        },
    ]

    for p_info in casma_products:
        prod, _ = Product.objects.update_or_create(
            tenant=casma,
            code=p_info['code'],
            defaults={
                'name': p_info['name'],
                'unit': p_info['unit'],
                'product_type': 'finished',
                'description': f"{p_info['name']} Casma para exportación",
            }
        )
        prod.varieties.exclude(name__in=p_info['varieties']).delete()
        for v in p_info['varieties']:
            ProductVariety.objects.get_or_create(
                product=prod,
                name=v,
                defaults={'code': v.replace(' ', '_')}
            )
        print(f"[OK] Producto Casma: {prod.name} -> Variedades: {[v.name for v in prod.varieties.all()]}")

    # 4. PRODUCTION USERS
    # -------------------------------------------------------------
    default_password = os.environ.get('DEFAULT_USER_PASSWORD', 'agro123')

    users_data = [
        {
            'email': 'admin.ica@sobifruits.com',
            'first_name': 'Administrador',
            'last_name': 'Ica',
            'role': User.ROLE_ADMIN,
            'tenant': ica,
            'organization': org,
            'is_staff': False,
            'is_superuser': False,
        },
        {
            'email': 'operario.ica@sobifruits.com',
            'first_name': 'Operador',
            'last_name': 'Balanza Ica',
            'role': User.ROLE_OPERATOR,
            'tenant': ica,
            'organization': org,
            'is_staff': False,
            'is_superuser': False,
        },
        {
            'email': 'admin.casma@sobifruits.com',
            'first_name': 'Administrador',
            'last_name': 'Casma',
            'role': User.ROLE_ADMIN,
            'tenant': casma,
            'organization': org,
            'is_staff': False,
            'is_superuser': False,
        },
        {
            'email': 'operario.casma@sobifruits.com',
            'first_name': 'Operador',
            'last_name': 'Balanza Casma',
            'role': User.ROLE_OPERATOR,
            'tenant': casma,
            'organization': org,
            'is_staff': False,
            'is_superuser': False,
        },
        {
            'email': 'superadmin@alchlab.com',
            'first_name': 'Soporte',
            'last_name': 'AlchLab',
            'role': User.ROLE_SUPERADMIN,
            'tenant': None,
            'organization': None,
            'is_staff': True,
            'is_superuser': True,
        },
    ]

    for u_info in users_data:
        user, created = User.objects.get_or_create(
            email=u_info['email'],
            defaults={
                'first_name': u_info['first_name'],
                'last_name': u_info['last_name'],
                'role': u_info['role'],
                'tenant': u_info['tenant'],
                'organization': u_info['organization'],
                'is_staff': u_info['is_staff'],
                'is_superuser': u_info['is_superuser'],
                'is_active': True,
            }
        )
        if not created:
            user.first_name = u_info['first_name']
            user.last_name = u_info['last_name']
            user.role = u_info['role']
            user.tenant = u_info['tenant']
            user.organization = u_info['organization']
            user.is_staff = u_info['is_staff']
            user.is_superuser = u_info['is_superuser']
            user.is_active = True
        user.set_password(default_password)
        user.save()
        print(f"[OK] Usuario: {user.email} (Rol: {user.role}, Sede: {user.tenant.code if user.tenant else 'Global'})")

    print("==========================================================")
    print("✅ CONFIGURACIÓN DE PRODUCCIÓN COMPLETADA EXITOSAMENTE")
    print("   - Cero reportes históricos (tablas limpias)")
    print("   - Cero transportistas falsos (para registrar en planta)")
    print("   - Catálogo de frutas y variedades listo para balanza")
    print("   - Usuarios listos con contraseña estándar")
    print("==========================================================")


seed_production()
