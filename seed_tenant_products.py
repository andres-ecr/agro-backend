import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from tenants.models import Tenant
from inventory.models import Product, ProductVariety

def seed_tenant_products():
    ica = Tenant.objects.get(code='ica')
    casma = Tenant.objects.get(code='casma')
    print(f"Loaded tenants: {ica.name} ({ica.code}), {casma.name} ({casma.code})")

    # --- Sede Ica ---
    # Delete any unassigned or Ica-associated Mango or Arandano
    deleted_count, _ = Product.objects.filter(name__in=['Mango', 'Arándano', 'Arandano', 'Arndano'], tenant__in=[ica, None]).delete()
    print(f"Deleted {deleted_count} Mango/Arandano products associated with Ica/None")

    # Uva
    uva_ica = Product.objects.filter(name__iexact='Uva').first()
    if not uva_ica:
        uva_ica = Product.objects.create(name='Uva', code='UVA', tenant=ica)
    else:
        uva_ica.tenant = ica
        uva_ica.save()

    uva_varieties = ['RED GLOBE', 'SUGRAONE', 'THOMSON', 'ALLISON', 'SWEET GLOBE']
    uva_ica.varieties.exclude(name__in=uva_varieties).delete()
    for v in uva_varieties:
        ProductVariety.objects.get_or_create(product=uva_ica, name=v)
    print(f"Ica Uva varieties: {[v.name for v in uva_ica.varieties.all()]}")

    # Palta (Ica)
    palta_ica = Product.objects.filter(name__iexact='Palta', tenant__in=[ica, None]).first()
    if not palta_ica:
        palta_ica = Product.objects.create(name='Palta', code='PALTA', tenant=ica)
    else:
        palta_ica.tenant = ica
        palta_ica.save()

    palta_ica.varieties.exclude(name='HASS').delete()
    ProductVariety.objects.get_or_create(product=palta_ica, name='HASS')
    print(f"Ica Palta varieties: {[v.name for v in palta_ica.varieties.all()]}")

    # Granada (Ica)
    granada_ica = Product.objects.filter(name__iexact='Granada', tenant__in=[ica, None]).first()
    if not granada_ica:
        granada_ica = Product.objects.create(name='Granada', code='GRANADA', tenant=ica)
    else:
        granada_ica.tenant = ica
        granada_ica.save()

    granada_ica.varieties.exclude(name='WONDERFUL').delete()
    ProductVariety.objects.get_or_create(product=granada_ica, name='WONDERFUL')
    print(f"Ica Granada varieties: {[v.name for v in granada_ica.varieties.all()]}")

    # --- Sede Casma ---
    # Mango
    mango_casma, _ = Product.objects.get_or_create(
        tenant=casma,
        code='CAS-MANGO-01',
        defaults={'name': 'Mango', 'product_type': 'finished', 'unit': 'kg'}
    )
    mango_casma.name = 'Mango'
    mango_casma.save()
    mango_varieties = ['KENT', 'HADEN', 'TOMMY ATKINS', 'EDWARD']
    mango_casma.varieties.exclude(name__in=mango_varieties).delete()
    for v in mango_varieties:
        ProductVariety.objects.get_or_create(product=mango_casma, name=v)
    print(f"Casma Mango varieties: {[v.name for v in mango_casma.varieties.all()]}")

    # Palta (Casma)
    palta_casma, _ = Product.objects.get_or_create(
        tenant=casma,
        code='CAS-PALTA-01',
        defaults={'name': 'Palta', 'product_type': 'finished', 'unit': 'kg'}
    )
    palta_casma.name = 'Palta'
    palta_casma.save()
    palta_casma_varieties = ['HASS', 'FUERTE']
    palta_casma.varieties.exclude(name__in=palta_casma_varieties).delete()
    for v in palta_casma_varieties:
        ProductVariety.objects.get_or_create(product=palta_casma, name=v)
    print(f"Casma Palta varieties: {[v.name for v in palta_casma.varieties.all()]}")

    # --- Verification ---
    print("\n--- VERIFICATION ---")
    ica_products = Product.objects.filter(tenant=ica)
    print(f"Ica Products ({ica_products.count()}):")
    for p in ica_products:
        print(f"  - {p.name} ({p.code}): {[v.name for v in p.varieties.all()]}")

    casma_products = Product.objects.filter(tenant=casma)
    print(f"Casma Products ({casma_products.count()}):")
    for p in casma_products:
        print(f"  - {p.name} ({p.code}): {[v.name for v in p.varieties.all()]}")

if __name__ == '__main__':
    seed_tenant_products()
