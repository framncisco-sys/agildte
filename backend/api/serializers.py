from rest_framework import serializers
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.db.models import Q
from .models import (
    Cliente,
    Compra,
    Venta,
    Retencion,
    Empresa,
    Liquidacion,
    RetencionRecibida,
    Producto,
    DetalleVenta,
    ActividadEconomica,
    PlantillaFactura,
    PlantillaItem,
)


class ActividadEconomicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActividadEconomica
        fields = ('codigo', 'descripcion')


class EmpresaSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Empresa
        fields = '__all__'
        extra_kwargs = {
            'clave_api_mh': {'write_only': True},
            'clave_certificado': {'write_only': True},
            'clave_correo': {'write_only': True},
            'smtp_password': {'write_only': True},
        }

    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None

    def validate_nombre(self, value):
        if not (value and str(value).strip()):
            raise serializers.ValidationError('El nombre de la empresa es obligatorio.')
        return str(value).strip()

    def validate_nrc(self, value):
        if not (value and str(value).strip()):
            raise serializers.ValidationError('El NRC es obligatorio.')
        return str(value).strip()

    def validate_user_api_mh(self, value):
        return (value or '').strip() or None

    def validate_clave_api_mh(self, value):
        return (value or '').strip() or None

    def validate_clave_certificado(self, value):
        return (value or '').strip() or None

    def validate_smtp_password(self, value):
        return (value or '').strip() or None

