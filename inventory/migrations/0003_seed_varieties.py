from django.db import migrations

VARIETIES_MAP = {
    'UVA': ['RED GLOBE', 'SUGRAONE', 'THOMSON', 'ALLISON', 'SWEET GLOBE', 'CRIMSON', 'AUTUMN CRISP'],
    'PALTA': ['HASS', 'FUERTE', 'ZUTANO', 'MALUMA'],
    'GRANADA': ['WONDERFUL', 'ACCO', '116'],
    'ARANDANO': ['BILIXI', 'VENTURA', 'EMERALD', 'SEKOYA POP', 'ROCIO'],
    'MANGO': ['KENT', 'HADEN', 'TOMMY ATKINS', 'EDWARD'],
}

def seed_varieties(apps, schema_editor):
    Product = apps.get_model('inventory', 'Product')
    ProductVariety = apps.get_model('inventory', 'ProductVariety')

    for prod_key, varieties in VARIETIES_MAP.items():
        products = Product.objects.filter(code__iexact=prod_key)
        if not products.exists():
            products = Product.objects.filter(name__icontains=prod_key[:4])
        for product in products:
            for v_name in varieties:
                ProductVariety.objects.get_or_create(
                    product=product,
                    name=v_name,
                    defaults={'is_active': True}
                )

def reverse_seed_varieties(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_productvariety'),
    ]

    operations = [
        migrations.RunPython(seed_varieties, reverse_seed_varieties),
    ]
