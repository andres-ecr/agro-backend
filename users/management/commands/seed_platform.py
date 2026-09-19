from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tenants.models import Tenant

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed tenants and test users for ERP platform'

    def handle(self, *args, **options):
        self.stdout.write("Seeding tenants and test users...")

        # 1. Tenants
        tenants_data = [
            {
                'name': 'Sede Ica',
                'code': 'ica',
                'ruc': '20512345671',
                'address': 'Carretera Panamericana Sur Km 300, Ica',
                'allowed_roles': ['admin', 'operator'],
                'is_active': True,
            },
            {
                'name': 'Sede Casma',
                'code': 'casma',
                'ruc': '20512345672',
                'address': 'Valle de Casma Km 375, Ancash',
                'allowed_roles': ['admin', 'operator'],
                'is_active': True,
            },
        ]

        tenants_map = {}
        for t_info in tenants_data:
            tenant, created = Tenant.objects.update_or_create(
                code=t_info['code'],
                defaults={
                    'name': t_info['name'],
                    'ruc': t_info['ruc'],
                    'address': t_info['address'],
                    'allowed_roles': t_info['allowed_roles'],
                    'is_active': t_info['is_active'],
                }
            )
            tenants_map[t_info['code']] = tenant
            action = "Created" if created else "Updated"
            self.stdout.write(f"  [{action}] Tenant {tenant.name} ({tenant.code}) - allowed_roles: {tenant.allowed_roles}")

        # 2. Users
        users_data = [
            {
                'email': 'superadmin@agro.com',
                'first_name': 'Platform',
                'last_name': 'Owner',
                'role': 'superadmin',
                'is_superuser': True,
                'is_staff': True,
                'tenant': None,
            },
            {
                'email': 'sadpvndv@gmail.com',
                'first_name': 'Super',
                'last_name': 'Admin',
                'role': 'superadmin',
                'is_superuser': True,
                'is_staff': True,
                'tenant': None,
            },
            {
                'email': 'admin.ica@agro.com',
                'first_name': 'Admin',
                'last_name': 'Ica',
                'role': 'admin',
                'is_superuser': False,
                'is_staff': False,
                'tenant': tenants_map['ica'],
            },
            {
                'email': 'operario.ica@agro.com',
                'first_name': 'Operario',
                'last_name': 'Ica',
                'role': 'operator',
                'is_superuser': False,
                'is_staff': False,
                'tenant': tenants_map['ica'],
            },
            {
                'email': 'admin.casma@agro.com',
                'first_name': 'Admin',
                'last_name': 'Casma',
                'role': 'admin',
                'is_superuser': False,
                'is_staff': False,
                'tenant': tenants_map['casma'],
            },
            {
                'email': 'operario.casma@agro.com',
                'first_name': 'Operario',
                'last_name': 'Casma',
                'role': 'operator',
                'is_superuser': False,
                'is_staff': False,
                'tenant': tenants_map['casma'],
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
                    'tenant': u_info['tenant'],
                    'is_active': True,
                }
            )

            user.first_name = u_info['first_name']
            user.last_name = u_info['last_name']
            user.role = u_info['role']
            user.is_superuser = u_info['is_superuser']
            user.is_staff = u_info['is_staff']
            user.tenant = u_info['tenant']
            user.is_active = True
            user.set_password(password)
            user.save()

            action = "Created" if created else "Updated"
            tenant_name = user.tenant.name if user.tenant else "None (Platform Superadmin)"
            self.stdout.write(f"  [{action}] User {user.email} (role: {user.role}, tenant: {tenant_name})")

        self.stdout.write(self.style.SUCCESS("Successfully seeded all tenants and users!"))
