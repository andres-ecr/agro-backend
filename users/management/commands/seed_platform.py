from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tenants.models import Organization, Tenant
from inventory.models import Product, ProductVariety
from producers.models import Producer, ProducerCLP
from transporte.models import TransportCompany, Driver, Vehicle

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed 3-level multi-tenant platform (Organizations, Sedes, Users, and Master Data)'

    def handle(self, *args, **options):
        self.stdout.write("Seeding 3-level multi-tenant SaaS architecture...")

        # 1. Organizations
        org_sobifruits, _ = Organization.objects.update_or_create(
            code='sobifruits',
            defaults={
                'name': 'Sobifruits S.A.C.',
                'ruc': '20601234567',
                'address': 'Av. Los Frutales 123, Ica, Perú',
                'is_active': True,
            }
        )
        self.stdout.write(f"  [Org] {org_sobifruits.name} ({org_sobifruits.code})")

        org_frutas_norte, _ = Organization.objects.update_or_create(
            code='frutas-norte',
            defaults={
                'name': 'Frutas del Norte S.A.C.',
                'ruc': '20709876543',
                'address': 'Carretera Panamericana Norte Km 980, Piura, Perú',
                'is_active': True,
            }
        )
        self.stdout.write(f"  [Org] {org_frutas_norte.name} ({org_frutas_norte.code})")

        # 2. Sedes / Tenants
        sedes_data = [
            {
                'organization': org_sobifruits,
                'name': 'Sede Ica',
                'code': 'ica',
                'ruc': '20601234567',
                'address': 'Carretera Panamericana Sur Km 300, Ica',
                'allowed_roles': ['admin', 'operator'],
                'is_active': True,
            },
            {
                'organization': org_sobifruits,
                'name': 'Sede Casma',
                'code': 'casma',
                'ruc': '20601234567',
                'address': 'Valle de Casma Km 375, Ancash',
                'allowed_roles': ['admin', 'operator'],
                'is_active': True,
            },
            {
                'organization': org_frutas_norte,
                'name': 'Sede Piura',
                'code': 'piura',
                'ruc': '20709876543',
                'address': 'Carretera Panamericana Norte Km 980, Piura',
                'allowed_roles': ['admin', 'operator'],
                'is_active': True,
            },
        ]

        sedes_map = {}
        for s in sedes_data:
            sede, created = Tenant.objects.update_or_create(
                code=s['code'],
                defaults={
                    'organization': s['organization'],
                    'name': s['name'],
                    'ruc': s['ruc'],
                    'address': s['address'],
                    'allowed_roles': s['allowed_roles'],
                    'is_active': s['is_active'],
                }
            )
            sedes_map[s['code']] = sede
            action = "Created" if created else "Updated"
            self.stdout.write(f"  [{action}] Sede {sede.name} -> Org: {sede.organization.name}")

        # 3. Users
        users_data = [
            {
                'email': 'superadmin@agro.com',
                'first_name': 'Platform',
                'last_name': 'Owner',
                'role': 'superadmin',
                'is_superuser': True,
                'is_staff': True,
                'organization': None,
                'tenant': None,
            },
            {
                'email': 'sadpvndv@gmail.com',
                'first_name': 'Super',
                'last_name': 'Admin',
                'role': 'superadmin',
                'is_superuser': True,
                'is_staff': True,
                'organization': None,
                'tenant': None,
            },
            {
                'email': 'admin.ica@agro.com',
                'first_name': 'Admin',
                'last_name': 'Ica',
                'role': 'admin',
                'is_superuser': False,
                'is_staff': False,
                'organization': org_sobifruits,
                'tenant': sedes_map['ica'],
            },
            {
                'email': 'operario.ica@agro.com',
                'first_name': 'Operario',
                'last_name': 'Ica',
                'role': 'operator',
                'is_superuser': False,
                'is_staff': False,
                'organization': org_sobifruits,
                'tenant': sedes_map['ica'],
            },
            {
                'email': 'admin.casma@agro.com',
                'first_name': 'Admin',
                'last_name': 'Casma',
                'role': 'admin',
                'is_superuser': False,
                'is_staff': False,
                'organization': org_sobifruits,
                'tenant': sedes_map['casma'],
            },
            {
                'email': 'operario.casma@agro.com',
                'first_name': 'Operario',
                'last_name': 'Casma',
                'role': 'operator',
                'is_superuser': False,
                'is_staff': False,
                'organization': org_sobifruits,
                'tenant': sedes_map['casma'],
            },
            {
                'email': 'admin.piura@agro.com',
                'first_name': 'Admin',
                'last_name': 'Piura',
                'role': 'admin',
                'is_superuser': False,
                'is_staff': False,
                'organization': org_frutas_norte,
                'tenant': sedes_map['piura'],
            },
            {
                'email': 'operario.piura@agro.com',
                'first_name': 'Operario',
                'last_name': 'Piura',
                'role': 'operator',
                'is_superuser': False,
                'is_staff': False,
                'organization': org_frutas_norte,
                'tenant': sedes_map['piura'],
            },
        ]

        password = 'agro123'
        for u_info in users_data:
            user, created = User.objects.get_or_create(
                email=u_info['email'],
                defaults={
                    'first_name': u_info['first_name'],
                    'last_name': u_info['last_name'],
                    'role': u_info['role'],
                    'is_superuser': u_info['is_superuser'],
                    'is_staff': u_info['is_staff'],
                    'organization': u_info['organization'],
                    'tenant': u_info['tenant'],
                    'is_active': True,
                }
            )

            user.first_name = u_info['first_name']
            user.last_name = u_info['last_name']
            user.role = u_info['role']
            user.is_superuser = u_info['is_superuser']
            user.is_staff = u_info['is_staff']
            user.organization = u_info['organization']
            user.tenant = u_info['tenant']
            user.is_active = True
            user.set_password(password)
            user.save()

            action = "Created" if created else "Updated"
            org_name = user.organization.name if user.organization else "None (Platform)"
            sede_name = user.tenant.name if user.tenant else "None"
            self.stdout.write(f"  [{action}] User {user.email} (Org: {org_name}, Sede: {sede_name}, Role: {user.role})")

        # 4. Master Data for Sede Piura
        sede_piura = sedes_map['piura']

        # Products
        limon, _ = Product.objects.update_or_create(
            tenant=sede_piura,
            code='PIU-LIMON-01',
            defaults={
                'name': 'Limón Sutil',
                'product_type': Product.TYPE_FINISHED,
                'unit': Product.UNIT_BOX,
            }
        )
        limon_varieties = ['SUTIL', 'TAHITI']
        limon.varieties.exclude(name__in=limon_varieties).delete()
        for v in limon_varieties:
            ProductVariety.objects.get_or_create(product=limon, name=v)
        self.stdout.write(f"  [Product] {limon.name} ({limon.code}) - Varieties: {limon_varieties}")

        banano, _ = Product.objects.update_or_create(
            tenant=sede_piura,
            code='PIU-BANANO-01',
            defaults={
                'name': 'Banano Orgánico',
                'product_type': Product.TYPE_FINISHED,
                'unit': Product.UNIT_BOX,
            }
        )
        banano_varieties = ['CAVENDISH']
        banano.varieties.exclude(name__in=banano_varieties).delete()
        for v in banano_varieties:
            ProductVariety.objects.get_or_create(product=banano, name=v)
        self.stdout.write(f"  [Product] {banano.name} ({banano.code}) - Varieties: {banano_varieties}")

        # Producer
        producer_piura, _ = Producer.objects.update_or_create(
            code='PROD-PIU-01',
            defaults={
                'tenant': sede_piura,
                'name': 'Asociación Agrícola del Chira',
                'clp': 'CLP-PIU-001',
                'address': 'Valle del Chira, Sullana, Piura',
            }
        )
        ProducerCLP.objects.get_or_create(
            producer=producer_piura,
            code='CLP-PIU-001',
            defaults={'lugar_produccion': 'Valle del Chira - Parcela 1'}
        )
        self.stdout.write(f"  [Producer] {producer_piura.name} ({producer_piura.code}) - CLP: {producer_piura.clp}")

        # Transport Company, Driver, Vehicle
        transporte_piura, _ = TransportCompany.objects.update_or_create(
            ruc='20711223344',
            tenant=sede_piura,
            defaults={
                'razon_social': 'Transportes del Chira S.A.C.',
                'address': 'Av. Sánchez Cerro 500, Piura',
                'phone': '969112233',
                'is_active': True,
            }
        )
        driver, _ = Driver.objects.update_or_create(
            company=transporte_piura,
            name='Pedro Flores',
            defaults={
                'license_number': 'Q12345678',
                'is_active': True,
            }
        )
        vehicle, _ = Vehicle.objects.update_or_create(
            company=transporte_piura,
            plate='P1U-456',
            defaults={
                'brand_model': 'Volvo FH 460',
                'is_active': True,
            }
        )
        self.stdout.write(f"  [Transport] {transporte_piura.razon_social} - Driver: {driver.name}, Vehicle: {vehicle.plate}")

        self.stdout.write(self.style.SUCCESS("Successfully seeded all 3-level multi-tenant platform data!"))
