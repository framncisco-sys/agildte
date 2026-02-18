"""
Servicio para generar archivos JSON de DTE (Documento Tributario Electrónico)
según el estándar del Ministerio de Hacienda de El Salvador.
"""
import uuid
from datetime import datetime, timezone, timedelta

# Zona horaria de El Salvador (UTC-6) para fecEmi/horEmi
TZ_EL_SALVADOR = timezone(timedelta(hours=-6))
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from .models import Venta, Empresa, Cliente


def obtener_codigo_departamento_municipio(departamento_nombre=None, municipio_nombre=None):
    """
    Mapea nombres de departamento/municipio a códigos según estándar MH.
    Formato: "DDMM" donde DD = código departamento (2 dígitos), MM = código municipio (2 dígitos)
    
    Ejemplo: "0614" = Departamento 06 (San Salvador), Municipio 14 (San Salvador)
    
    Returns:
        str: Código combinado "DDMM" o "0614" por defecto (San Salvador)
    """
    # Mapeo básico de departamentos (códigos comunes en El Salvador)
    # Departamento 06 = San Salvador
    # Municipio 14 = San Salvador (ciudad)
    
    # Por defecto, usar San Salvador (0614)
    codigo_default = "0614"
    
    if not departamento_nombre and not municipio_nombre:
        return codigo_default
    
    # Si se proporciona un código directamente (formato "DDMM"), usarlo
    if isinstance(departamento_nombre, str) and len(departamento_nombre) == 4 and departamento_nombre.isdigit():
        return departamento_nombre
    
    # Mapeo simplificado (extender según necesidad)
    # Por ahora, siempre retornamos el código por defecto
    # TODO: Implementar mapeo completo de departamentos/municipios de El Salvador
    return codigo_default


def formatear_decimal(valor, decimales=2):
    """
    Formatea un valor numérico a Decimal con la cantidad de decimales especificada.
    
    Args:
        valor: Valor numérico (int, float, Decimal, str, None)
        decimales: Número de decimales (default: 2)
    
    Returns:
        Decimal: Valor formateado con los decimales especificados
    """
    if valor is None:
        return Decimal('0.00')
    
    try:
        decimal = Decimal(str(valor))
        # Redondear a los decimales especificados
        factor = Decimal('10') ** decimales
        return (decimal * factor).quantize(Decimal('1'), rounding=ROUND_HALF_UP) / factor
    except (ValueError, TypeError):
        return Decimal('0.00')


def _complemento_receptor(valor):
    """Complemento de direccion: usar 'San Miguel' para prueba (evitar '...')."""
    return "San Miguel"


def _es_valor_vacio(valor):
    """True si el valor debe omitirse (None, "", o string solo espacios). V3: no enviar null."""
    if valor is None:
        return True
    if isinstance(valor, str) and (not valor or not valor.strip()):
        return True
    return False


def limpiar_nulos(diccionario, campos_requeridos=None):
    """
    Elimina recursivamente claves con valor None o "" del diccionario.
    REGLA DE ORO V3: Si un campo es opcional y su valor es None o "", ELIMINAR LA LLAVE.
    
    Args:
        diccionario: Diccionario a limpiar
        campos_requeridos: Lista de rutas de campos que deben mantenerse aunque sean None
                          (ej: ['receptor.nrc'] para DTE-01)
    
    Returns:
        dict: Diccionario sin claves null/vacías (excepto campos requeridos)
    """
    if not isinstance(diccionario, dict):
        return diccionario
    
    if campos_requeridos is None:
        campos_requeridos = []
    
    resultado = {}
    for clave, valor in diccionario.items():
        ruta_campo = clave
        
        if _es_valor_vacio(valor):
            # Mantener si: está en requeridos, o es prefijo de uno, o es sufijo (ej. "referencia" en "pagos.referencia")
            if (ruta_campo in campos_requeridos or
                any(ruta.startswith(f"{ruta_campo}.") for ruta in campos_requeridos) or
                any(ruta.endswith(f".{ruta_campo}") for ruta in campos_requeridos)):
                resultado[clave] = None
            continue
        elif isinstance(valor, dict):
            # Limpiar recursivamente diccionarios anidados
            campos_requeridos_hijo = [ruta.split('.', 1)[1] for ruta in campos_requeridos if ruta.startswith(f"{ruta_campo}.")]
            valor_limpio = limpiar_nulos(valor, campos_requeridos_hijo)
            if valor_limpio:  # Solo agregar si el diccionario no está vacío
                resultado[clave] = valor_limpio
        elif isinstance(valor, list):
            # Limpiar elementos de listas
            lista_limpia = [limpiar_nulos(item, campos_requeridos) if isinstance(item, dict) else item for item in valor if item is not None]
            if lista_limpia:  # Solo agregar si la lista no está vacía
                resultado[clave] = lista_limpia
        else:
            # Agregar valores no-null
            resultado[clave] = valor
    
    return resultado


