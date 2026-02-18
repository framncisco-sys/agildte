from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

from .utils.fields import EncryptedCharField, EncryptedTextField

# 1. MODELO EMPRESA (Tus 12 Clientes VIP)
# Aquí va la configuración pesada: Logos, Correo para leer facturas, Sellos.
class Empresa(models.Model):
    nombre = models.CharField(max_length=200)
    nrc = models.CharField(max_length=20, unique=True)
    nit = models.CharField(max_length=30, blank=True, null=True)
    direccion = models.TextField(null=True, blank=True)
    es_importador = models.BooleanField(default=False)
    
    # --- MÓDULO DE LECTURA DE CORREOS (Solo para tus VIPs) ---
    email_lectura = models.EmailField(blank=True, null=True, help_text="Correo donde llegan los DTEs de proveedores")
    clave_correo = models.CharField(max_length=100, blank=True, null=True, help_text="Contraseña de aplicación para leer el correo")
    hora_sync = models.TimeField(default="03:00:00", help_text="Hora automática de lectura")
    
    # Logo para sus facturas
    logo = models.ImageField(upload_to='logos/', null=True, blank=True)
    
    # --- CREDENCIALES MINISTERIO DE HACIENDA (MH) ---
    # IMPORTANTE: Hacienda requiere códigos numéricos según estándar:
    # '00' = Producción (api.dtes.mh.gob.sv)
    # '01' = Pruebas (apitest.dtes.mh.gob.sv)
    AMBIENTE_CHOICES = [
        ('00', 'PRODUCCION'),
        ('01', 'PRUEBAS'),
    ]
    ambiente = models.CharField(
        max_length=2,
        choices=AMBIENTE_CHOICES,
        default='01',  # Default a Pruebas para seguridad
        help_text="Ambiente del sistema de facturación electrónica: '00' = Producción, '01' = Pruebas"
    )
    
    user_api_mh = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Usuario NIT/DUI para autenticación en el portal MH (sin guiones)"
    )
    
    clave_api_mh = EncryptedCharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Contraseña de la API del Ministerio de Hacienda (cifrada en BD)"
    )
    
    archivo_certificado = models.FileField(
        upload_to='certificados/',
        null=True,
        blank=True,
        help_text="Archivo de certificado digital (.crt) para firma de documentos"
    )
    
    clave_certificado = EncryptedCharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Contraseña del archivo de certificado digital (cifrada en BD)"
    )
    
    cod_actividad = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Código de actividad económica según MH (ej: 70201, 47520)"
    )
    
    desc_actividad = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Descripción de la actividad económica"
    )
    
    # --- CAMPOS PARA SECCIÓN EMISOR DEL DTE ---
    cod_establecimiento = models.CharField(
        max_length=4,
        default='M001',
        help_text="Código de establecimiento (Ej: M001)"
    )
    
    cod_punto_venta = models.CharField(
        max_length=4,
        default='P001',
        help_text="Código de punto de venta (Ej: P001)"
    )
    
    departamento = models.CharField(
        max_length=2,
        default='06',
        help_text="Código de departamento de 2 dígitos (Ej: 06 para San Salvador)"
    )
    
    municipio = models.CharField(
        max_length=2,
        default='14',
        help_text="Código de municipio de 2 dígitos (Ej: 14 para San Salvador)"
    )
    
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Teléfono de contacto de la empresa"
    )
    
    correo = models.EmailField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Correo electrónico de contacto de la empresa"
    )

    # --- CONFIGURACIÓN SMTP PARA ENVÍO DE FACTURAS ---
    smtp_host = models.CharField(max_length=255, blank=True, null=True, help_text="Host SMTP (ej: smtp.gmail.com)")
    smtp_port = models.IntegerField(default=587, help_text="Puerto SMTP (587 TLS, 465 SSL)")
    smtp_user = models.CharField(max_length=255, blank=True, null=True, help_text="Usuario SMTP")
    smtp_password = EncryptedCharField(max_length=500, blank=True, null=True, help_text="Contraseña SMTP (cifrada)")
    smtp_use_tls = models.BooleanField(default=True, help_text="Usar TLS para conexión SMTP")
    email_asunto_default = models.CharField(
        max_length=255,
        default="Factura electrónica - {{numero_control}}",
        blank=True,
        help_text="Asunto del correo. Variables: {{numero_control}}, {{cliente}}, {{fecha}}"
    )
    email_template_html = models.TextField(
        blank=True,
        null=True,
        default='<p>Estimado(a) {{cliente}},</p><p>Adjuntamos su factura electrónica {{numero_control}}.</p><p>Saludos cordiales.</p>',
        help_text="Plantilla HTML del cuerpo del correo. Variables: {{cliente}}, {{numero_control}}, {{fecha}}, {{total}}"
    )

    def __str__(self):
        return self.nombre


