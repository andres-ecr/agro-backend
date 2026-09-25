# reports/serializers.py
from rest_framework import serializers
from .models import Report, Responsable
import json
from decimal import Decimal


class ResponsableSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Responsable
        fields = ('id', 'first_name', 'last_name', 'full_name', 'is_active', 'created_at')
        read_only_fields = ('id', 'full_name', 'created_at')

class ReportSerializer(serializers.ModelSerializer):
    registros = serializers.JSONField(required=False)
    datosGenerales = serializers.JSONField(required=False)
    totales = serializers.JSONField(required=False)
    
    tenant_name = serializers.ReadOnlyField(source='tenant.name')
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')
    
    class Meta:
        model = Report
        fields = (
            'id', 'registros', 'datosGenerales', 'totales', 
            'timestamp', 'incrementLote', 'status', 'created_at',
            'producto', 'lote', 'totalPesoBruto', 'totalPesoNeto', 'totalJabas',
            'tenant', 'tenant_name', 'created_by', 'created_by_name'
        )
        read_only_fields = ['created_at', 'producto', 'lote', 'totalPesoBruto', 'totalPesoNeto', 'totalJabas', 'tenant', 'tenant_name', 'created_by', 'created_by_name']
    
    def create(self, validated_data):
        try:
            # Extraer los datos JSON
            registros = validated_data.pop('registros', [])
            datosGenerales = validated_data.pop('datosGenerales', {})
            totales = validated_data.pop('totales', {})
            
            # Extraer campos de datosGenerales para almacenar en campos directos
            producto = datosGenerales.get('producto', '')
            lote = datosGenerales.get('carga') or datosGenerales.get('lote', '')
            
            # Extraer campos de totales para almacenar en campos directos
            totalPesoBruto = totales.get('totalPesoBruto', '0.0')
            totalPesoNeto = totales.get('totalPesoNeto', '0.0')
            totalJabas = totales.get('totalJabas', 0)
            
            # Convertir a tipos adecuados
            try:
                totalPesoBruto = Decimal(totalPesoBruto)
            except:
                totalPesoBruto = Decimal('0.0')
                
            try:
                totalPesoNeto = Decimal(totalPesoNeto)
            except:
                totalPesoNeto = Decimal('0.0')
                
            try:
                totalJabas = int(totalJabas)
            except:
                totalJabas = 0
            
            created_by = validated_data.get('created_by')
            tenant = validated_data.get('tenant')

            # Crear el reporte
            report = Report(
                id=validated_data.get('id'),
                created_by=created_by,
                tenant=tenant,
                producto=producto,
                lote=lote,
                timestamp=validated_data.get('timestamp'),
                incrementLote=validated_data.get('incrementLote', False),
                status=validated_data.get('status', 'completed'),
                registros_json=json.dumps(registros),
                datosGenerales_json=json.dumps(datosGenerales),
                totales_json=json.dumps(totales),
                totalPesoBruto=totalPesoBruto,
                totalPesoNeto=totalPesoNeto,
                totalJabas=totalJabas
            )
            report.save()
            return report
        except Exception as e:
            # Registrar el error para depuración
            print(f"Error al crear reporte: {str(e)}")
            raise
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convertir JSON a objetos Python
        try:
            if instance.registros_json:
                representation['registros'] = json.loads(instance.registros_json)
            else:
                representation['registros'] = []
            
            if instance.datosGenerales_json:
                representation['datosGenerales'] = json.loads(instance.datosGenerales_json)
            else:
                representation['datosGenerales'] = {}
            
            if instance.totales_json:
                representation['totales'] = json.loads(instance.totales_json)
            else:
                representation['totales'] = {}
        except Exception as e:
            # Registrar el error para depuración
            print(f"Error al convertir JSON: {str(e)}")
            
        return representation

class ReportListSerializer(serializers.ModelSerializer):
    tenant_name = serializers.ReadOnlyField(source='tenant.name')
    productor = serializers.SerializerMethodField()
    placa = serializers.SerializerMethodField()
    carga = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id', 'producto', 'lote', 'created_at', 
            'totalPesoNeto', 'status', 'tenant', 'tenant_name',
            'productor', 'placa', 'carga'
        )

    def get_productor(self, obj):
        if obj.datosGenerales_json:
            try:
                data = json.loads(obj.datosGenerales_json)
                return data.get('productor', '')
            except Exception:
                return ''
        return ''

    def get_placa(self, obj):
        if obj.datosGenerales_json:
            try:
                data = json.loads(obj.datosGenerales_json)
                return data.get('placaVehiculo') or data.get('placa') or data.get('datosTransporte') or ''
            except Exception:
                return ''
        return ''

    def get_carga(self, obj):
        if obj.datosGenerales_json:
            try:
                data = json.loads(obj.datosGenerales_json)
                return data.get('carga', '')
            except Exception:
                return ''
        return ''