class CorrelativoDTE:
    """
    Clase para manejar correlativos de números de control DTE con reinicio anual automático.
    Formato: DTE-{tipo}-{codEstable}{codPunto}-{correlativo_15_digitos}
    Ejemplo: DTE-01-M001P001-000000000000001
    """
    
    @staticmethod
    def obtener_siguiente_correlativo(empresa_id, tipo_dte='03', sucursal='M001', punto='P001'):
        """
        Obtiene el siguiente número correlativo para un DTE con reinicio anual automático.
        Formato estricto: DTE-{tipo}-{codEstable}{codPunto}-{correlativo_15_digitos}
        Total: 31 caracteres exactos
        Ejemplo: DTE-01-M001P001-000000000000001
        
        El correlativo se reinicia automáticamente a 1 cada año nuevo.
        
        Args:
            empresa_id: ID de la empresa
            tipo_dte: Tipo de DTE ('01' para Factura CF, '03' para Crédito Fiscal)
            sucursal: Código de establecimiento (ej: 'M001')
            punto: Código de punto de venta (ej: 'P001')
        
        Returns:
            str: Número de control formateado con exactamente 31 caracteres
        """
        from .models import Correlativo, Empresa
        from django.db import transaction
        from datetime import datetime
        
        # Validar que empresa_id existe
        if not empresa_id:
            raise ValueError("empresa_id es requerido para generar el correlativo")
        
        # Obtener el año actual
        anio_actual = datetime.now().year
        
        # Usar transacción + select_for_update para evitar condiciones de carrera en concurrencia
        from django.db import IntegrityError
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    correlativo_obj, _ = Correlativo.objects.select_for_update().get_or_create(
                        empresa_id=empresa_id,
                        tipo_dte=tipo_dte,
                        anio=anio_actual,
                        defaults={'ultimo_correlativo': 0}
                    )
                    correlativo_obj.ultimo_correlativo += 1
                    correlativo_obj.save()
                    correlativo = correlativo_obj.ultimo_correlativo
                break
            except IntegrityError:
                if attempt == max_retries - 1:
                    raise
                continue
        
        # Formatear correlativo con 15 dígitos (parte final del número de control)
        correlativo_formateado = str(correlativo).zfill(15)
        
        # Construir número de control: DTE-{tipo}-{codEstable}{codPunto}-{correlativo}
        # Ejemplo: DTE-01-M001P001-000000000000001 (31 caracteres)
        numero_control = f"DTE-{tipo_dte}-{sucursal}{punto}-{correlativo_formateado}"
        
        # Validar que tenga exactamente 31 caracteres
        if len(numero_control) != 31:
            raise ValueError(
                f"El número de control debe tener 31 caracteres, tiene {len(numero_control)}: {numero_control}"
            )
        
        return numero_control