# 2. MODELO CLIENTE (Directorio General / Excel Masivo)
# Aquí cargaremos a los 50,000 contribuyentes. Debe ser ligero.
# FLEXIBILIZADO: Permite clientes sin NRC (Consumidor Final, Clientes Varios)
class Cliente(models.Model):
    # TIPO DE CLIENTE: Permite distinguir entre Contribuyentes y Consumidores Finales
    TIPO_CLIENTE_CHOICES = [
        ('CONTRIBUYENTE', 'Contribuyente'),
        ('CONSUMIDOR_FINAL', 'Consumidor Final'),
    ]
    tipo_cliente = models.CharField(
        max_length=20,
        choices=TIPO_CLIENTE_CHOICES,
        default='CONTRIBUYENTE',
        help_text="Tipo de cliente: Contribuyente (tiene NRC) o Consumidor Final (sin NRC)"
    )
    
    # NOTA: NRC ya NO es primary_key porque puede ser null para Consumidor Final
    # Se mantiene unique=True para evitar duplicados en contribuyentes
    nrc = models.CharField(max_length=20, unique=True, blank=True, null=True, 
                          help_text="NRC del cliente (obligatorio solo para Contribuyentes)")
    
    nombre = models.CharField(max_length=200)
    
    # Tipo y número de documento (MH: NIT, DUI, Pasaporte)
    TIPO_DOCUMENTO_CHOICES = [
        ('NIT', 'NIT'),
        ('DUI', 'DUI'),
        ('Pasaporte', 'Pasaporte'),
    ]
    tipo_documento = models.CharField(
        max_length=20,
        choices=TIPO_DOCUMENTO_CHOICES,
        default='NIT',
        blank=True,
        null=True,
        help_text="Tipo de documento de identidad según MH"
    )
    documento_identidad = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="NIT, DUI o Pasaporte según tipo_documento"
    )
    
    # Campos opcionales: pueden ser null para clientes genéricos (compatibilidad con DTE generator)
    nit = models.CharField(max_length=30, blank=True, null=True,
                          help_text="NIT del cliente (opcional)")
    dui = models.CharField(max_length=20, blank=True, null=True,
                          help_text="DUI del cliente (opcional, para Consumidor Final)")
    
    # Solo necesitamos su correo para ENVIARLE la factura, no su clave.
    email_contacto = models.EmailField(blank=True, null=True)
    
    telefono = models.CharField(max_length=20, blank=True, null=True,
                                help_text="Teléfono de contacto (opcional)") 
    
    # Dirección opcional: puede ser null para clientes genéricos
    direccion = models.TextField(null=True, blank=True,
                                help_text="Dirección del cliente (opcional)")
    
    # Ubicación geográfica (códigos de 2 dígitos según estándar MH)
    departamento = models.CharField(
        max_length=2,
        default='06',
        help_text='Código de departamento de 2 dígitos (Ej: 06 para San Salvador)'
    )
    municipio = models.CharField(
        max_length=2,
        default='14',
        help_text='Código de municipio de 2 dígitos (Ej: 14 para San Salvador)'
    )
    
    giro = models.CharField(max_length=200, blank=True, null=True,
                           help_text="Giro o actividad económica (útil para el Excel)")
    
    # Campos para DTE-03 (Crédito Fiscal) - Obligatorios según normativa 2025
    cod_actividad = models.CharField(
        max_length=6, 
        blank=True, 
        null=True,
        help_text='Código de Actividad Económica según CAT-019 (Ej: 45201 para Reparación mecánica de automotores)'
    )
    desc_actividad = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text='Descripción de la Actividad Económica (Ej: Reparación mecánica de automotores)'
    )

    # IVA Percibido 1%: cuando es gran contribuyente y mismo giro que emisor
    gran_contribuyente = models.BooleanField(
        default=False,
        help_text='Si es gran contribuyente y mismo giro que emisor, aplica IVA Percibido 1%'
    )

    def save(self, *args, **kwargs):
        # Sincronizar documento_identidad con nit/dui para compatibilidad con DTE generator
        if self.documento_identidad and self.tipo_documento:
            if self.tipo_documento == 'NIT':
                self.nit = self.documento_identidad.strip()
                self.dui = None
            elif self.tipo_documento == 'DUI':
                self.dui = self.documento_identidad.strip()
                self.nit = None
            else:
                self.nit = self.documento_identidad.strip()
                self.dui = None
        super().save(*args, **kwargs)

    def __str__(self):
        # Manejar caso donde nrc puede ser None
        if self.nrc:
            return f"{self.nombre} ({self.nrc})"
        else:
            return f"{self.nombre} (Sin NRC - {self.get_tipo_cliente_display()})"