class ClienteSerializer(serializers.ModelSerializer):
    # Campos opcionales: permitir null y no requerirlos
    nrc = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    nit = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    dui = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    direccion = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    # Alias para API (frontend): correo, direccion_complemento, direccion_departamento, direccion_municipio, actividad_economica
    correo = serializers.EmailField(required=False, allow_null=True, allow_blank=True, write_only=True)
    direccion_complemento = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    direccion_departamento = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    direccion_municipio = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    actividad_economica = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)

    class Meta:
        model = Cliente
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Alias para el frontend (normativa MH)
        data['correo'] = instance.email_contacto
        data['direccion_complemento'] = instance.direccion
        data['direccion_departamento'] = instance.departamento
        data['direccion_municipio'] = instance.municipio
        data['actividad_economica'] = instance.cod_actividad
        # Rellenar documento_identidad desde nit/dui si viene vacío (datos legacy)
        if not data.get('documento_identidad') and instance:
            if instance.nit:
                data['documento_identidad'] = instance.nit
                data['tipo_documento'] = data.get('tipo_documento') or 'NIT'
            elif instance.dui:
                data['documento_identidad'] = instance.dui
                data['tipo_documento'] = data.get('tipo_documento') or 'DUI'
        return data

    def validate(self, attrs):
        # Si tiene NRC, actividad económica es obligatoria (DTE-03 / CCF)
        nrc = attrs.get('nrc') or (self.instance.nrc if self.instance else None)
        cod_actividad = attrs.get('cod_actividad') or attrs.get('actividad_economica')
        if self.instance:
            cod_actividad = cod_actividad or self.instance.cod_actividad
        if nrc and str(nrc).strip():
            if not (cod_actividad and str(cod_actividad).strip()):
                raise serializers.ValidationError({
                    'actividad_economica': 'Si el cliente tiene NRC (Contribuyente), el campo Actividad Económica es obligatorio para DTE-03.'
                })
        # Correo obligatorio para enviar DTE (validación de formato si se envía)
        correo = attrs.get('correo') or attrs.get('email_contacto')
        if correo and not self._is_valid_email(correo):
            raise serializers.ValidationError({'correo': 'El correo no tiene un formato válido.'})
        # Unicidad NIT/documento_identidad: no duplicar cliente con mismo documento (por empresa)
        empresa = attrs.get('empresa')
        doc = (attrs.get('documento_identidad') or '').strip() or (attrs.get('nit') or '').strip()
        if doc:
            qs = Cliente.objects.filter(Q(nit=doc) | Q(documento_identidad=doc))
            if empresa:
                qs = qs.filter(empresa=empresa)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'documento_identidad': 'Ya existe un cliente con ese documento en esta empresa.'
                })
        # Unicidad NRC (por empresa)
        nrc_val = (attrs.get('nrc') or '').strip()
        if nrc_val:
            qs = Cliente.objects.filter(nrc=nrc_val)
            if empresa:
                qs = qs.filter(empresa=empresa)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({'nrc': 'Ya existe un cliente con ese NRC en esta empresa.'})
        return attrs

    def _is_valid_email(self, value):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(value and re.match(pattern, value))

    def create(self, validated_data):
        self._map_alias_to_model(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._map_alias_to_model(validated_data)
        return super().update(instance, validated_data)

    def _map_alias_to_model(self, validated_data):
        if 'correo' in validated_data:
            validated_data['email_contacto'] = validated_data.pop('correo') or validated_data.get('email_contacto')
        if 'direccion_complemento' in validated_data:
            validated_data['direccion'] = validated_data.pop('direccion_complemento') or validated_data.get('direccion')
        if 'direccion_departamento' in validated_data:
            validated_data['departamento'] = validated_data.pop('direccion_departamento') or validated_data.get('departamento', '06')
        if 'direccion_municipio' in validated_data:
            validated_data['municipio'] = validated_data.pop('direccion_municipio') or validated_data.get('municipio', '14')
        if 'actividad_economica' in validated_data:
            validated_data['cod_actividad'] = validated_data.pop('actividad_economica') or validated_data.get('cod_actividad')

class CompraSerializer(serializers.ModelSerializer):
    # Campos explícitos para aceptar datos del frontend que no son del modelo
    nrc_proveedor = serializers.CharField(required=False, write_only=True)
    nombre_proveedor = serializers.CharField(required=False, write_only=True)
    proveedor = serializers.CharField(required=False)
    
    class Meta:
        model = Compra
        fields = '__all__'

    def to_representation(self, instance):
        """
        Sobrescribe la representación para incluir nrc_proveedor y nombre_proveedor
        desde la relación proveedor, permitiendo que el frontend los reciba.
        """
        representation = super().to_representation(instance)
        # Agregar campos planos desde la relación proveedor
        if instance.proveedor:
            representation['nrc_proveedor'] = instance.proveedor.nrc
            representation['nombre_proveedor'] = instance.proveedor.nombre
        else:
            representation['nrc_proveedor'] = None
            representation['nombre_proveedor'] = None
        return representation

    def create(self, validated_data):
        # 1. EXTRAER y ELIMINAR datos que no son del modelo Compra
        # Usamos pop() para que desaparezcan de validated_data
        proveedor_input = validated_data.pop('proveedor', None)
        nrc_extra = validated_data.pop('nrc_proveedor', None)
        nombre_extra = validated_data.pop('nombre_proveedor', None)
        
        # 2. Lógica para definir el NRC
        nrc_final = proveedor_input or nrc_extra
        if not nrc_final:
            raise serializers.ValidationError({'proveedor': 'Falta el NRC'})
        
        # 3. Buscar o Crear el Proveedor
        proveedor_obj, created = Cliente.objects.get_or_create(
            nrc=nrc_final,
            defaults={
                'nombre': nombre_extra or f'Proveedor {nrc_final}',
            }
        )
        
        # 4. Asignar el objeto limpio a validated_data
        validated_data['proveedor'] = proveedor_obj
        
        # 5. Guardar la Compra (Ahora validated_data está limpio)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Actualiza una compra existente, limpiando campos extra y manejando cambios de proveedor.
        """
        # 1. EXTRAER y ELIMINAR datos que no son del modelo Compra
        proveedor_input = validated_data.pop('proveedor', None)
        nrc_extra = validated_data.pop('nrc_proveedor', None)
        nombre_extra = validated_data.pop('nombre_proveedor', None)
        
        # 2. Si se proporcionó un nuevo NRC, buscar/crear el proveedor
        nrc_final = proveedor_input or nrc_extra
        
        if nrc_final:
            # Si el NRC cambió o es diferente al actual, buscar/crear nuevo proveedor
            if not instance.proveedor or instance.proveedor.nrc != nrc_final:
                proveedor_obj, created = Cliente.objects.get_or_create(
                    nrc=nrc_final,
                    defaults={
                        'nombre': nombre_extra or f'Proveedor {nrc_final}',
                    }
                )
                validated_data['proveedor'] = proveedor_obj
            elif nombre_extra and instance.proveedor.nombre != nombre_extra:
                # Si solo cambió el nombre, actualizar el proveedor existente
                instance.proveedor.nombre = nombre_extra
                instance.proveedor.save()
        
        # 3. Actualizar la instancia (validated_data está limpio)
        return super().update(instance, validated_data)

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'

class DetalleVentaSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)
    producto_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    venta = serializers.PrimaryKeyRelatedField(read_only=True)  # Solo lectura para evitar validación
    
    class Meta:
        model = DetalleVenta
        fields = '__all__'
        extra_kwargs = {
            'venta': {'read_only': True}  # Asegurar que venta sea solo lectura
        }
    
    def to_internal_value(self, data):
        """Redondea automáticamente campos DecimalField a 2 decimales antes de validar"""
        # Campos monetarios que deben tener máximo 2 decimales
        campos_decimales = [
            'cantidad', 'precio_unitario', 'monto_descuento', 
            'venta_no_sujeta', 'venta_exenta', 'venta_gravada', 'iva_item'
        ]
        
        for campo in campos_decimales:
            if campo in data and data[campo] is not None:
                try:
                    valor = float(data[campo])
                    # Redondear a 2 decimales
                    valor_redondeado = round(valor, 2)
                    data[campo] = valor_redondeado
                except (ValueError, TypeError):
                    pass  # Si no se puede convertir, dejar que la validación normal lo maneje
        
        return super().to_internal_value(data)


class PlantillaItemSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)
    producto_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = PlantillaItem
        fields = '__all__'
        extra_kwargs = {
            'plantilla': {'read_only': True},
        }


class PlantillaFacturaSerializer(serializers.ModelSerializer):
    """
    Serializer para CRUD de plantillas de facturación rápida,
    incluyendo sus ítems anidados.
    """
    items = PlantillaItemSerializer(many=True, required=False)
    cliente = ClienteSerializer(read_only=True)
    cliente_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = PlantillaFactura
        fields = '__all__'

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        cliente_id = validated_data.pop('cliente_id', None)

        if cliente_id:
            try:
                cliente = Cliente.objects.get(pk=cliente_id)
            except Cliente.DoesNotExist:
                raise serializers.ValidationError({'cliente_id': 'Cliente no encontrado.'})
            validated_data['cliente'] = cliente

        plantilla = PlantillaFactura.objects.create(**validated_data)

        for idx, item_raw in enumerate(items_data):
            producto_id = item_raw.pop('producto_id', None)
            producto = None
            if producto_id:
                try:
                    producto = Producto.objects.get(pk=producto_id)
                except Producto.DoesNotExist:
                    producto = None

            # Normalizar decimales básicos
            campos_decimales = ['cantidad', 'precio_unitario']
            for campo in campos_decimales:
                if campo in item_raw and item_raw[campo] is not None:
                    try:
                        valor = Decimal(str(item_raw[campo]))
                        item_raw[campo] = valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    except (ValueError, TypeError):
                        item_raw[campo] = Decimal('0.00')

            numero_item = item_raw.pop('numero_item', idx + 1)
            PlantillaItem.objects.create(
                plantilla=plantilla,
                producto=producto,
                numero_item=numero_item,
                **item_raw,
            )

        return plantilla

    @transaction.atomic
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        cliente_id = validated_data.pop('cliente_id', None)

        if cliente_id is not None:
            if cliente_id:
                try:
                    instance.cliente = Cliente.objects.get(pk=cliente_id)
                except Cliente.DoesNotExist:
                    raise serializers.ValidationError({'cliente_id': 'Cliente no encontrado.'})
            else:
                instance.cliente = None

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Si se envían items, reemplazar completamente el detalle de la plantilla
        if items_data is not None:
            instance.items.all().delete()
            for idx, item_raw in enumerate(items_data):
                producto_id = item_raw.pop('producto_id', None)
                producto = None
                if producto_id:
                    try:
                        producto = Producto.objects.get(pk=producto_id)
                    except Producto.DoesNotExist:
                        producto = None

                campos_decimales = ['cantidad', 'precio_unitario']
                for campo in campos_decimales:
                    if campo in item_raw and item_raw[campo] is not None:
                        try:
                            valor = Decimal(str(item_raw[campo]))
                            item_raw[campo] = valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        except (ValueError, TypeError):
                            item_raw[campo] = Decimal('0.00')

                numero_item = item_raw.pop('numero_item', idx + 1)
                PlantillaItem.objects.create(
                    plantilla=instance,
                    producto=producto,
                    numero_item=numero_item,
                    **item_raw,
                )

        return instance

class VentaSerializer(serializers.ModelSerializer):
    # Campo explícito para aceptar NRC del cliente desde el frontend
    cliente = serializers.CharField(required=False)
    # Detalles solo lectura (se crean por separado)
    detalles = serializers.SerializerMethodField()
    estado_dte = serializers.CharField(read_only=False)  # Permitir escribir estado_dte
    # Campos calculados para el frontend (Historial de Documentos)
    estado = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    json_url = serializers.SerializerMethodField()
    observaciones_mh = serializers.SerializerMethodField()
    fecha_hora_emision = serializers.SerializerMethodField()
    
    class Meta:
        model = Venta
        fields = '__all__'
    
    def to_internal_value(self, data):
        """Redondea campos monetarios a 2 decimales antes de validar"""
        # Campos monetarios que deben redondearse
        campos_monetarios = [
            'venta_gravada', 'venta_exenta', 'venta_no_sujeta', 
            'debito_fiscal', 'iva_retenido_1', 'iva_retenido_2'
        ]
        
        # Redondear cada campo monetario si existe
        for campo in campos_monetarios:
            if campo in data and data[campo] is not None:
                try:
                    valor = float(data[campo])
                    # Redondear a 2 decimales
                    data[campo] = round(valor, 2)
                except (ValueError, TypeError):
                    pass  # Si no se puede convertir, dejar el valor original
        
        return super().to_internal_value(data)
    
    def get_detalles(self, obj):
        """Obtener detalles de la venta"""
        detalles = obj.detalles.all()
        return DetalleVentaSerializer(detalles, many=True).data

    def get_estado(self, obj):
        """Estado resumido: PROCESADO, RECHAZADO, ANULADO o PENDIENTE"""
        if obj.estado_dte == 'Anulado':
            return 'ANULADO'
        if obj.sello_recepcion:
            return 'PROCESADO'
        if obj.estado_dte == 'RechazadoMH':
            return 'RECHAZADO'
        return 'PENDIENTE'

    def get_pdf_url(self, obj):
        """Ruta para descargar el PDF (relativa al baseURL del frontend)"""
        return f"ventas/{obj.pk}/generar-pdf/"

    def get_json_url(self, obj):
        """Ruta para descargar el JSON DTE"""
        return f"ventas/{obj.pk}/generar-dte/"

    def get_fecha_hora_emision(self, obj):
        """Combina fecha_emision y hora_emision en ISO para el frontend (coincide con PDF/DTE)"""
        if not obj.fecha_emision:
            return None
        fecha_str = obj.fecha_emision.strftime('%Y-%m-%d')
        hora = (obj.hora_emision or '12:00:00').strip()
        if not hora or len(hora) < 5:
            hora = '12:00:00'
        # Devolver en ISO sin TZ (hora local DTE = El Salvador)
        return f"{fecha_str}T{hora}"

    def get_observaciones_mh(self, obj):
        """
        Estructura de rechazo MH: { codigo, descripcion, observaciones }.
        Para compatibilidad con datos antiguos, observaciones es siempre una lista.
        """
        raw = getattr(obj, 'observaciones_mh', None)
        if not raw:
            return {'codigo': None, 'descripcion': None, 'observaciones': []}
        import json
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                obs = parsed.get('observaciones') or []
                if not isinstance(obs, list):
                    obs = [str(obs)]
                return {
                    'codigo': parsed.get('codigo'),
                    'descripcion': parsed.get('descripcion'),
                    'observaciones': obs,
                }
            return {'codigo': None, 'descripcion': None, 'observaciones': parsed if isinstance(parsed, list) else [str(parsed)]}
        except (json.JSONDecodeError, TypeError):
            return {'codigo': None, 'descripcion': str(raw), 'observaciones': [str(raw)]}

    def to_representation(self, instance):
        """
        Sobrescribe la representación para incluir nrc_receptor, nit_receptor, nombre_receptor,
        telefono_receptor, correo_receptor y direccion_receptor desde venta o cliente.
        """
        representation = super().to_representation(instance)
        if instance.cliente:
            representation['nrc_receptor'] = instance.cliente.nrc
            representation['nit_receptor'] = getattr(instance.cliente, 'nit', None)
            representation['nombre_receptor'] = instance.cliente.nombre
            representation['cliente_id'] = instance.cliente.id
            representation['cliente'] = instance.cliente.nrc
            representation['telefono_receptor'] = representation.get('telefono_receptor') or getattr(instance.cliente, 'telefono', None)
            representation['correo_receptor'] = representation.get('correo_receptor') or getattr(instance.cliente, 'email_contacto', None)
            representation['direccion_receptor'] = representation.get('direccion_receptor') or getattr(instance.cliente, 'direccion', None)
            representation['departamento_receptor'] = getattr(instance.cliente, 'departamento', None)
            representation['municipio_receptor'] = getattr(instance.cliente, 'municipio', None)
        else:
            representation['nrc_receptor'] = None
            representation['nit_receptor'] = None
            representation['nombre_receptor'] = representation.get('nombre_receptor')
            representation['cliente'] = None
            representation['telefono_receptor'] = representation.get('telefono_receptor')
        return representation

    @transaction.atomic
    def create(self, validated_data):
        """
        Crea una venta siguiendo el orden correcto:
        1. Extraer datos anidados (si los hay)
        2. Crear la instancia de Venta (genera el ID)
        3. Crear relaciones después (si es necesario)
        """
        # 1. Extraer cualquier dato anidado ANTES de crear la venta
        # (Aunque VentaSerializer normalmente no maneja detalles, 
        #  extraemos por si acaso para evitar errores)
        detalles_data = validated_data.pop('detalles', [])
        
        # 2. Manejar cliente
        cliente_input = validated_data.pop('cliente', None)
        tipo_venta = validated_data.get('tipo_venta', 'CCF')
        
        # Normalizar cliente_input: tratar None, string vacío o "null" como ausente
        cliente_input_limpio = None
        if cliente_input and str(cliente_input).strip() and str(cliente_input).lower() != 'null':
            cliente_input_limpio = str(cliente_input).strip()
        
        # Si es Consumidor Final y no hay cliente válido, usar cliente genérico
        if tipo_venta == 'CF' and not cliente_input_limpio:
            cliente_obj, _ = Cliente.objects.get_or_create(
                nrc='0000-000000-000-0',  # NRC genérico para Consumidor Final
                defaults={
                    'nombre': 'Consumidor Final',
                    'nit': '0000-000000-000-0',
                }
            )
        elif cliente_input_limpio:
            # Si hay cliente_input (NRC), buscar o crear
            cliente_obj, _ = Cliente.objects.get_or_create(
                nrc=cliente_input_limpio,
                defaults={
                    'nombre': validated_data.get('nombre_receptor') or f'Cliente {cliente_input_limpio}',
                }
            )
        else:
            # Para CCF, requiere cliente
            raise serializers.ValidationError({
                'cliente': 'Debes proporcionar un cliente para ventas a Contribuyentes (CCF).'
            })
        
        validated_data['cliente'] = cliente_obj
        
        # 3. Redondear campos monetarios antes de crear
        campos_monetarios = ['venta_gravada', 'venta_exenta', 'venta_no_sujeta', 'debito_fiscal']
        for campo in campos_monetarios:
            if campo in validated_data and validated_data[campo] is not None:
                try:
                    valor = Decimal(str(validated_data[campo]))
                    validated_data[campo] = valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                except (ValueError, TypeError):
                    validated_data[campo] = Decimal('0.00')

        # 3b. Ambiente de emisión: desde empresa para filtrar dashboard/ventas por ambiente
        empresa = validated_data.get('empresa')
        validated_data['ambiente_emision'] = (empresa.ambiente if empresa else '01')
        
        # 4. Crear la venta PRIMERO (esto genera el ID)
        venta = Venta.objects.create(**validated_data)
        
        # 5. Si hay detalles, crearlos DESPUÉS de que la venta tenga ID
        # (Nota: Normalmente esto se maneja en VentaConDetallesSerializer,
        #  pero lo incluimos aquí por seguridad)
        if detalles_data:
            for detalle_data in detalles_data:
                # Extraer producto_id si existe
                producto_id = detalle_data.pop('producto_id', None)
                producto_obj = None
                if producto_id:
                    try:
                        producto_obj = Producto.objects.get(id=producto_id)
                    except Producto.DoesNotExist:
                        pass
                
                # Convertir y redondear campos decimales
                campos_decimales = [
                    'cantidad', 'precio_unitario', 'monto_descuento', 
                    'venta_no_sujeta', 'venta_exenta', 'venta_gravada', 'iva_item'
                ]
                for campo in campos_decimales:
                    if campo in detalle_data:
                        try:
                            valor = Decimal(str(detalle_data[campo]))
                            detalle_data[campo] = valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        except (ValueError, TypeError):
                            detalle_data[campo] = Decimal('0.00')
                
                # Crear el detalle vinculado a la venta (que ya tiene ID)
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto_obj,
                    **detalle_data
                )
            
            # Recalcular totales desde los detalles
            venta.calcular_totales()
            venta.save()
        
        return venta

    def update(self, instance, validated_data):
        """
        Actualiza una venta existente, limpiando campos extra y manejando cambios de cliente.
        """
        cliente_input = validated_data.pop('cliente', None)
        tipo_venta = validated_data.get('tipo_venta', instance.tipo_venta)
        
        # Normalizar cliente_input
        cliente_input_limpio = None
        if cliente_input and str(cliente_input).strip() and str(cliente_input).lower() != 'null':
            cliente_input_limpio = str(cliente_input).strip()
        
        # Si se proporcionó un nuevo cliente o cambió el tipo de venta
        if tipo_venta == 'CF' and not cliente_input_limpio:
            # Si es CF y no hay cliente, usar cliente genérico
            cliente_obj, _ = Cliente.objects.get_or_create(
                nrc='0000-000000-000-0',
                defaults={
                    'nombre': 'Consumidor Final',
                    'nit': '0000-000000-000-0',
                }
            )
            validated_data['cliente'] = cliente_obj
        elif cliente_input_limpio:
            # Si hay cliente_input y es diferente al actual, buscar/crear
            if not instance.cliente or instance.cliente.nrc != cliente_input_limpio:
                cliente_obj, _ = Cliente.objects.get_or_create(
                    nrc=cliente_input_limpio,
                    defaults={
                        'nombre': validated_data.get('nombre_receptor') or instance.nombre_receptor or f'Cliente {cliente_input_limpio}',
                    }
                )
                validated_data['cliente'] = cliente_obj
        elif tipo_venta == 'CCF' and not instance.cliente:
            # Para CCF, requiere cliente
            raise serializers.ValidationError({
                'cliente': 'Debes proporcionar un cliente para ventas a Contribuyentes (CCF).'
            })
        
        # Actualizar la instancia (validated_data está limpio)
        return super().update(instance, validated_data)

class RetencionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Retencion
        fields = '__all__'

class LiquidacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Liquidacion
        fields = '__all__'

class RetencionRecibidaSerializer(serializers.ModelSerializer):
    ventas_aplicadas = serializers.PrimaryKeyRelatedField(many=True, queryset=Venta.objects.all(), required=False)
    
    class Meta:
        model = RetencionRecibida
        fields = '__all__'
    
    def to_representation(self, instance):
        """Incluir detalles de ventas aplicadas en la representación"""
        representation = super().to_representation(instance)
        if instance.ventas_aplicadas.exists():
            representation['ventas_aplicadas_detalle'] = [
                {
                    'id': v.id,
                    'fecha_emision': v.fecha_emision.strftime('%Y-%m-%d'),
                    'numero_documento': v.numero_documento or '',
                    'venta_gravada': float(v.venta_gravada),
                    'debito_fiscal': float(v.debito_fiscal),
                }
                for v in instance.ventas_aplicadas.all()
            ]
        return representation

class VentaConDetallesSerializer(serializers.ModelSerializer):
    """Serializer para crear ventas con detalles en una sola operación"""
    cliente = serializers.CharField(required=False, allow_null=True)
    cliente_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    tipo_dte = serializers.CharField(required=False, allow_null=True, write_only=True)
    documento_relacionado_id = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    documento_receptor = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    tipo_doc_receptor = serializers.CharField(required=False, allow_blank=True, default='NIT', write_only=True)
    receptor_direccion = serializers.CharField(required=False, allow_blank=True, write_only=True)
    receptor_correo = serializers.CharField(required=False, allow_blank=True, write_only=True)
    nit_receptor = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    nombre_comercial_receptor = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    receptor_departamento = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    receptor_municipio = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    receptor_telefono = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    detalles = DetalleVentaSerializer(many=True, required=False, write_only=True)
    
    class Meta:
        model = Venta
        fields = '__all__'
    
    def _actualizar_cliente_si_cambia(self, cliente_obj, nombre, direccion, correo, **kwargs):
        """Actualiza el Cliente si los datos del formulario difieren de la BD.
        kwargs: nit, nombre_comercial, cod_actividad, desc_actividad, departamento, municipio, telefono
        """
        actualizar = False
        if nombre and (cliente_obj.nombre or '') != str(nombre).strip():
            cliente_obj.nombre = str(nombre).strip()
            actualizar = True
        if direccion is not None and (cliente_obj.direccion or '') != str(direccion).strip():
            cliente_obj.direccion = str(direccion).strip() or None
            actualizar = True
        if correo is not None:
            correo_limpio = str(correo).strip() or None
            if (cliente_obj.email_contacto or '') != (correo_limpio or ''):
                cliente_obj.email_contacto = correo_limpio
                actualizar = True
        for campo in ('nit', 'dui', 'tipo_documento', 'documento_identidad', 'nombre_comercial', 'cod_actividad', 'desc_actividad', 'departamento', 'municipio', 'telefono'):
            val = kwargs.get(campo)
            if val is not None:
                val_str = str(val).strip() if val else None
                actual = getattr(cliente_obj, campo, None) or ''
                if (val_str or '') != (actual or ''):
                    setattr(cliente_obj, campo, val_str or None)
                    actualizar = True
        if actualizar:
            cliente_obj.save()
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Crea una venta con sus detalles en una transacción atómica.
        CASO A: cliente_id -> Cliente existente, actualizar si form difiere.
        CASO B: cliente (NRC) -> get_or_create, actualizar si form difiere.
        CASO C: CF sin cliente -> venta.cliente=None, usar nombre_receptor/nrc_receptor.
        """
        detalles_data = validated_data.pop('detalles', [])
        cliente_input = validated_data.pop('cliente', None)
        cliente_id = validated_data.pop('cliente_id', None)
        tipo_dte = validated_data.pop('tipo_dte', None)
        documento_relacionado_id = validated_data.pop('documento_relacionado_id', None)
        documento_receptor = validated_data.pop('documento_receptor', None)
        tipo_doc_receptor = validated_data.pop('tipo_doc_receptor', None)
        receptor_direccion = validated_data.pop('receptor_direccion', None)
        receptor_correo = validated_data.pop('receptor_correo', None)
        nit_receptor = validated_data.pop('nit_receptor', None)
        nombre_comercial_receptor = validated_data.pop('nombre_comercial_receptor', None)
        receptor_departamento = validated_data.pop('receptor_departamento', None)
        receptor_municipio = validated_data.pop('receptor_municipio', None)
        receptor_telefono = validated_data.pop('receptor_telefono', None)
        tipo_venta = validated_data.get('tipo_venta', 'CCF')
        nombre_receptor = validated_data.get('nombre_receptor') or ''
        cod_act_receptor = validated_data.get('cod_actividad_receptor')
        desc_act_receptor = validated_data.get('desc_actividad_receptor')
        
        cliente_input_limpio = None
        if cliente_input and str(cliente_input).strip() and str(cliente_input).lower() != 'null':
            cliente_input_limpio = str(cliente_input).strip()
        
        cliente_obj = None
        if tipo_dte == '14':
            # CASO FSE: Factura Sujeto Excluido. El "cliente" del form es el PROVEEDOR informal.
            # No se registra como Cliente BD; se guarda en campos nombre_receptor/documento_receptor.
            validated_data['tipo_venta'] = 'FSE'
            validated_data['cliente'] = None
            validated_data['nombre_receptor'] = nombre_receptor.strip() or 'Proveedor Sujeto Excluido'
            validated_data['documento_receptor'] = str(documento_receptor).strip() if documento_receptor else None
            validated_data['tipo_doc_receptor'] = str(tipo_doc_receptor).strip() if tipo_doc_receptor else 'NIT'
            validated_data['direccion_receptor'] = str(receptor_direccion).strip() if receptor_direccion else None
            validated_data['correo_receptor'] = str(receptor_correo).strip() if receptor_correo else None
        elif tipo_venta == 'CF' and not cliente_input_limpio and not cliente_id:
            # CASO C: Consumidor Final (datos manuales del formulario)
            validated_data['cliente'] = None
            validated_data['nombre_receptor'] = nombre_receptor.strip() or 'Consumidor Final'
            validated_data['nrc_receptor'] = validated_data.get('nrc_receptor')
            validated_data['documento_receptor'] = str(documento_receptor).strip() if documento_receptor else None
            validated_data['tipo_doc_receptor'] = str(tipo_doc_receptor).strip() if tipo_doc_receptor else 'NIT'
            validated_data['direccion_receptor'] = str(receptor_direccion).strip() if receptor_direccion else None
            validated_data['correo_receptor'] = str(receptor_correo).strip() if receptor_correo else None
        elif cliente_id:
            # CASO A: Cliente existente por ID
            try:
                cliente_obj = Cliente.objects.get(pk=cliente_id)
                nit_raw = (nit_receptor or '').strip() or None
                nit_val = dui_val = tipo_doc = doc_dig = None
                if nit_raw:
                    doc_dig = ''.join(c for c in nit_raw if c.isdigit())
                    if len(doc_dig) == 10:
                        doc_dig = doc_dig[:9]
                    es_dui = len(doc_dig) == 9
                    tipo_doc = 'DUI' if es_dui else 'NIT'
                    nit_val = None if es_dui else nit_raw
                    dui_val = doc_dig if es_dui else None
                nom_com = (nombre_comercial_receptor or '').strip() or None
                dept = (receptor_departamento or '').strip() or None
                muni = (receptor_municipio or '').strip() or None
                tel = (receptor_telefono or '').strip() or None
                self._actualizar_cliente_si_cambia(
                    cliente_obj, nombre_receptor, receptor_direccion, receptor_correo,
                    nit=nit_val, dui=dui_val, tipo_documento=tipo_doc, documento_identidad=doc_dig,
                    nombre_comercial=nom_com, cod_actividad=cod_act_receptor,
                    desc_actividad=desc_act_receptor, departamento=dept, municipio=muni, telefono=tel
                )
            except Cliente.DoesNotExist:
                raise serializers.ValidationError({'cliente_id': 'Cliente no encontrado.'})
            validated_data['cliente'] = cliente_obj
        elif cliente_input_limpio:
            # CASO B: Cliente por NRC (get_or_create)
            # CCF requiere NIT o DUI (ley de homologación). 9 dígitos=DUI, 14 dígitos=NIT.
            nit_def = (nit_receptor or '').strip() or None
            if not nit_def:
                raise serializers.ValidationError({
                    'nit_receptor': 'Para Crédito Fiscal (CCF) se requiere NIT (14 dígitos) o DUI (9 dígitos) en columna "nit".'
                })
            doc_dig = ''.join(c for c in nit_def if c.isdigit())
            # Excel elimina ceros iniciales: 8 dígitos → DUI sin cero → completar a 9
            if len(doc_dig) == 8:
                doc_dig = '0' + doc_dig
            elif len(doc_dig) == 13:
                doc_dig = '0' + doc_dig
            elif len(doc_dig) == 10:
                doc_dig = doc_dig[:9]
            es_dui = len(doc_dig) == 9
            if es_dui:
                tipo_doc, nit_val, dui_val = 'DUI', None, doc_dig
            else:
                tipo_doc, nit_val, dui_val = 'NIT', nit_def, None
            empresa = validated_data.get('empresa')
            defaults = {
                'nombre': nombre_receptor.strip() or f'Cliente {cliente_input_limpio}',
                'nit': nit_val,
                'dui': dui_val,
                'tipo_documento': tipo_doc,
                'documento_identidad': doc_dig,
                'direccion': (receptor_direccion or '').strip() or None,
                'email_contacto': (receptor_correo or '').strip() or None,
                'cod_actividad': (cod_act_receptor or '').strip() or None,
                'desc_actividad': (desc_act_receptor or '').strip() or None,
                'departamento': (receptor_departamento or '').strip()[:2] or '06',
                'municipio': (receptor_municipio or '').strip()[:2] or '14',
                'telefono': (receptor_telefono or '').strip() or None,
                'nombre_comercial': (nombre_comercial_receptor or '').strip() or None,
            }
            if empresa:
                defaults['empresa'] = empresa
            lookup = {'nrc': cliente_input_limpio}
            if empresa:
                lookup['empresa'] = empresa
            else:
                lookup['empresa__isnull'] = True
            cliente_obj, _ = Cliente.objects.get_or_create(defaults=defaults, **lookup)
            nom_com = (nombre_comercial_receptor or '').strip() or None
            dept = (receptor_departamento or '').strip() or None
            muni = (receptor_municipio or '').strip() or None
            tel = (receptor_telefono or '').strip() or None
            self._actualizar_cliente_si_cambia(
                cliente_obj, nombre_receptor, receptor_direccion, receptor_correo,
                nit=nit_val, dui=dui_val, tipo_documento=tipo_doc, documento_identidad=doc_dig,
                nombre_comercial=nom_com, cod_actividad=cod_act_receptor,
                desc_actividad=desc_act_receptor, departamento=dept, municipio=muni, telefono=tel
            )
            validated_data['cliente'] = cliente_obj
        else:
            raise serializers.ValidationError({
                'cliente': 'Para CCF debes proporcionar cliente_id o cliente (NRC).'
            })
        
        # 2b. NC/ND requieren documento_relacionado_id
        if tipo_dte in ('05', '06') and not (documento_relacionado_id and str(documento_relacionado_id).strip()):
            raise serializers.ValidationError({
                'documento_relacionado_id': 'Nota de Crédito y Nota de Débito requieren el documento relacionado (factura original).'
            })
        
        # 2c. Tipo DTE para NC/ND: sobrescribir tipo_venta
        if tipo_dte in ('05', '06'):
            validated_data['tipo_venta'] = 'NC' if tipo_dte == '05' else 'ND'
        
        # 3. Redondear campos monetarios de la venta antes de crear
        campos_monetarios_venta = ['venta_gravada', 'venta_exenta', 'venta_no_sujeta', 'debito_fiscal']
        for campo in campos_monetarios_venta:
            if campo in validated_data and validated_data[campo] is not None:
                try:
                    valor = Decimal(str(validated_data[campo]))
                    validated_data[campo] = valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                except (ValueError, TypeError):
                    validated_data[campo] = Decimal('0.00')
            else:
                # Si no viene el campo, inicializar en 0
                validated_data[campo] = Decimal('0.00')

        # 3b. Ambiente de emisión: desde empresa para filtrar dashboard/ventas por ambiente
        empresa = validated_data.get('empresa')
        validated_data['ambiente_emision'] = (empresa.ambiente if empresa else '01')
        
        # 4. Crear la venta PRIMERO
        venta = Venta.objects.create(**validated_data)
        
        # 5. Crear los detalles DESPUÉS de crear la venta
        for idx, detalle_raw in enumerate(detalles_data):
            # Extraer producto_id si existe
            producto_id = detalle_raw.pop('producto_id', None)
            producto_obj = None
            if producto_id:
                try:
                    producto_obj = Producto.objects.get(id=producto_id)
                except Producto.DoesNotExist:
                    # Si el producto no existe, continuar sin producto (item libre)
                    pass
            
            # Preparar datos del detalle
            detalle_data = {}
            
            # Campos de texto
            if 'descripcion_libre' in detalle_raw:
                detalle_data['descripcion_libre'] = detalle_raw.get('descripcion_libre', '')
            if 'codigo_libre' in detalle_raw:
                detalle_data['codigo_libre'] = detalle_raw.get('codigo_libre', '')
            
            # Asegurar numero_item
            detalle_data['numero_item'] = detalle_raw.get('numero_item', idx + 1)
            
            # Consumidor Final (01): el precio ingresado es TOTAL con IVA. Normalizar para no guardar total como gravado.
            if tipo_dte == '01':
                try:
                    cant = Decimal(str(detalle_raw.get('cantidad', 1)))
                    prec = Decimal(str(detalle_raw.get('precio_unitario', 0)))
                    total_linea = (cant * prec).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    vg_raw = Decimal(str(detalle_raw.get('venta_gravada', 0)))
                    iva_raw = Decimal(str(detalle_raw.get('iva_item', 0)))
                except (ValueError, TypeError):
                    total_linea = vg_raw = iva_raw = Decimal('0.00')
                # Si venta_gravada parece "total con IVA" (ej. 1000) e iva ≈ total - total/1.13, normalizar
                if total_linea > 0:
                    iva_si_total = (vg_raw - vg_raw / Decimal('1.13')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    if abs(iva_raw - iva_si_total) <= Decimal('0.03'):
                        total_con_iva = vg_raw
                    else:
                        total_con_iva = (vg_raw + iva_raw).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    monto_gravado = (total_con_iva / Decimal('1.13')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    iva_linea = (total_con_iva - monto_gravado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    detalle_data['venta_gravada'] = monto_gravado
                    detalle_data['iva_item'] = iva_linea
                    detalle_data['precio_unitario'] = (monto_gravado / cant).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if cant else Decimal('0.00')
                    detalle_data['cantidad'] = cant
                    detalle_data['monto_descuento'] = Decimal(str(detalle_raw.get('monto_descuento', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    detalle_data['venta_no_sujeta'] = Decimal(str(detalle_raw.get('venta_no_sujeta', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    detalle_data['venta_exenta'] = Decimal(str(detalle_raw.get('venta_exenta', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                else:
                    for campo in ['cantidad', 'precio_unitario', 'monto_descuento', 'venta_no_sujeta', 'venta_exenta', 'venta_gravada', 'iva_item']:
                        valor_raw = detalle_raw.get(campo, 0)
                        try:
                            detalle_data[campo] = Decimal(str(valor_raw)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        except (ValueError, TypeError):
                            detalle_data[campo] = Decimal('0.00')
            else:
                # Campos decimales (no CF): convertir y redondear
                campos_decimales = [
                    'cantidad', 'precio_unitario', 'monto_descuento',
                    'venta_no_sujeta', 'venta_exenta', 'venta_gravada', 'iva_item'
                ]
                for campo in campos_decimales:
                    valor_raw = detalle_raw.get(campo, 0)
                    try:
                        valor = Decimal(str(valor_raw))
                        detalle_data[campo] = valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    except (ValueError, TypeError):
                        detalle_data[campo] = Decimal('0.00')
            
            # Crear el detalle pasando explícitamente la venta
            DetalleVenta.objects.create(
                venta=venta,
                producto=producto_obj,
                **detalle_data
            )
        
        # 6. Recalcular totales desde los detalles (sobrescribe los valores enviados)
        venta.calcular_totales()
        venta.save()
        
        # 6b. Documento relacionado (NC/ND): atributos para DTE05/06 builder
        if documento_relacionado_id and str(documento_relacionado_id).strip():
            doc_rel_id_clean = str(documento_relacionado_id).strip()
            orig = Venta.objects.filter(codigo_generacion__iexact=doc_rel_id_clean).first()
            if orig:
                venta.documento_relacionado_codigo = orig.codigo_generacion
                venta.documento_relacionado_numero_control = orig.numero_control
                venta.documento_relacionado_fecha_emision = orig.fecha_emision
                venta.documento_relacionado_tipo = '01' if orig.tipo_venta == 'CF' else '03'
                venta.documento_relacionado_tipo_generacion = 2
            else:
                venta.documento_relacionado_codigo = doc_rel_id_clean
                venta.documento_relacionado_numero_control = None
                venta.documento_relacionado_fecha_emision = venta.fecha_emision
                venta.documento_relacionado_tipo = '03'
                venta.documento_relacionado_tipo_generacion = 2
            # Persistir la referencia para poder detectar desde el DTE original si tiene NC/ND
            venta.codigo_generacion_referenciado = doc_rel_id_clean
            venta.save(update_fields=['codigo_generacion_referenciado'])
        
        # 7. Generar DTE automáticamente si estado es 'Generado'
        if venta.estado_dte == 'Generado':
            try:
                from .dte_generator import DTEGenerator, CorrelativoDTE
                
                # Generar código y número de control si no existen
                if not venta.codigo_generacion:
                    import uuid
                    venta.codigo_generacion = str(uuid.uuid4()).upper()
                
                if not venta.numero_control:
                    tmap = {'CF': '01', 'CCF': '03', 'NC': '05', 'ND': '06', 'FSE': '14'}
                    tipo_dte = tmap.get(venta.tipo_venta, '03')
                    venta.numero_control = CorrelativoDTE.obtener_siguiente_correlativo(
                        empresa_id=venta.empresa.id if venta.empresa else None,
                        tipo_dte=tipo_dte
                    )
                
                venta.save()
            except Exception as e:
                # Si falla la generación del DTE, no fallar toda la transacción
                # La venta ya está guardada, solo registrar el error
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error generando DTE para venta {venta.id}: {str(e)}")
        
        return venta