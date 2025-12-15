from django.db import models

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

    def __str__(self):
        return self.nombre


# 2. MODELO CLIENTE (Directorio General / Excel Masivo)
# Aquí cargaremos a los 50,000 contribuyentes. Debe ser ligero.
class Cliente(models.Model):
    # Nota: Mantenemos el NRC como llave primaria si así lo tenías, 
    # es excelente para evitar duplicados en la carga masiva.
    nrc = models.CharField(max_length=20, unique=True, primary_key=True) 
    
    nombre = models.CharField(max_length=200)
    nit = models.CharField(max_length=30, blank=True, null=True)
    dui = models.CharField(max_length=20, blank=True, null=True)
    
    # Solo necesitamos su correo para ENVIARLE la factura, no su clave.
    email_contacto = models.EmailField(blank=True, null=True) 
    
    direccion = models.TextField(null=True, blank=True)
    giro = models.CharField(max_length=200, blank=True, null=True) # Útil para el Excel

    def __str__(self):
        return f"{self.nombre} ({self.nrc})"

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
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='compras_hechas')
    
    # Datos Generales
    fecha_emision = models.DateField()
    fecha_registro = models.DateTimeField(auto_now_add=True)
    periodo_aplicado = models.CharField(max_length=7) # Ej: "2025-10"
    
    # Clasificación (Consumidor Final o Contribuyente)
    tipo_venta = models.CharField(max_length=10, choices=[('CF', 'Consumidor Final'), ('CCF', 'Contribuyente')])
    
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

    def __str__(self):
        return f"{self.fecha_emision} - {self.tipo_venta} - ${self.venta_gravada}"
# --- TABLA 4: RETENCIONES RECIBIDAS (Saldo a Favor) ---
class Retencion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="retenciones")
    
    # Datos del Documento
    fecha_emision = models.DateField()
    periodo_aplicado = models.CharField(max_length=7) # 2025-10
    
    # Tipo: 07 (Cliente) o 14/Liq (Tarjeta)
    TIPO_RET_CHOICES = [('1', 'Retención IVA 1% (Cliente)'), ('2', 'Retención Tarjeta (Banco)')]
    tipo_retencion = models.CharField(max_length=2, choices=TIPO_RET_CHOICES, default='1')
    
    # Identificación
    codigo_generacion = models.CharField(max_length=100) # El código largo del JSON
    sello_recepcion = models.CharField(max_length=100, blank=True, null=True)
    
    # Quién te retuvo
    nombre_emisor = models.CharField(max_length=200) # El Banco o el Cliente Grande
    nrc_emisor = models.CharField(max_length=20, blank=True, null=True)
    
    # El dinero importante
    monto_sujeto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00) # La venta base
    monto_retenido = models.DecimalField(max_digits=12, decimal_places=2, default=0.00) # El dinero a favor

   # TIPO DE RETENCIÓN (MH usa códigos de Anexo: 6 o 7)
    # 161 = Tarjeta (Anexo 6), 162 = Cliente (Anexo 7)
    TIPO_RET_CHOICES = [('161', 'Retención Tarjeta (Anexo 6)'), ('162', 'Retención IVA 1% (Anexo 7)')]
    tipo_retencion = models.CharField(max_length=3, choices=TIPO_RET_CHOICES, default='162')
    
    # IDENTIFICACIÓN DEL DOCUMENTO
    codigo_generacion = models.CharField(max_length=100, blank=True, null=True) # DTE
    numero_serie = models.CharField(max_length=100, blank=True, null=True) # Serie Física
    numero_documento = models.CharField(max_length=100, blank=True, null=True) # Correlativo Físico
    
    # QUIÉN RETUVO (EL DATO CLAVE)
    nombre_emisor = models.CharField(max_length=200)
    nit_emisor = models.CharField(max_length=20) # <--- ¡NUEVO Y OBLIGATORIO!
    
    # MONTOS
    monto_sujeto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monto_retenido = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Retención {self.tipo_retencion} - ${self.monto_retenido}"