# --- CATÁLOGO ACTIVIDAD ECONÓMICA (MH / CLAEES - 885 registros) ---
class ActividadEconomica(models.Model):
    """Catálogo de actividades económicas para DTE-03. Carga desde CSV (;)."""
    codigo = models.CharField(max_length=10, primary_key=True)
    descripcion = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Actividad Económica'
        verbose_name_plural = 'Actividades Económicas'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


# --- TABLA 2: LIBRO DE COMPRAS (¡NUEVA!) ---
class Compra(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='compras_realizadas', null=True)
    # Relación: Una compra pertenece a un Cliente
    proveedor = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='compras_recibidas')
    
    # Datos del Documento
    fecha_emision = models.DateField()
    fecha_registro = models.DateTimeField(auto_now_add=True) # Auditoría (cuándo se creó)
    tipo_documento = models.CharField(max_length=2, default="03") # 03, 05, 12, 14
    codigo_generacion = models.CharField(max_length=100, blank=True, null=True) # DTE o Físico
    
    # Datos del Proveedor
    nrc_proveedor = models.CharField(max_length=20)
    nombre_proveedor = models.CharField(max_length=200)
    
    # Montos
    monto_gravado = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monto_iva = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monto_percepcion = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Clasificación (Tus menús en cascada)
    clasificacion_1 = models.CharField(max_length=50, default="Gravada") # Gravada/Exenta
    clasificacion_2 = models.CharField(max_length=50, blank=True) # Costo/Gasto
    clasificacion_3 = models.CharField(max_length=50, blank=True) # Industria/Ventas...
    
    # Estados y Reglas
    periodo_aplicado = models.CharField(max_length=7) # Ej: "2025-10"
    estado = models.CharField(max_length=20, default="Registrado") # Pendiente, Registrado, Posponer

    def __str__(self):
        return f"{self.fecha_emision} - {self.nombre_proveedor} (${self.monto_total})"

