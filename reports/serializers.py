# reports/serializers.py
from rest_framework import serializers
from .models import Report, Responsable
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date, time, datetime, timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException


class ReportEditConflict(APIException):
    status_code = 409
    default_detail = 'El reporte fue modificado por otro administrador o falta su revisión. Cancele y vuelva a abrir la edición para cargar los cambios actuales.'
    default_code = 'report_edit_conflict'


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
    revision = serializers.SerializerMethodField()
    expectedRevision = serializers.CharField(write_only=True, required=False)
    
    tenant_name = serializers.ReadOnlyField(source='tenant.name')
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')
    campaign_name = serializers.ReadOnlyField(source='campaign.name')

    def get_revision(self, instance):
        return instance.updated_at.isoformat()

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            fields['id'].read_only = True
        return fields

    def validate(self, attrs):
        if self.instance is None:
            return attrs
        immutable = {'id', 'tenant', 'created_by', 'created_at', 'updated_at', 'campaign', 'timestamp', 'incrementLote'}
        forbidden = immutable.intersection(self.initial_data)
        if forbidden:
            raise serializers.ValidationError({key: 'Este campo no se puede modificar.' for key in forbidden})
        if attrs.get('expectedRevision') != self.get_revision(self.instance):
            raise ReportEditConflict()
        existing = json.loads(self.instance.datosGenerales_json or '{}')
        supplied = attrs.get('datosGenerales', {})
        if not isinstance(supplied, dict):
            raise serializers.ValidationError({'datosGenerales': 'Debe ser un objeto.'})
        general = {**existing, **supplied}
        for key, value in supplied.items():
            if isinstance(value, (dict, list)) and value != existing.get(key):
                raise serializers.ValidationError({'datosGenerales': f'{key}: solo se permiten valores simples.'})
            if isinstance(value, float) and not Decimal(str(value)).is_finite():
                raise serializers.ValidationError({'datosGenerales': f'{key}: valor inválido.'})
        for key, limit in [('producto', 100), ('carga', 50)]:
            value = general.get(key) or (general.get('lote') if key == 'carga' else self.instance.producto)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise serializers.ValidationError({'datosGenerales': f'{key} es obligatorio (máximo {limit} caracteres).'})
            general[key] = value.strip()
        for key, value in general.items():
            if key.startswith('fecha') and value and key != 'fechaHora':
                try:
                    calendar = datetime.strptime(str(value), '%d/%m/%Y').date() if '/' in str(value) else date.fromisoformat(str(value))
                    general[key] = calendar.isoformat()
                except ValueError:
                    raise serializers.ValidationError({'datosGenerales': f'{key}: fecha inválida.'})
        if general.get('hora'):
            try:
                time.fromisoformat(str(general['hora']))
            except ValueError:
                raise serializers.ValidationError({'datosGenerales': 'hora: valor inválido.'})
        if general.get('fecha') and general.get('hora'):
            general['fechaHora'] = f"{general['fecha']}T{general['hora']}"
        if 'productorCode' in general:
            if not isinstance(general['productorCode'], str):
                raise serializers.ValidationError({'datosGenerales': 'El código del productor debe ser texto.'})
        records = attrs.get('registros', json.loads(self.instance.registros_json or '[]'))
        if not isinstance(records, list):
            raise serializers.ValidationError({'registros': 'Debe ser una lista.'})
        totals = {key: Decimal('0') for key in ('totalPesoBruto', 'totalPesoParihuela', 'totalTara', 'totalJabas', 'totalPesoNeto')}
        normalized = []
        ids = set()
        for index, record in enumerate(records):
            identifier = record.get('id') if isinstance(record, dict) else None
            valid_id = (isinstance(identifier, str) and bool(identifier.strip())) or (type(identifier) is int and identifier > 0)
            if not valid_id or str(identifier) in ids:
                raise serializers.ValidationError({'registros': f'Fila {index + 1}: identificador ausente o duplicado.'})
            ids.add(str(identifier))
            row = dict(record)
            amounts = {}
            for key in ('pesoBruto', 'pesoParihuela', 'tara', 'jabas', 'pesoJaba'):
                raw = record.get(key, 0 if key in ('pesoParihuela', 'pesoJaba') else None)
                try:
                    if isinstance(raw, bool):
                        raise ValueError()
                    value = Decimal(str(raw))
                    if not value.is_finite() or value < 0 or value > Decimal('99999999.99'):
                        raise ValueError()
                    if key == 'jabas' and (value != value.to_integral_value() or value > 2147483647):
                        raise ValueError()
                except (InvalidOperation, ValueError, TypeError):
                    raise serializers.ValidationError({'registros': f'Fila {index + 1}: {key} inválido.'})
                amounts[key] = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                row[key] = int(value) if key == 'jabas' else str(amounts[key])
            net = amounts['pesoBruto'] - amounts['pesoParihuela'] - amounts['tara']
            if net < 0:
                raise serializers.ValidationError({'registros': f'Fila {index + 1}: los descuentos superan el peso bruto.'})
            row['pesoNeto'] = str(net)
            for total, key in [('totalPesoBruto', 'pesoBruto'), ('totalPesoParihuela', 'pesoParihuela'), ('totalTara', 'tara'), ('totalJabas', 'jabas')]:
                totals[total] += amounts[key]
            totals['totalPesoNeto'] += net
            normalized.append(row)
        if any(value > Decimal('99999999.99') for key, value in totals.items() if key != 'totalJabas') or totals['totalJabas'] > 2147483647:
            raise serializers.ValidationError({'registros': 'Los totales superan el límite permitido.'})
        totals['promedioPorJaba'] = (totals['totalPesoNeto'] / totals['totalJabas']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if totals['totalJabas'] else Decimal('0')
        campaign = self.instance.campaign
        if not campaign or campaign.tenant_id != self.instance.tenant_id or campaign.product.name.casefold() != general['producto'].casefold():
            from inventory.models import Campaign
            campaign = Campaign.objects.filter(tenant=self.instance.tenant, product__name__iexact=general['producto'], status='active').first()
            if not campaign:
                raise serializers.ValidationError({'datosGenerales': 'El producto necesita una campaña activa en esta sede.'})
        attrs['datosGenerales'] = general
        attrs['registros'] = normalized
        attrs['totales'] = {key: int(value) if key == 'totalJabas' else str(value) for key, value in totals.items()}
        self.edit_campaign = campaign
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        general = validated_data['datosGenerales']
        totals = validated_data['totales']
        # One database compare-and-update protects even concurrently preloaded serializers.
        changed = Report.objects.filter(pk=instance.pk, updated_at=instance.updated_at).update(
            datosGenerales_json=json.dumps(general), registros_json=json.dumps(validated_data['registros']),
            totales_json=json.dumps(totals), producto=general['producto'], lote=general['carga'],
            totalPesoBruto=Decimal(totals['totalPesoBruto']), totalPesoNeto=Decimal(totals['totalPesoNeto']),
            totalJabas=totals['totalJabas'], campaign=self.edit_campaign,
            status=validated_data.get('status', instance.status), updated_at=max(timezone.now(), instance.updated_at + timedelta(microseconds=1)),
        )
        if changed != 1:
            raise ReportEditConflict()
        instance.refresh_from_db()
        return instance
    
    class Meta:
        model = Report
        fields = (
            'id', 'registros', 'datosGenerales', 'totales', 'revision', 'expectedRevision',
            'timestamp', 'incrementLote', 'status', 'created_at',
            'producto', 'lote', 'totalPesoBruto', 'totalPesoNeto', 'totalJabas',
            'tenant', 'tenant_name', 'campaign', 'campaign_name',
            'created_by', 'created_by_name'
        )
        read_only_fields = [
            'created_at', 'producto', 'lote', 'totalPesoBruto', 'totalPesoNeto',
            'totalJabas', 'tenant', 'tenant_name', 'campaign', 'campaign_name',
            'created_by', 'created_by_name'
        ]
    
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
            campaign = validated_data.get('campaign')

            # Crear el reporte
            report = Report(
                id=validated_data.get('id'),
                created_by=created_by,
                tenant=tenant,
                campaign=campaign,
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
    campaign_name = serializers.ReadOnlyField(source='campaign.name')
    productor = serializers.SerializerMethodField()
    placa = serializers.SerializerMethodField()
    carga = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id', 'producto', 'lote', 'created_at', 
            'totalPesoNeto', 'status', 'tenant', 'tenant_name',
            'campaign', 'campaign_name',
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
