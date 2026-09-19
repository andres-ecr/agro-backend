from django.core.management.base import BaseCommand
from tenants.models import Tenant
from reports.models import Report
from producers.models import Producer, ProducerCLP
from transporte.models import TransportCompany, Driver, Vehicle


class Command(BaseCommand):
    help = 'Migrate legacy reports to tenants (30 to Sede Ica, 6 to Sede Casma) and seed Casma master data'

    def handle(self, *args, **options):
        self.stdout.write("Starting legacy data migration and seeding...")

        try:
            ica = Tenant.objects.get(code='ica')
        except Tenant.DoesNotExist:
            ica = Tenant.objects.create(name='Sede Ica', code='ica', is_active=True)
            self.stdout.write(self.style.SUCCESS(f"Created tenant {ica.name}"))

        try:
            casma = Tenant.objects.get(code='casma')
        except Tenant.DoesNotExist:
            casma = Tenant.objects.create(name='Sede Casma', code='casma', is_active=True)
            self.stdout.write(self.style.SUCCESS(f"Created tenant {casma.name}"))

        # 1. Assign legacy reports (tenant__isnull=True)
        unassigned_reports = list(Report.objects.filter(tenant__isnull=True).order_by('created_at', 'id'))
        if unassigned_reports:
            ica_reports = unassigned_reports[:30]
            casma_reports = unassigned_reports[30:36]

            for r in ica_reports:
                r.tenant = ica
                r.save(update_fields=['tenant'])

            for r in casma_reports:
                r.tenant = casma
                r.save(update_fields=['tenant'])

            self.stdout.write(
                self.style.SUCCESS(
                    f"Assigned {len(ica_reports)} legacy reports to {ica.name} and {len(casma_reports)} to {casma.name}."
                )
            )
        else:
            self.stdout.write("No unassigned legacy reports found.")

        # Ensure exact count: 30 for Ica, 6 for Casma
        total_ica = Report.objects.filter(tenant=ica).count()
        total_casma = Report.objects.filter(tenant=casma).count()
        unassigned = Report.objects.filter(tenant__isnull=True).count()

        self.stdout.write(f"Report status: Sede Ica={total_ica}, Sede Casma={total_casma}, Unassigned={unassigned}")

        # 2. Seed Casma Master Data
        self.stdout.write("Seeding Casma master data...")

        # Casma Producer
        producer_casma, created_prod = Producer.objects.update_or_create(
            code='PROD-CASMA-01',
            defaults={
                'name': 'Agrícola Casma Valle Verde S.A.C.',
                'clp': 'CLP-CAS-001',
                'tenant': casma,
                'address': 'Valle de Casma, Sector Huambacho, Casma',
                'phone': '943123456',
                'email': 'contacto@agricolacasma.com',
            }
        )
        action_prod = "Created" if created_prod else "Updated"
        self.stdout.write(f"  [{action_prod}] Producer: {producer_casma.name} ({producer_casma.code})")

        # Producer CLPs
        clp1, created_clp1 = ProducerCLP.objects.update_or_create(
            producer=producer_casma,
            code='CLP-CAS-001',
            defaults={
                'lugar_produccion': 'Sector Huambacho',
                'is_active': True,
            }
        )
        action_clp1 = "Created" if created_clp1 else "Updated"
        self.stdout.write(f"  [{action_clp1}] CLP: {clp1.code} - {clp1.lugar_produccion}")

        clp2, created_clp2 = ProducerCLP.objects.update_or_create(
            producer=producer_casma,
            code='CLP-CAS-002',
            defaults={
                'lugar_produccion': 'Sector Tabón',
                'is_active': True,
            }
        )
        action_clp2 = "Created" if created_clp2 else "Updated"
        self.stdout.write(f"  [{action_clp2}] CLP: {clp2.code} - {clp2.lugar_produccion}")

        # Casma Transport Company
        company_casma, created_tc = TransportCompany.objects.update_or_create(
            ruc='20601234567',
            defaults={
                'tenant': casma,
                'razon_social': 'Transportes del Norte Casma S.A.C.',
                'address': 'Av. Panamericana Norte Km 376, Casma',
                'phone': '943987654',
                'is_active': True,
            }
        )
        action_tc = "Created" if created_tc else "Updated"
        self.stdout.write(f"  [{action_tc}] Transport Company: {company_casma.razon_social} ({company_casma.ruc})")

        # Driver
        driver, created_drv = Driver.objects.update_or_create(
            license_number='Q12345678',
            defaults={
                'company': company_casma,
                'name': 'Carlos Mendoza',
                'is_active': True,
            }
        )
        action_drv = "Created" if created_drv else "Updated"
        self.stdout.write(f"  [{action_drv}] Driver: {driver.name} ({driver.license_number})")

        # Vehicle
        vehicle, created_veh = Vehicle.objects.update_or_create(
            plate='ABC-789',
            defaults={
                'company': company_casma,
                'brand_model': 'Volvo FMX',
                'is_active': True,
            }
        )
        action_veh = "Created" if created_veh else "Updated"
        self.stdout.write(f"  [{action_veh}] Vehicle: {vehicle.plate} ({vehicle.brand_model})")

        self.stdout.write(self.style.SUCCESS("Legacy data migration and Casma seeding completed successfully!"))