# --- TABLA 3: LIBRO DE VENTAS (VERSIÓN FINAL COMPLETA) ---
class Venta(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='ventas_realizadas', null=True)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name='compras_hechas',
        null=True, blank=True,
        help_text="Opcional: Consumidor Final puede ser null; usar nombre_receptor/nrc_receptor"
    )
    
    # Datos Generales
    fecha_emision = models.DateField()
    hora_emision = models.CharField(max_length=10, blank=True, null=True, help_text="Hora real del DTE (HH:MM:SS) según MH")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    periodo_aplicado = models.CharField(max_length=7) # Ej: "2025-10"
    
    # Clasificación (Consumidor Final o Contribuyente)
    tipo_venta = models.CharField(
        max_length=10,
        choices=[
            ('CF', 'Consumidor Final'),
            ('CCF', 'Contribuyente'),
            ('NC', 'Nota de Crédito'),
            ('ND', 'Nota de Débito'),
        ],
        default='CCF',
    )
    
    # Clasificación Documento MH (Campo 3 del Manual)
    CLASE_DOC_CHOICES = [
        ('1', 'Impreso por Imprenta'),
        ('2', 'Formulario Único'),
        ('3', 'Ticket / Máquina Registradora'),
        ('4', 'Documento Electrónico (DTE)'),
    ]
    clase_documento = models.CharField(max_length=2, choices=CLASE_DOC_CHOICES, default='1')

    # --- IDENTIFICACIÓN DEL DOCUMENTO ---
    # Campo general para el número principal (sea físico o electrónico)
    numero_documento = models.CharField(max_length=100, blank=True, null=True)
    
    # Campos específicos para DTE (Electrónicos)
    codigo_generacion = models.CharField(max_length=100, blank=True, null=True) # El código largo (UUID)
    numero_control = models.CharField(max_length=100, blank=True, null=True)    # El consecutivo (DTE-01...)
    sello_recepcion = models.CharField(max_length=100, blank=True, null=True)   # El sello de Hacienda
    
    # Campos específicos para Físicos (Papel)
    serie_documento = models.CharField(max_length=100, blank=True, null=True)
    numero_resolucion = models.CharField(max_length=100, blank=True, null=True)
    numero_formulario_unico = models.CharField(max_length=100, blank=True, null=True) # Solo para Clase 2
    
    # Campos para Resumen Consumidor Final (Rangos)
    numero_control_desde = models.CharField(max_length=50, blank=True, null=True)
    numero_control_hasta = models.CharField(max_length=50, blank=True, null=True)
    
    # Datos del Receptor (Cliente que compra)
    nombre_receptor = models.CharField(max_length=200, blank=True, null=True)
    nrc_receptor = models.CharField(max_length=20, blank=True, null=True)
    documento_receptor = models.CharField(max_length=50, blank=True, null=True)  # DUI/NIT para CF manual
    tipo_doc_receptor = models.CharField(max_length=10, blank=True, null=True)  # 'NIT' o 'DUI'
    direccion_receptor = models.CharField(max_length=500, blank=True, null=True)
    correo_receptor = models.CharField(max_length=200, blank=True, null=True)
    
    # Montos
    venta_gravada = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    venta_exenta = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    venta_no_sujeta = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    debito_fiscal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Retenciones (Lo que nos quitaron)
    iva_retenido_1 = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    iva_retenido_2 = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # Clasificación MH (Anexos)
    # 1=Gravada, 2=Exenta, 3=No Sujeta, etc.
    clasificacion_venta = models.CharField(max_length=20, default="1") 
    # 1=Profesiones, 3=Comercial, etc.
    tipo_ingreso = models.CharField(max_length=20, default="3") 

    # Estado del DTE
    ESTADO_DTE_CHOICES = [
        ('Borrador', 'Borrador'),
        ('Generado', 'Generado'),
        ('Enviado', 'Enviado'),
        ('AceptadoMH', 'Aceptado por MH'),
        ('RechazadoMH', 'Rechazado por MH'),
        ('ErrorEnvio', 'Error de envío (reintentar)'),
        ('PendienteEnvio', 'Pendiente de envío (MH no disponible)'),
        ('Anulado', 'Anulado'),
    ]
    estado_dte = models.CharField(max_length=20, choices=ESTADO_DTE_CHOICES, default='Borrador')
    error_envio_mensaje = models.CharField(
        max_length=500, blank=True, null=True,
        help_text="Último error al enviar a MH (timeout, red, servidor caído)"
    )
    
    # Observaciones/errores de MH cuando el documento es rechazado (JSON o texto)
    observaciones_mh = models.TextField(blank=True, null=True, help_text="Errores/observaciones de MH al rechazar")
    
    # Método para calcular totales desde detalles
    def calcular_totales(self):
        """Calcula los totales sumando los detalles de la venta"""
        from decimal import Decimal
        detalles = self.detalles.all()
        
        # Sumar con Decimal para evitar errores de None
        self.venta_gravada = sum(
            Decimal(str(d.venta_gravada)) if d.venta_gravada else Decimal('0.00') 
            for d in detalles
        )
        self.venta_exenta = sum(
            Decimal(str(d.venta_exenta)) if d.venta_exenta else Decimal('0.00') 
            for d in detalles
        )
        self.venta_no_sujeta = sum(
            Decimal(str(d.venta_no_sujeta)) if d.venta_no_sujeta else Decimal('0.00') 
            for d in detalles
        )
        self.debito_fiscal = sum(
            Decimal(str(d.iva_item)) if d.iva_item else Decimal('0.00') 
            for d in detalles
        )
        
        # Redondear a 2 decimales
        from decimal import ROUND_HALF_UP
        self.venta_gravada = self.venta_gravada.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.venta_exenta = self.venta_exenta.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.venta_no_sujeta = self.venta_no_sujeta.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.debito_fiscal = self.debito_fiscal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return self
    
    def save(self, *args, **kwargs):
        # Solo calcular totales si la venta ya tiene un ID (ya está guardada)
        # Esto evita el error "instance needs to have a primary key value"
        if self.pk is not None:
            if hasattr(self, 'detalles') and self.detalles.exists():
                self.calcular_totales()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fecha_emision} - {self.tipo_venta} - ${self.venta_gravada}"

