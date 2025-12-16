from rest_framework import serializers
from .models import Cliente, Compra, Venta, Retencion, Empresa  # <-- agrega Empresa aquí

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'

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

class VentaSerializer(serializers.ModelSerializer):
    # Campo explícito para aceptar NRC del cliente desde el frontend
    cliente = serializers.CharField(required=False)
    
    class Meta:
        model = Venta
        fields = '__all__'

    def to_representation(self, instance):
        """
        Sobrescribe la representación para incluir nrc_receptor y nombre_receptor
        desde la relación cliente, permitiendo que el frontend los reciba.
        """
        representation = super().to_representation(instance)
        # Agregar campos planos desde la relación cliente
        if instance.cliente:
            representation['nrc_receptor'] = instance.cliente.nrc
            representation['nombre_receptor'] = instance.cliente.nombre
            # También incluir el NRC como string para compatibilidad
            representation['cliente'] = instance.cliente.nrc
        else:
            representation['nrc_receptor'] = None
            representation['nombre_receptor'] = None
            representation['cliente'] = None
        return representation

    def create(self, validated_data):
        """
        Lógica especial para manejar Consumidor Final:
        - Si tipo_venta es "CF" y no hay cliente (o viene null/vacío), crea/usa cliente genérico
        - Si tipo_venta es "CCF", requiere cliente específico
        """
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
        return super().create(validated_data)

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