class DTEGenerator:
    """
    Generador de archivos JSON DTE a partir de una Venta.
    """
    
    def __init__(self, venta):
        if not isinstance(venta, Venta):
            raise ValueError("Se requiere una instancia de Venta")
        self.venta = venta
        self.empresa = venta.empresa
    
    def generar_json(self, ambiente='00', generar_codigo=True, generar_numero_control=True):
        """
        Genera el JSON completo del DTE según el estándar del MH.
        
        Args:
            ambiente: '00' = Producción, '01' = Pruebas
            generar_codigo: Si True, genera un nuevo UUID si no existe
            generar_numero_control: Si True, genera un nuevo número de control si no existe
        """
        # Generar identificadores si no existen
        if generar_codigo and not self.venta.codigo_generacion:
            self.venta.codigo_generacion = str(uuid.uuid4()).upper()
        
        if generar_numero_control and not self.venta.numero_control:
            tipo_dte = '01' if self.venta.tipo_venta == 'CF' else '03'
            # Obtener códigos de establecimiento desde empresa (o usar defaults)
            cod_estable = self.empresa.cod_establecimiento if self.empresa else 'M001'
            cod_estable = cod_estable.strip() if cod_estable and cod_estable.strip() else 'M001'
            
            cod_punto_venta = self.empresa.cod_punto_venta if self.empresa else 'P001'
            cod_punto_venta = cod_punto_venta.strip() if cod_punto_venta and cod_punto_venta.strip() else 'P001'
            
            self.venta.numero_control = CorrelativoDTE.obtener_siguiente_correlativo(
                empresa_id=self.empresa.id if self.empresa else None,
                tipo_dte=tipo_dte,
                sucursal=cod_estable,
                punto=cod_punto_venta
            )
        
        # Obtener fecha y hora actual (hora real de El Salvador UTC-6)
        fecha_emision = self.venta.fecha_emision
        ahora_sv = datetime.now(TZ_EL_SALVADOR)
        hora_actual = ahora_sv.strftime('%H:%M:%S')
        fecha_str = fecha_emision.strftime('%Y-%m-%d')
        
        # Construir el JSON
        # CRÍTICO: Generar cuerpo documento primero para recalcular IVA
        # Luego usar esos valores recalculados en el resumen
        cuerpo_documento = self._generar_cuerpo_documento()
        
        # Campos raíz requeridos por esquema MH (pueden ser null/array vacío)
        extension_data = self._generar_extension()
        dte_json = {
            "identificacion": self._generar_identificacion(ambiente, fecha_str, hora_actual),
            "documentoRelacionado": None,  # null si no hay documentos relacionados
            "emisor": self._generar_emisor(),
            "receptor": self._generar_receptor(),
            "otrosDocumentos": None,
            "ventaTercero": None,
            "cuerpoDocumento": cuerpo_documento,
            "resumen": self._generar_resumen(cuerpo_documento),
            "extension": extension_data,
            "apendice": None,
        }
        
        # Aplicar limpieza específica según reglas del esquema
        dte_json_limpio = self._limpiar_diccionario_dte(dte_json)
        
        return dte_json_limpio
    
    def _obtener_tipo_dte(self):
        """Obtiene el tipo de DTE según el tipo de venta."""
        return '01' if self.venta.tipo_venta == 'CF' else '03'
    
    def _limpiar_diccionario_dte(self, dte_json):
        """
        Limpia el diccionario DTE. Mantiene campos requeridos por MH aunque sean null.
        """
        import copy
        dte_limpio = copy.deepcopy(dte_json)

        # Campos que MH exige presentes (pueden ser null)
        campos_requeridos_mh = [
            "identificacion.tipoContingencia", "identificacion.motivoContin",
            "documentoRelacionado", "otrosDocumentos", "ventaTercero", "extension", "apendice",
            "extension.nombEntrega", "extension.docuEntrega", "extension.nombRecibe",
            "extension.docuRecibe", "extension.observaciones", "extension.placaVehiculo",
            "emisor.codEstableMH", "emisor.codEstable", "emisor.codPuntoVentaMH", "emisor.codPuntoVenta",
            "emisor.nombreComercial",
            "resumen.numPagoElectronico", "resumen.ivaRete1",
            "resumen.pagos.referencia", "resumen.pagos.periodo", "resumen.pagos.plazo",
            "cuerpoDocumento.numeroDocumento", "cuerpoDocumento.codTributo",
        ]
        dte_limpio = limpiar_nulos(dte_limpio, campos_requeridos=campos_requeridos_mh)

        # Resumen: eliminar solo reteIVA si es 0 (ivaRete1 es requerido por MH)
        if "resumen" in dte_limpio and isinstance(dte_limpio["resumen"], dict):
            resumen = dte_limpio["resumen"]
            if "reteIVA" in resumen and (resumen["reteIVA"] == 0 or resumen["reteIVA"] == 0.0):
                del resumen["reteIVA"]

        return dte_limpio
    
    def _generar_identificacion(self, ambiente, fecha_str, hora_actual):
        """Genera la sección de identificación del DTE."""
        tipo_dte = '01' if self.venta.tipo_venta == 'CF' else '03'
        
        # Asegurar que numeroControl tenga el formato correcto (31 caracteres)
        numero_control = self.venta.numero_control or ""
        if not numero_control or len(numero_control) != 31:
            # Generar número de control si no existe o no tiene el formato correcto
            tipo_dte_code = tipo_dte
            # Obtener códigos de establecimiento desde empresa (o usar defaults)
            cod_estable = self.empresa.cod_establecimiento if self.empresa else 'M001'
            cod_estable = cod_estable.strip() if cod_estable and cod_estable.strip() else 'M001'
            
            cod_punto_venta = self.empresa.cod_punto_venta if self.empresa else 'P001'
            cod_punto_venta = cod_punto_venta.strip() if cod_punto_venta and cod_punto_venta.strip() else 'P001'
            
            self.venta.numero_control = CorrelativoDTE.obtener_siguiente_correlativo(
                empresa_id=self.empresa.id if self.empresa else None,
                tipo_dte=tipo_dte_code,
                sucursal=cod_estable,
                punto=cod_punto_venta
            )
            numero_control = self.venta.numero_control
        
        # Validar formato de numeroControl
        if len(numero_control) != 31:
            raise ValueError(f"numeroControl debe tener exactamente 31 caracteres. Actual: {len(numero_control)} - '{numero_control}'")
        
        # Generar código de generación si no existe
        # CRÍTICO: codigoGeneracion debe estar en MAYÚSCULAS según el esquema
        codigo_generacion = self.venta.codigo_generacion or str(uuid.uuid4())
        codigo_generacion = codigo_generacion.upper()  # Convertir a mayúsculas
        
        # Para operación normal (tipoModelo=1), los campos de contingencia deben estar presentes como null
        # DTE-03 (Crédito Fiscal): Versión 3 según Catálogo 2025 (sin ivaItem en items)
        # DTE-01 (Factura CF): Versión 1 (estructura clásica)
        version_dte = 3 if tipo_dte == '03' else 1  # DTE-01 → v1, DTE-03 → v3
        
        identificacion = {
            "version": int(version_dte),
            "ambiente": ambiente,
            "tipoDte": tipo_dte,
            "numeroControl": numero_control,
            "codigoGeneracion": codigo_generacion,
            "fecEmi": fecha_str,
            "horEmi": hora_actual,
            "tipoModelo": 1,
            "tipoOperacion": 1,
            "tipoContingencia": None,  # Requerido por esquema MH (null = operación normal)
            "motivoContin": None,
            "tipoMoneda": "USD",
        }
        # Si en el futuro se necesita contingencia, agregar aquí:
        # if tipo_contingencia:
        #     identificacion["tipoContingencia"] = tipo_contingencia
        #     identificacion["motivoContingencia"] = motivo
        #     identificacion["fecVenContingencia"] = fecha_vencimiento
        
        return identificacion
    
    def _generar_emisor(self):
        """Genera la sección del emisor (empresa que factura)."""
        if not self.empresa:
            raise ValueError("La venta debe tener una empresa asociada")
        
        # Datos del emisor desde el modelo Empresa
        # Usar campos de actividad de la empresa si están configurados
        cod_actividad = self.empresa.cod_actividad or "62010"  # Por defecto si no está configurado
        desc_actividad = self.empresa.desc_actividad or "Desarrollo de software"  # Por defecto
        
        # Obtener códigos de departamento/municipio desde el modelo Empresa
        # CRÍTICO: 
        # - departamento debe ser código de 2 dígitos (DD)
        # - municipio debe ser código de 2 dígitos (MM) - NO 4 dígitos
        # Asegurar longitud fija rellenando con ceros si es necesario
        codigo_departamento_raw = self.empresa.departamento or "06"
        codigo_departamento = str(codigo_departamento_raw).strip().zfill(2)  # Asegurar 2 dígitos
        
        codigo_municipio_raw = self.empresa.municipio or "14"
        codigo_municipio = str(codigo_municipio_raw).strip().zfill(2)  # Asegurar 2 dígitos (NO 4)
        
        # Limpiar NIT (sin guiones ni espacios)
        nit_limpio = (self.empresa.nit or self.empresa.nrc or "").replace('-', '').replace(' ', '')
        
        # Obtener códigos de establecimiento desde el modelo Empresa
        # Validar que no sean cadenas vacías - usar defaults si están vacíos
        cod_estable = self.empresa.cod_establecimiento or 'M001'
        cod_estable = cod_estable.strip() if cod_estable and cod_estable.strip() else 'M001'
        
        cod_punto_venta = self.empresa.cod_punto_venta or 'P001'
        cod_punto_venta = cod_punto_venta.strip() if cod_punto_venta and cod_punto_venta.strip() else 'P001'
        
        # Esquema MH fe-fc-v1 / fe-ccf-v3: requieren los 4 campos (codEstableMH puede ser null si MH no asignó)
        emisor = {
            "nit": nit_limpio,
            "nrc": self.empresa.nrc,
            "nombre": self.empresa.nombre,
            "codActividad": cod_actividad,
            "descActividad": desc_actividad,
            "tipoEstablecimiento": "01",
            "direccion": {
                "departamento": codigo_departamento,
                "municipio": codigo_municipio,
                "complemento": (self.empresa.direccion or "").strip()
            },
            "codEstableMH": cod_estable,   # MH: null si no asignó; usar nuestro código
            "codEstable": cod_estable,     # Contribuyente
            "codPuntoVentaMH": cod_punto_venta,
            "codPuntoVenta": cod_punto_venta
        }
        # nombreComercial requerido por MH; si Empresa no tiene nombre_comercial, usar nombre
        nom_com = getattr(self.empresa, 'nombre_comercial', None) or ''
        emisor["nombreComercial"] = (nom_com or self.empresa.nombre or "Empresa").strip() or "Empresa"
        
        # Agregar campos opcionales desde el modelo
        if self.empresa.telefono:
            emisor["telefono"] = self.empresa.telefono
        if self.empresa.correo:
            emisor["correo"] = self.empresa.correo
        
        return emisor
    
    def _generar_receptor(self):
        """
        Genera la sección del receptor (cliente) según el tipo de DTE.
        
        LÓGICA PARA EL SALVADOR:
        - DTE-03 (Crédito Fiscal): nrc es OBLIGATORIO
        - DTE-01 (Consumidor Final): nrc NO DEBE EXISTIR, nombreComercial NO DEBE EXISTIR
          - Sub-caso A: Cliente con DUI/NIT → enviar tipoDocumento y numDocumento
          - Sub-caso B: Cliente genérico sin documentos → omitir campos según esquema
        """
        cliente = self.venta.cliente
        tipo_dte = '01' if self.venta.tipo_venta == 'CF' else '03'
        
        # Obtener código de departamento/municipio desde el cliente
        # CRÍTICO: municipio debe ser 2 dígitos, no 4
        # Priorizar los valores del cliente, usar defaults si están vacíos
        codigo_departamento_raw = getattr(cliente, 'departamento', None) or '06'
        codigo_departamento = str(codigo_departamento_raw).strip().zfill(2)  # Asegurar 2 dígitos
        
        codigo_municipio_raw = getattr(cliente, 'municipio', None) or '14'
        codigo_municipio = str(codigo_municipio_raw).strip().zfill(2)  # Asegurar 2 dígitos (NO 4)
        
        # ============================================
        # CASO 1: DTE-03 (CRÉDITO FISCAL) - Normativa 2025
        # ============================================
        if tipo_dte == '03':
            # VALIDACIÓN: nrc es OBLIGATORIO para DTE-03
            # Si es ambiente de pruebas ('00') y no hay NRC, usar genérico de prueba
            ambiente_actual = getattr(self.venta.empresa, 'ambiente', '00') if self.venta.empresa else '00'
            if not cliente.nrc:
                if ambiente_actual == '00':
                    # En pruebas, usar NRC genérico
                    nrc_cliente = "0000000"
                else:
                    # En producción, lanzar error
                    raise ValueError(
                        f"Error: El cliente '{cliente.nombre}' no tiene NRC. "
                        "Para emitir un Crédito Fiscal (DTE-03), el cliente debe ser un Contribuyente con NRC."
                    )
            else:
                nrc_cliente = cliente.nrc
            
            # Limpiar NIT (sin guiones ni espacios)
            nit_limpio = (cliente.nit or cliente.nrc or "").replace('-', '').replace(' ', '')
            
            # Obtener nombre: usar nombre_comercial, razon_social o nombre del cliente
            # Si el modelo no tiene estos campos, usar nombre directamente
            nombre_cliente = (
                getattr(cliente, 'nombre_comercial', None) or 
                getattr(cliente, 'razon_social', None) or 
                cliente.nombre
            )
            nombre_receptor = self.venta.nombre_receptor or nombre_cliente
            
            # Obtener codActividad y descActividad del cliente
            # CRÍTICO: Estos campos son OBLIGATORIOS para DTE-03 según normativa 2025 (CAT-019)
            # Si no existen en el cliente, usar valores por defecto según CAT-019
            cod_actividad_cliente = cliente.cod_actividad if cliente.cod_actividad else "10005"  # "10005" = Otros
            desc_actividad_cliente = cliente.desc_actividad if cliente.desc_actividad else (cliente.giro or "Otros")
            
            # CRÍTICO: Construir receptor con todos los campos obligatorios para DTE-03
            # SEGÚN EJEMPLO MH: El receptor DTE-03 usa "nit" directamente, NO "tipoDocumento"/"numDocumento"
            telefono_receptor = getattr(cliente, 'telefono', None) or "22222222"
            nombre_comercial = (
                getattr(cliente, 'nombre_comercial', None) or
                getattr(cliente, 'razon_social', None) or
                nombre_receptor
            )
            receptor = {
                "nit": nit_limpio or "00000000000000",
                "nrc": nrc_cliente,
                "nombre": nombre_receptor,
                "nombreComercial": nombre_comercial,  # Requerido CCF v3
                "codActividad": cod_actividad_cliente,
                "descActividad": desc_actividad_cliente,
                "direccion": {
                    "departamento": codigo_departamento,
                    "municipio": codigo_municipio,
                    "complemento": _complemento_receptor(cliente.direccion)
                },
                "telefono": telefono_receptor
            }
            if cliente.email_contacto:
                receptor["correo"] = cliente.email_contacto
            
            return receptor
        
        # ============================================
        # CASO 2: DTE-01 (CONSUMIDOR FINAL)
        # ============================================
        # CRÍTICO: Para DTE-01, nrc debe ser None (no eliminarlo)
        # nombreComercial NO DEBE EXISTIR
        # PERO: otros campos opcionales DEBEN ir como null si no tienen valor
        
        # Determinar nombre del receptor
        nombre_receptor = self.venta.nombre_receptor or cliente.nombre or "Clientes Varios"
        
        # SUB-CASO A: Cliente con DUI o NIT
        tiene_nit = cliente.nit and cliente.nit.strip()
        tiene_dui = cliente.dui and cliente.dui.strip()
        
        if tiene_nit or tiene_dui:
            # Cliente tiene documento de identidad
            if tiene_nit:
                tipo_documento = "36"  # 36 = NIT
                num_documento = cliente.nit.replace('-', '').replace(' ', '').zfill(14)
            else:  # tiene_dui
                tipo_documento = "13"  # 13 = DUI
                num_documento = cliente.dui.replace('-', '').replace(' ', '').zfill(14)
            
            telefono_receptor = getattr(cliente, 'telefono', None) or "22222222"
            receptor = {
                "tipoDocumento": tipo_documento,
                "numDocumento": num_documento,
                "nombre": nombre_receptor,
                "nrc": None,  # CRÍTICO: Para DTE-01, nrc debe ser None (no eliminarlo)
                # Campos opcionales como null si no tienen valor
                "codActividad": None,
                "descActividad": None,
                "direccion": None if not cliente.direccion else {
                    "departamento": codigo_departamento,
                    "municipio": codigo_municipio,  # 2 dígitos
                    "complemento": cliente.direccion
                },
                "telefono": telefono_receptor,
                "correo": cliente.email_contacto if cliente.email_contacto else None,
            }
            
            # NOTA: nombreComercial NO se incluye (no debe existir en DTE-01)
            return receptor
        
        # SUB-CASO B: Cliente genérico sin documentos (ej: "Clientes Varios")
        # Para ventas menores o clientes genéricos sin identificación
        telefono_receptor = getattr(cliente, 'telefono', None) or "22222222"
        receptor = {
            "tipoDocumento": None,  # null si no tiene DUI/NIT
            "numDocumento": None,   # null si no tiene DUI/NIT
            "nombre": nombre_receptor,
            "nrc": None,  # CRÍTICO: Para DTE-01, nrc debe ser None (no eliminarlo)
            # Campos opcionales explícitamente como null
            "codActividad": None,
            "descActividad": None,
            "direccion": None if not cliente.direccion else {
                "departamento": codigo_departamento,
                "municipio": codigo_municipio,
                "complemento": cliente.direccion
            },
            "telefono": telefono_receptor,
            "correo": cliente.email_contacto if cliente.email_contacto else None,
        }
        
        # NOTA CRÍTICA: nrc es None (no se elimina)
        # nombreComercial NO se incluye (no debe existir en DTE-01)
        return receptor
    
    def _generar_cuerpo_documento(self):
        """
        Genera el cuerpo del documento (productos/servicios) desde DetalleVenta.
        
        LÓGICA CONDICIONAL:
        - DTE-01 (Factura): tributos debe ser None (IVA incluido, no se desglosa)
        - DTE-03 (Crédito Fiscal): tributos debe ser ["20"] si es gravado
        """
        items = []
        tipo_dte = self._obtener_tipo_dte()
        
        # Obtener detalles de la venta
        detalles = self.venta.detalles.all().order_by('numero_item')
        
        if detalles.exists():
            # Usar detalles reales
            for detalle in detalles:
                codigo = detalle.producto.codigo if detalle.producto else (detalle.codigo_libre or "LIBRE")
                descripcion = detalle.producto.descripcion if detalle.producto else (detalle.descripcion_libre or "Item")
                tipo_item = detalle.producto.tipo_item if detalle.producto else 1
                
                # CRÍTICO: Convertir precio_unitario y cantidad a float antes de operar
                precio_unitario = float(formatear_decimal(detalle.precio_unitario))
                cantidad = float(formatear_decimal(detalle.cantidad))
                monto_descuento = float(formatear_decimal(detalle.monto_descuento))
                
                # Calcular monto_total_linea (precio * cantidad) - descuento
                monto_total_linea = round(precio_unitario * cantidad, 2) - monto_descuento
                
                # Inicializar las 3 variables de venta en 0.0
                v_gravada = 0.0
                v_exenta = 0.0
                v_nosujeta = 0.0
                
                # Determinar el tipo de producto basándome en los valores del detalle
                # Si tiene venta_gravada > 0, es gravado
                # Si tiene venta_exenta > 0, es exento
                # Si tiene venta_no_sujeta > 0, es no sujeta
                detalle_venta_gravada = float(formatear_decimal(detalle.venta_gravada))
                detalle_venta_exenta = float(formatear_decimal(detalle.venta_exenta))
                detalle_venta_no_sujeta = float(formatear_decimal(detalle.venta_no_sujeta))
                
                # Distribuir el monto según el tipo
                if detalle_venta_gravada > 0:
                    # Es gravado
                    v_gravada = round(monto_total_linea, 2)
                elif detalle_venta_exenta > 0:
                    # Es exento
                    v_exenta = round(monto_total_linea, 2)
                elif detalle_venta_no_sujeta > 0:
                    # Es no sujeta
                    v_nosujeta = round(monto_total_linea, 2)
                else:
                    # Si no hay clasificación clara, asumir gravado por defecto
                    v_gravada = round(monto_total_linea, 2)
                
                # Recalcular IVA según el tipo de DTE (solo si es gravado)
                es_gravado = v_gravada > 0
                if es_gravado:
                    if tipo_dte == '01':
                        # DTE-01 (Factura): El precio incluye IVA
                        # ventaGravada debe ser el monto total (con IVA incluido)
                        # ivaItem es el IVA extraído del monto total
                        iva_item_calculado = round(v_gravada - (v_gravada / 1.13), 2)
                        # v_gravada se mantiene como monto total (no se divide por 1.13)
                    else:
                        # DTE-03 (Crédito Fiscal): El precio es más IVA
                        # ventaGravada es el monto base, IVA se calcula sobre ese monto
                        iva_item_calculado = round(v_gravada * 0.13, 2)
                else:
                    # No es gravado (exento o no sujeta)
                    iva_item_calculado = 0.00
                
                # DTE-01: tributos puede ser null/vacío; DTE-03: tributos ["20"] si es gravado
                if tipo_dte == '01':
                    tributos_value = None
                else:
                    tributos_value = ["20"] if es_gravado else []
                
                # CRÍTICO: Para DTE-03 Versión 1, ivaItem DEBE llevar el valor calculado (obligatorio)
                item = {
                    "numItem": detalle.numero_item,
                    "tipoItem": tipo_item,
                    "numeroDocumento": None,  # Requerido aunque sea null
                    "codigo": codigo if codigo else None,  # Puede ser null según ejemplo
                    "codTributo": None,
                    "descripcion": descripcion,
                    "cantidad": cantidad,
                    "uniMedida": 59,  # 59 = Unidad
                    "precioUni": precio_unitario,
                    "montoDescu": monto_descuento,
                    "ventaNoSuj": round(v_nosujeta, 2),
                    "ventaExenta": round(v_exenta, 2),
                    "ventaGravada": round(v_gravada, 2),
                    "tributos": tributos_value,  # None para DTE-01, ["20"] o [] para DTE-03
                    "psv": 0.00,
                    "noGravado": 0.00
                }
                
                # DTE-01 (V1): ivaItem obligatorio en cada item
                # DTE-03 (V3): NO incluir ivaItem (Catálogo 2025 - IVA solo en resumen)
                if tipo_dte == '01':
                    item["ivaItem"] = round(v_gravada - (v_gravada / 1.13), 2) if es_gravado else 0.00
                # DTE-03 V3: no agregar ivaItem
                items.append(item)
        else:
            # Fallback: crear items desde totales (compatibilidad con ventas antiguas)
            venta_gravada = float(self.venta.venta_gravada or 0)
            venta_exenta = float(self.venta.venta_exenta or 0)
            venta_no_sujeta = float(self.venta.venta_no_sujeta or 0)
            debito_fiscal = float(self.venta.debito_fiscal or 0)
            
            num_item = 1
            if venta_gravada > 0:
                # Venta gravada tiene IVA
                tiene_iva_gravada = debito_fiscal > 0
                
                # DTE-01: tributos puede ser null/vacío; DTE-03: tributos ["20"] si es gravado
                if tipo_dte == '01':
                    tributos_value = None
                else:
                    tributos_value = ["20"] if tiene_iva_gravada else []
                
                # DTE-01: ivaItem calculado inverso; DTE-03: ivaItem = monto_gravado * 0.13
                venta_gravada_float = float(formatear_decimal(venta_gravada))
                if tipo_dte == '01':
                    # DTE-01: El precio incluye IVA
                    iva_item_fallback = round(venta_gravada_float - (venta_gravada_float / 1.13), 2)
                else:
                    # DTE-03: IVA explícito sobre el monto gravado (obligatorio en v1)
                    iva_item_fallback = round(venta_gravada_float * 0.13, 2)
                
                fallback_item = {
                    "numItem": num_item,
                    "tipoItem": 1,
                    "cantidad": 1.0,
                    "codigo": "PROD001",
                    "codTributo": None,
                    "uniMedida": 59,
                    "descripcion": "Venta gravada",
                    "precioUni": venta_gravada_float,
                    "montoDescu": 0.00,
                    "ventaNoSuj": 0.00,
                    "ventaExenta": 0.00,
                    "ventaGravada": venta_gravada_float,
                    "psv": 0.00,
                    "noGravado": 0.00,
                    "numeroDocumento": None,
                    "tributos": tributos_value
                }
                if tipo_dte == '01':
                    fallback_item["ivaItem"] = iva_item_fallback
                items.append(fallback_item)
                num_item += 1
            
            if venta_exenta > 0:
                # Venta exenta NO tiene IVA
                # DTE-01: tributos puede ser null/vacío; DTE-03: exento no lleva tributos
                tributos_value = None if tipo_dte == '01' else []
                
                exento_item = {
                    "numItem": num_item,
                    "tipoItem": 1,
                    "cantidad": 1.0,
                    "codigo": "PROD002",
                    "codTributo": None,
                    "uniMedida": 59,
                    "descripcion": "Venta exenta",
                    "precioUni": float(formatear_decimal(venta_exenta)),
                    "montoDescu": 0.00,
                    "ventaNoSuj": 0.00,
                    "ventaExenta": float(formatear_decimal(venta_exenta)),
                    "ventaGravada": 0.00,
                    "psv": 0.00,
                    "noGravado": 0.00,
                    "numeroDocumento": None,
                    "tributos": tributos_value
                }
                if tipo_dte == '01':
                    exento_item["ivaItem"] = 0.00
                items.append(exento_item)
                num_item += 1
            
            if venta_no_sujeta > 0:
                # Venta no sujeta NO tiene IVA
                # DTE-01: tributos puede ser null/vacío; DTE-03: no sujeta no lleva tributos
                tributos_value = None if tipo_dte == '01' else []
                
                nosuj_item = {
                    "numItem": num_item,
                    "tipoItem": 1,
                    "cantidad": 1.0,
                    "codigo": "PROD003",
                    "codTributo": None,
                    "uniMedida": 59,
                    "descripcion": "Venta no sujeta",
                    "precioUni": float(formatear_decimal(venta_no_sujeta)),
                    "montoDescu": 0.00,
                    "ventaNoSuj": float(formatear_decimal(venta_no_sujeta)),
                    "ventaExenta": 0.00,
                    "ventaGravada": 0.00,
                    "psv": 0.00,
                    "noGravado": 0.00,
                    "numeroDocumento": None,
                    "tributos": tributos_value
                }
                if tipo_dte == '01':
                    nosuj_item["ivaItem"] = 0.00
                items.append(nosuj_item)
        
        # Si no hay items, crear uno por defecto
        if not items:
            venta_gravada_default = formatear_decimal(self.venta.venta_gravada or 0)
            debito_fiscal_default = formatear_decimal(self.venta.debito_fiscal or 0)
            # Verificar si tiene IVA
            tiene_iva_default = debito_fiscal_default > 0
            
            # DTE-01: tributos puede ser null/vacío; DTE-03: tributos ["20"] si es gravado
            if tipo_dte == '01':
                tributos_value = None
            else:
                tributos_value = ["20"] if tiene_iva_default else []
            
            # DTE-01: ivaItem calculado inverso; DTE-03: ivaItem = monto_gravado * 0.13
            venta_gravada_default_float = float(venta_gravada_default)
            if tipo_dte == '01':
                # DTE-01: El precio incluye IVA
                iva_item_default = round(venta_gravada_default_float - (venta_gravada_default_float / 1.13), 2)
            else:
                # DTE-03: IVA explícito sobre el monto gravado (obligatorio en v1)
                iva_item_default = round(venta_gravada_default_float * 0.13, 2)
            
            default_item = {
                "numItem": 1,
                "tipoItem": 1,
                "cantidad": 1.0,
                "codigo": "PROD001",
                "codTributo": None,
                "uniMedida": 59,
                "descripcion": "Venta",
                "precioUni": venta_gravada_default_float,
                "montoDescu": 0.00,
                "ventaNoSuj": 0.00,
                "ventaExenta": 0.00,
                "ventaGravada": venta_gravada_default_float,
                "psv": 0.00,
                "noGravado": 0.00,
                "numeroDocumento": None,
                "tributos": tributos_value
            }
            if tipo_dte == '01':
                default_item["ivaItem"] = iva_item_default
            items.append(default_item)
        
        return items
    
    def _generar_resumen(self, cuerpo_documento=None):
        """
        Genera la sección de resumen del DTE.
        
        LÓGICA CONDICIONAL:
        - DTE-01 (Factura): tributos debe ser None (IVA incluido, no se desglosa)
        - DTE-03 (Crédito Fiscal): tributos debe desglosar el IVA con código "20"
        
        Args:
            cuerpo_documento: Lista de items del cuerpo documento (opcional).
                            Si se proporciona, recalcula totales desde los items.
        """
        tipo_dte = self._obtener_tipo_dte()
        
        # CRÍTICO: Si se proporciona cuerpo_documento, recalcular totales desde los items
        if cuerpo_documento:
            # Recalcular totales sumando valores de los items recalculados
            total_gravado = float(sum(item.get("ventaGravada", 0) for item in cuerpo_documento))
            total_exento = float(sum(item.get("ventaExenta", 0) for item in cuerpo_documento))
            total_no_sujeto = float(sum(item.get("ventaNoSuj", 0) for item in cuerpo_documento))
            total_descu = float(sum(item.get("montoDescu", 0) for item in cuerpo_documento))
            
            # DTE-01 V1: total_iva = suma de ivaItem (cada item tiene ivaItem)
            # DTE-03 V3: total_iva = total_gravado * 0.13 (items no tienen ivaItem)
            if tipo_dte == '03':
                total_iva = round(total_gravado * 0.13, 2)
            else:
                total_iva = float(sum(item.get("ivaItem", 0) for item in cuerpo_documento))
        else:
            # Fallback: usar valores de la base de datos
            total_gravado = float(formatear_decimal(self.venta.venta_gravada or 0))
            total_exento = float(formatear_decimal(self.venta.venta_exenta or 0))
            total_no_sujeto = float(formatear_decimal(self.venta.venta_no_sujeta or 0))
            total_descu = 0.00
            
            # V1: Calcular IVA según tipo de DTE (fallback)
            if tipo_dte == '03':
                # DTE-03: IVA = totalGravada * 0.13 (IVA explícito)
                total_iva = round(total_gravado * 0.13, 2)
            else:
                # DTE-01: IVA incluido en el precio
                total_iva = round(total_gravado - (total_gravado / 1.13), 2)
        
        # CRÍTICO: Convertir todos los valores Decimal a float antes de hacer operaciones
        # Manejar el caso si son None (usando or 0)
        iva_retenido_1 = float(self.venta.iva_retenido_1 or 0) if self.venta.iva_retenido_1 is not None else 0.0
        iva_retenido_2 = float(self.venta.iva_retenido_2 or 0) if self.venta.iva_retenido_2 is not None else 0.0
        rete_renta = float(self.venta.rete_renta or 0) if hasattr(self.venta, 'rete_renta') and self.venta.rete_renta is not None else 0.0
        
        # Calcular subtotal de ventas (suma de todas las categorías)
        subtotal_ventas = round(total_gravado + total_exento + total_no_sujeto, 2)
        
        # V1: Calcular montoTotalOperacion
        if tipo_dte == '01':
            # DTE-01: IVA incluido en el subtotal
            monto_total_operacion = round(subtotal_ventas, 2)
        else:
            # DTE-03: montoTotalOperacion = subTotal + totalIva (obligatorio en v1)
            sub_total = round(subtotal_ventas - total_descu, 2)
            monto_total_operacion = round(sub_total + total_iva, 2)
        
        # CCF v3: ivaPerci1 = IVA Percibido (0 si no hay gran contribuyente mismo giro)
        # Simplificado: ivaPerci1 = 0 (clientes no serán gran contribuyente)
        if tipo_dte == '03':
            iva_perci_1 = 0.0
            total_pagar = round(monto_total_operacion - iva_retenido_1 - iva_retenido_2 + 0.0, 2)
        else:
            iva_perci_1 = 0.0
            total_pagar = round(monto_total_operacion - iva_retenido_1 - iva_retenido_2, 2)
        
        # Convertir total a letras (función auxiliar)
        total_letras = self._numero_a_letras(total_pagar)
        
        # Calcular totalNoGravado (generalmente 0.00)
        total_no_gravado = 0.00
        
        # Calcular saldoFavor (generalmente 0.00, puede ser negativo si hay retenciones)
        saldo_favor = 0.00
        
        # CRÍTICO: totalPagar debe igualar suma de pagos (validación MH)
        # Esquema MH exige referencia, periodo, plazo (pueden ser null)
        # Código "01" = Efectivo
        monto_pago = round(total_pagar, 2)
        pagos = [
            {
                "codigo": "01",
                "montoPago": monto_pago,
                "referencia": None,
                "periodo": None,
                "plazo": None,
            }
        ]
        
        # DTE-03: desglosa IVA en tributos; DTE-01: tributos vacío/null
        if tipo_dte == '03':
            tributos_value = [
                {
                    "codigo": "20",
                    "descripcion": "Impuesto al Valor Agregado 13%",
                    "valor": round(total_iva, 2)
                }
            ] if total_iva > 0 else []
        else:
            tributos_value = None
        
        resumen = {
            "totalNoSuj": round(total_no_sujeto, 2),
            "totalExenta": round(total_exento, 2),
            "totalGravada": round(total_gravado, 2),
            "subTotalVentas": round(subtotal_ventas, 2),
            "descuNoSuj": 0.00,
            "descuExenta": 0.00,
            "descuGravada": round(total_descu, 2),
            "porcentajeDescuento": 0.00,
            "totalDescu": round(total_descu, 2),
            "tributos": tributos_value,  # None para DTE-01, lista para DTE-03
            "subTotal": round(subtotal_ventas - total_descu, 2),
            "reteRenta": round(rete_renta, 2),
            "ivaPerci1": round(iva_perci_1, 2),
            "reteIVA": round(iva_retenido_1, 2),  # Se eliminará si es 0.00 en limpiar_diccionario
            # Campos obligatorios agregados:
            "ivaRete1": round(iva_retenido_1, 2),  # Retención IVA 1%
            "montoTotalOperacion": round(monto_total_operacion, 2),  # Total de la operación
            "totalNoGravado": round(total_no_gravado, 2),  # Total no gravado
            "totalIva": round(total_iva, 2),
            "saldoFavor": round(saldo_favor, 2),  # Saldo a favor
            "totalPagar": round(total_pagar, 2),
            "totalLetras": total_letras,
            "condicionOperacion": 1,
            "pagos": pagos,
            "numPagoElectronico": None,  # Requerido por esquema (null si no aplica)
        }

        # Reglas por tipo DTE (fe-fc-v1 vs fe-ccf-v3):
        if tipo_dte == '03':
            # CCF v3: totalIva NO permitido; usar ivaPerci1
            resumen.pop("totalIva", None)
        else:
            # FC v1: ivaPerci1 no debe viajar; totalIva sí
            resumen.pop("ivaPerci1", None)

        return resumen
    
    def _generar_extension(self):
        """
        Genera la sección de extensión. Esquema MH exige todos los campos (pueden ser null).
        """
        ext = self._generar_extension_default()
        docu_entrega = getattr(self.venta, 'docu_entrega', None)
        docu_recibe = getattr(self.venta, 'docu_recibe', None)
        placa_vehiculo = getattr(self.venta, 'placa_vehiculo', None)
        observaciones = getattr(self.venta, 'observaciones', None)
        nomb_entrega = getattr(self.venta, 'nomb_entrega', None)
        nomb_recibe = getattr(self.venta, 'nomb_recibe', None)
        if docu_entrega:
            ext["docuEntrega"] = docu_entrega
        if docu_recibe:
            ext["docuRecibe"] = docu_recibe
        if placa_vehiculo:
            ext["placaVehiculo"] = placa_vehiculo
        if observaciones:
            ext["observaciones"] = observaciones
        if nomb_entrega:
            ext["nombEntrega"] = nomb_entrega
        if nomb_recibe:
            ext["nombRecibe"] = nomb_recibe
        return ext
    
    def _generar_extension_default(self):
        """Extension con campos requeridos por MH (null cuando no hay datos)."""
        return {
            "nombEntrega": None,
            "docuEntrega": None,
            "nombRecibe": None,
            "docuRecibe": None,
            "observaciones": None,
            "placaVehiculo": None,
        }
    
    def _numero_a_letras(self, numero):
        """
        Convierte un número a letras en español usando num2words.
        Formato: "CIENTO TRECE DOLARES CON 00/100 USD" (MAYÚSCULAS)
        """
        try:
            # Intentar usar num2words si está disponible
            try:
                from num2words import num2words
                
                numero_entero = int(numero)
                numero_decimal = int(round((numero - numero_entero) * 100))
                
                # Convertir parte entera a palabras en español
                if numero_entero == 0:
                    texto_entero = "CERO"
                else:
                    texto_entero = num2words(numero_entero, lang='es', to='cardinal').upper()
                    # Reemplazar "uno" por "un" cuando es necesario (opcional, según preferencia)
                    # texto_entero = texto_entero.replace("UNO", "UN")
                
                # Formatear decimales
                decimal_str = f"{numero_decimal:02d}"
                
                # Construir el texto completo en MAYÚSCULAS
                if numero_decimal > 0:
                    resultado = f"{texto_entero} DOLARES CON {decimal_str}/100 USD"
                else:
                    resultado = f"{texto_entero} DOLARES CON 00/100 USD"
                
                return resultado
                
            except ImportError:
                # Fallback: implementación básica mejorada si num2words no está disponible
                # NOTA: Esta implementación es limitada. Se recomienda instalar num2words.
                numero_entero = int(numero)
                numero_decimal = int(round((numero - numero_entero) * 100))
                
                def convertir_0_99(n):
                    """Convierte números de 0 a 99 a palabras"""
                    if n == 0:
                        return "CERO"
                    unidades = ['', 'UNO', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE']
                    decenas = ['', 'DIEZ', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
                    especiales = {
                        11: 'ONCE', 12: 'DOCE', 13: 'TRECE', 14: 'CATORCE', 15: 'QUINCE',
                        16: 'DIECISÉIS', 17: 'DIECISIETE', 18: 'DIECIOCHO', 19: 'DIECINUEVE',
                        20: 'VEINTE', 21: 'VEINTIUNO', 22: 'VEINTIDÓS', 23: 'VEINTITRÉS',
                        24: 'VEINTICUATRO', 25: 'VEINTICINCO', 26: 'VEINTISÉIS', 27: 'VEINTISIETE',
                        28: 'VEINTIOCHO', 29: 'VEINTINUEVE'
                    }
                    
                    if n in especiales:
                        return especiales[n]
                    elif n < 10:
                        return unidades[n]
                    else:
                        decena = n // 10
                        unidad = n % 10
                        if unidad == 0:
                            return decenas[decena]
                        else:
                            return f"{decenas[decena]} Y {unidades[unidad]}"
                
                # Implementación básica para números hasta 999,999
                if numero_entero == 0:
                    texto = "CERO"
                elif numero_entero < 100:
                    texto = convertir_0_99(numero_entero)
                elif numero_entero < 1000:
                    # Cientos
                    centenas = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 
                               'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS']
                    resto = numero_entero % 100
                    centena = numero_entero // 100
                    
                    if centena == 1 and resto == 0:
                        texto = "CIEN"
                    else:
                        texto_centena = centenas[centena]
                        if resto > 0:
                            resto_texto = convertir_0_99(resto)
                            texto = f"{texto_centena} {resto_texto}"
                        else:
                            texto = texto_centena
                elif numero_entero < 1000000:
                    # Miles
                    miles = numero_entero // 1000
                    resto = numero_entero % 1000
                    
                    if miles == 1:
                        texto_miles = "MIL"
                    else:
                        texto_miles_num = convertir_0_99(miles) if miles < 100 else f"{miles}"
                        texto_miles = f"{texto_miles_num} MIL"
                    
                    if resto > 0:
                        texto_resto = convertir_0_99(resto) if resto < 100 else f"{resto}"
                        texto = f"{texto_miles} {texto_resto}"
                    else:
                        texto = texto_miles
                else:
                    # Para números muy grandes, usar formato numérico (fallback)
                    texto = f"{numero_entero}"
                
                decimal_str = f"{numero_decimal:02d}"
                resultado = f"{texto} DOLARES CON {decimal_str}/100 USD"
                
                return resultado
                
        except Exception as e:
            # En caso de error, retornar formato básico
            try:
                numero_entero = int(numero)
                numero_decimal = int(round((numero - numero_entero) * 100))
                decimal_str = f"{numero_decimal:02d}"
                return f"{numero_entero} DOLARES CON {decimal_str}/100 USD"
            except:
                return "CERO DOLARES CON 00/100 USD"