# --- TABLA 3.1: PRODUCTOS / ÍTEMS (catálogo por empresa) ---
class Producto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='productos', null=True)
    codigo = models.CharField(max_length=50, blank=True, default='')
    descripcion = models.CharField(max_length=200)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    TIPO_ITEM_CHOICES = [(1, 'Bien'), (2, 'Servicio')]
    tipo_item = models.IntegerField(choices=TIPO_ITEM_CHOICES, default=1)
    TIPO_IMPUESTO_CHOICES = [
        ('20', 'Gravado 13% (IVA)'),
        ('exento', 'Exento'),
    ]
    tipo_impuesto = models.CharField(
        max_length=10, choices=TIPO_IMPUESTO_CHOICES, default='20'
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'codigo'],
                condition=models.Q(codigo__isnull=False) & ~models.Q(codigo=''),
                name='producto_empresa_codigo_uniq',
            )
        ]

    def __str__(self):
        return f"{self.codigo or 'N/A'} - {self.descripcion}"

# --- TABLA 3.2: DETALLE DE VENTA ---
class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True)
    
    # Si no hay producto, permitir item libre
    descripcion_libre = models.CharField(max_length=200, blank=True, null=True)
    codigo_libre = models.CharField(max_length=50, blank=True, null=True)
    
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monto_descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Clasificación del item
    venta_no_sujeta = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    venta_exenta = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    venta_gravada = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    iva_item = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    numero_item = models.IntegerField(default=1)
    
    def calcular_subtotal(self):
        """Calcula el subtotal del item"""
        subtotal = (self.cantidad * self.precio_unitario) - self.monto_descuento
        return subtotal
    
    def calcular_iva(self):
        """Calcula el IVA del item (13% sobre venta gravada)"""
        if self.venta_gravada > 0:
            return self.venta_gravada * Decimal('0.13')
        return Decimal('0.00')
    
    def save(self, *args, **kwargs):
        # Si no hay producto, usar descripción libre
        if not self.producto:
            if not self.descripcion_libre:
                self.descripcion_libre = "Item sin producto"
            if not self.codigo_libre:
                self.codigo_libre = "LIBRE"
        
        # Calcular IVA si hay venta gravada
        if self.venta_gravada > 0 and self.iva_item == 0:
            self.iva_item = self.calcular_iva()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        desc = self.producto.descripcion if self.producto else self.descripcion_libre
        return f"{self.venta.id} - {desc} x{self.cantidad}"

