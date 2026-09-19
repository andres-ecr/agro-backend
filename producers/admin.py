from django.contrib import admin
from .models import Producer, ProducerCLP


class ProducerCLPInline(admin.TabularInline):
    model = ProducerCLP
    extra = 1


@admin.register(Producer)
class ProducerAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'clp', 'phone', 'created_at')
    search_fields = ('code', 'name', 'clp')
    inlines = [ProducerCLPInline]


@admin.register(ProducerCLP)
class ProducerCLPAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'producer', 'lugar_produccion', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('code', 'lugar_produccion', 'producer__name')
