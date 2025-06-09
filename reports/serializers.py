# reports/serializers.py
from rest_framework import serializers
from .models import Report
import json
from decimal import Decimal

class ReportSerializer(serializers.ModelSerializer):
    registros = serializers.JSONField(required=False)
    datosGenerales = serializers.JSONField(required=False)
    totales = serializers.JSONField(required=False)
    
    class Meta:
        model = Report
        fields = (
            'id', 'registros', 'datosGenerales', 'totales', 
            'timestamp', 'incrementLote', 'status', 'created_at',
            'producto', 'lote', 'totalPesoBruto', 'totalPesoNeto', 'totalJabas'
        )
        read_only_fields = ['created_at', 'producto', 'lote', 'totalPesoBruto', 'totalPesoNeto', 'totalJabas']
    
    def create(self, validated_data):
        try:
            # Extraer los datos JSON
            registros = validated_data.pop('registros', [])
            datosGenerales = validated_data.pop('datosGenerales', {})
            totales = validated_data.pop('totales', {})
            
            # Extraer campos de datosGenerales para almacenar en campos directos
            producto = datosGenerales.get('producto', '')
            lote = datosGenerales.get('lote', '')
            
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
            
            # Crear el reporte
            report = Report(
                id=validated_data.get('id'),
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
    class Meta:
        model = Report
        fields = (
            'id', 'producto', 'lote', 'created_at', 
            'totalPesoNeto', 'status'
        )