# --- TABLA 4: RETENCIONES RECIBIDAS (Saldo a Favor) - MODELO LEGACY ---
class Retencion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="retenciones")
    fecha_emision = models.DateField()
    periodo_aplicado = models.CharField(max_length=7)
    TIPO_RET_CHOICES = [('161', 'Retención Tarjeta (Anexo 6)'), ('162', 'Retención IVA 1% (Anexo 7)')]
    tipo_retencion = models.CharField(max_length=3, choices=TIPO_RET_CHOICES, default='162')
    codigo_generacion = models.CharField(max_length=100, blank=True, null=True)
    numero_serie = models.CharField(max_length=100, blank=True, null=True)
    numero_documento = models.CharField(max_length=100, blank=True, null=True)
    nombre_emisor = models.CharField(max_length=200)
    nit_emisor = models.CharField(max_length=20)
    monto_sujeto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monto_retenido = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Retención {self.tipo_retencion} - ${self.monto_retenido}"

# --- TABLA 5: LIQUIDACIONES (DTE-09 / CSV 161) ---
# Propósito: Informativo/Financiero y generación de anexo 161
class Liquidacion(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='liquidaciones', null=True)
    
    # Datos del Documento
    fecha_documento = models.DateField()
    codigo_generacion = models.CharField(max_length=100, unique=True)  # UUID único
    sello_recibido = models.CharField(max_length=200, blank=True, null=True)
    
    # Datos del Agente (Quien emite la liquidación)
    nit_agente = models.CharField(max_length=30)
    nombre_agente = models.CharField(max_length=200)
    
    # Montos
    monto_operacion = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    iva_percibido_2 = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Anticipo IVA
    comision = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    liquido_pagar = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True)
    periodo_aplicado = models.CharField(max_length=7)  # Ej: "2025-10"

    def __str__(self):
        return f"Liquidación {self.fecha_documento} - {self.nombre_agente} (${self.liquido_pagar})"

# --- TABLA 6: RETENCIONES RECIBIDAS (DTE-07 / CSV 162) ---
# Propósito: Control de saldo IVA a favor y generación anexo 162
class RetencionRecibida(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='retenciones_recibidas', null=True)
    
    # Datos del Documento
    fecha_documento = models.DateField()
    codigo_generacion = models.CharField(max_length=100, unique=True)  # UUID único
    sello_recibido = models.CharField(max_length=200, blank=True, null=True)
    
    # Datos del Agente (Quien retuvo)
    nit_agente = models.CharField(max_length=30)
    nombre_agente = models.CharField(max_length=200)
    
    # Montos
    monto_sujeto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monto_retenido_1 = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Retención 1%
    
    # Estado y Conciliación
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Aplicada', 'Aplicada'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    
    # Relación ManyToMany con Venta para saber qué facturas mató esta retención
    ventas_aplicadas = models.ManyToManyField(Venta, related_name='retenciones_aplicadas', blank=True)
    
    # Auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True)
    periodo_aplicado = models.CharField(max_length=7)  # Ej: "2025-10"

    def __str__(self):
        return f"Retención {self.fecha_documento} - {self.nombre_agente} (${self.monto_retenido_1}) - {self.estado}"

