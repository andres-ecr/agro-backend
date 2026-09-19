from django.core.management.base import BaseCommand
from tenants.models import Tenant
from users.models import User
from producers.models import Producer, ProducerCLP


class Command(BaseCommand):
    help = 'Seed default tenants (Sede Ica and Sede Casma) and assign existing users to Sede Ica'

    def handle(self, *args, **options):
        ica, created_ica = Tenant.objects.get_or_create(
            code='ica',
            defaults={
                'name': 'Sede Ica',
                'is_active': True,
                'address': 'Ica, Perú',
            }
        )
        if created_ica:
            self.stdout.write(self.style.SUCCESS(f'Created tenant: {ica.name} ({ica.code})'))
        else:
            self.stdout.write(f'Tenant {ica.name} already exists.')

        casma, created_casma = Tenant.objects.get_or_create(
            code='casma',
            defaults={
                'name': 'Sede Casma',
                'is_active': True,
                'address': 'Casma, Perú',
            }
        )
        if created_casma:
            self.stdout.write(self.style.SUCCESS(f'Created tenant: {casma.name} ({casma.code})'))
        else:
            self.stdout.write(f'Tenant {casma.name} already exists.')

        # Assign existing users without tenant to Sede Ica
        users_to_assign = User.objects.filter(tenant__isnull=True)
        count = users_to_assign.count()
        if count > 0:
            users_to_assign.update(tenant=ica)
            self.stdout.write(self.style.SUCCESS(f'Assigned {count} users to tenant {ica.name}.'))
        else:
            self.stdout.write('All users already have an assigned tenant.')

        # Sync legacy producer clp to ProducerCLP
        for producer in Producer.objects.all():
            if producer.clp and not producer.clp_list.exists():
                clp_obj, created = ProducerCLP.objects.get_or_create(
                    producer=producer,
                    code=producer.clp,
                    defaults={'is_active': True}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created ProducerCLP {clp_obj.code} for {producer.name}'))

        self.stdout.write(self.style.SUCCESS('Seeding completed successfully.'))