# --- TABLA 7: PERFIL DE USUARIO (Sistema Multi-Empresa) ---
# Propósito: Vincular usuarios de Django con empresas y asignar roles
class PerfilUsuario(models.Model):
    """
    Perfil extendido del usuario de Django que vincula usuarios con empresas
    y asigna roles dentro del sistema SaaS multi-empresa.
    """
    # Relación OneToOne con el modelo User de Django
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil',
        help_text="Usuario de Django asociado a este perfil"
    )
    
    # Relación ForeignKey con Empresa (un usuario pertenece a una empresa)
    # Nota: Para usuarios MASTER, empresa puede ser None (gestionan todas las empresas)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='usuarios',
        null=True,
        blank=True,
        help_text="Empresa a la que pertenece este usuario (None para usuarios MASTER)"
    )
    
    # Roles del sistema
    ROL_CHOICES = [
        ('MASTER', 'Master (Super Administrador)'),
        ('ADMINISTRADOR', 'Administrador de Empresa'),
        ('VENDEDOR', 'Vendedor/Contador'),
    ]
    rol = models.CharField(
        max_length=20,
        choices=ROL_CHOICES,
        default='VENDEDOR',
        help_text="Rol del usuario en el sistema"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el perfil está activo"
    )
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
        ordering = ['rol', 'empresa', 'user__username']
        # Un usuario solo puede tener un perfil activo
        # Nota: OneToOne garantiza un perfil por usuario, pero un MASTER puede tener empresa=None
    
    def __str__(self):
        empresa_nombre = self.empresa.nombre if self.empresa else "Todas las empresas"
        return f"{self.user.username} - {empresa_nombre} ({self.get_rol_display()})"
    
    def es_master(self):
        """Retorna True si el usuario es Master"""
        return self.rol == 'MASTER'
    
    def es_administrador(self):
        """Retorna True si el usuario es Administrador"""
        return self.rol == 'ADMINISTRADOR'
    
    def es_vendedor(self):
        """Retorna True si el usuario es Vendedor"""
        return self.rol == 'VENDEDOR'

# --- TABLA 8: CORRELATIVOS DTE (Sistema de Numeración Anual) ---
# Propósito: Controlar la numeración de documentos DTE con reinicio anual automático
class Correlativo(models.Model):
    """
    Modelo para gestionar correlativos de números de control DTE.
    Se reinicia automáticamente a 1 cada año nuevo.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='correlativos',
        help_text="Empresa a la que pertenece este correlativo"
    )
    
    tipo_dte = models.CharField(
        max_length=2,
        help_text="Tipo de DTE: '01' = Factura Consumidor Final, '03' = Crédito Fiscal"
    )
    
    anio = models.IntegerField(
        help_text="Año del correlativo (se reinicia automáticamente cada año)"
    )
    
    ultimo_correlativo = models.IntegerField(
        default=0,
        help_text="Último número correlativo utilizado para este tipo de DTE en este año"
    )
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Correlativo DTE"
        verbose_name_plural = "Correlativos DTE"
        unique_together = ('empresa', 'tipo_dte', 'anio')
        ordering = ['empresa', 'tipo_dte', '-anio']
        indexes = [
            models.Index(fields=['empresa', 'tipo_dte', 'anio']),
        ]
    
    def __str__(self):
        return f"{self.empresa.nombre} - DTE-{self.tipo_dte} - Año {self.anio} - Correlativo: {self.ultimo_correlativo}"


# --- TABLA 9: TAREA FACTURACIÓN (Cola de envíos asíncronos) ---
class TareaFacturacion(models.Model):
    """
    Cola de tareas de facturación para procesamiento asíncrono.
    Permite responder al usuario de inmediato y procesar (firma, MH, correo) en segundo plano.
    """
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Procesando', 'Procesando'),
        ('Completada', 'Completada'),
        ('Error', 'Error'),
    ]

    venta = models.OneToOneField(
        Venta,
        on_delete=models.CASCADE,
        related_name='tarea_facturacion'
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    intentos = models.IntegerField(default=0, help_text="Número de intentos de procesamiento")
    proximo_reintento = models.DateTimeField(null=True, blank=True, help_text="Cuándo reintentar (exponential backoff)")
    error_mensaje = models.TextField(blank=True, null=True)
    creada_at = models.DateTimeField(auto_now_add=True)
    actualizada_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tarea de Facturación"
        verbose_name_plural = "Tareas de Facturación"
        ordering = ['proximo_reintento', 'creada_at']

    def __str__(self):
        return f"Tarea venta #{self.venta_id} - {self.estado}"
