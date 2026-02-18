from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Cliente, Compra, Venta, Empresa, Producto, DetalleVenta, Liquidacion, RetencionRecibida, PerfilUsuario, Correlativo, ActividadEconomica, TareaFacturacion

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_cliente', 'nrc', 'nit', 'dui', 'cod_actividad', 'gran_contribuyente', 'departamento', 'municipio')
    list_filter = ('tipo_cliente', 'departamento', 'municipio')
    search_fields = ('nombre', 'nrc', 'nit', 'dui', 'cod_actividad')
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'tipo_cliente')
        }),
        ('Documentos de Identificación', {
            'fields': ('nrc', 'nit', 'dui'),
            'description': 'NRC es obligatorio solo para Contribuyentes. NIT y DUI son opcionales.'
        }),
        ('Actividad Económica (CAT-019)', {
            'fields': ('cod_actividad', 'desc_actividad', 'giro'),
            'description': 'Código y descripción de actividad económica según CAT-019. Obligatorios para DTE-03 (Crédito Fiscal). Ej: 45201 = Reparación mecánica de automotores.'
        }),
        ('Información de Contacto', {
            'fields': ('email_contacto', 'direccion')
        }),
        ('Ubicación Geográfica', {
            'fields': ('departamento', 'municipio'),
            'description': 'Códigos de 2 dígitos según estándar MH. Default: 06 (San Salvador) y 14 (San Salvador).'
        }),
    )

@admin.register(ActividadEconomica)
class ActividadEconomicaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion')
    search_fields = ('codigo', 'descripcion')
    ordering = ('codigo',)


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('fecha_emision', 'nombre_proveedor', 'monto_total', 'estado')

# --- INLINE PARA DETALLEVENTA EN VENTA ---
class DetalleVentaInline(admin.TabularInline):
    """
    Inline para agregar productos (DetalleVenta) directamente al crear/editar una Venta.
    Permite agregar múltiples productos en la misma pantalla de creación/edición de venta.
    """
    model = DetalleVenta
    extra = 1  # Muestra una línea vacía lista para llenar
    # Usar autocomplete si Producto está registrado con search_fields, sino usar raw_id_fields
    autocomplete_fields = ['producto']  # Autocompletado para buscar productos fácilmente
    # raw_id_fields = ['producto']  # Descomentar si autocomplete no funciona
    
    fields = (
        'numero_item',
        'producto',
        'descripcion_libre',
        'codigo_libre',
        'cantidad',
        'precio_unitario',
        'monto_descuento',
        'venta_no_sujeta',
        'venta_exenta',
        'venta_gravada',
        'iva_item',
    )
    verbose_name = "Producto/Item"
    verbose_name_plural = "Productos/Items de la Venta"
    
    # Permitir ordenar los items (opcional, requiere django-admin-sortable2)
    # ordering = ('numero_item',)
    
    class Media:
        # Opcional: agregar CSS/JS personalizado si es necesario
        pass

# --- VENTA ADMIN CON INLINES ---
@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    """
    Admin para gestionar ventas con capacidad de agregar productos inline.
    """
    list_display = ('numero_control', 'cliente', 'fecha_emision', 'total_pagar', 'estado_dte', 'tipo_venta')
    list_filter = ('estado_dte', 'tipo_venta', 'periodo_aplicado', 'clase_documento', 'empresa')
    search_fields = ('numero_control', 'codigo_generacion', 'numero_documento', 'cliente__nombre', 'cliente__nrc')
    readonly_fields = ('fecha_registro', 'sello_recepcion')
    date_hierarchy = 'fecha_emision'
    
    # Inlines para agregar productos directamente
    inlines = [DetalleVentaInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('empresa', 'cliente', 'fecha_emision', 'periodo_aplicado', 'tipo_venta')
        }),
        ('Identificación del Documento', {
            'fields': (
                'clase_documento',
                'numero_documento',
                'numero_control',
                'codigo_generacion',
                'sello_recepcion',
            ),
            'description': 'Campos para identificar el documento (físico o electrónico)'
        }),
        ('Datos del Receptor', {
            'fields': ('nombre_receptor', 'nrc_receptor'),
            'classes': ('collapse',)
        }),
        ('Montos y Totales', {
            'fields': (
                'venta_gravada',
                'venta_exenta',
                'venta_no_sujeta',
                'debito_fiscal',
                'iva_retenido_1',
                'iva_retenido_2',
            )
        }),
        ('Clasificación MH', {
            'fields': ('clasificacion_venta', 'tipo_ingreso'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('estado_dte',)
        }),
        ('Auditoría', {
            'fields': ('fecha_registro',),
            'classes': ('collapse',)
        }),
    )
    
    def total_pagar(self, obj):
        """
        Calcula y muestra el total a pagar de la venta.
        Total = Venta Gravada + Venta Exenta + Venta No Sujeta + Débito Fiscal - Retenciones
        """
        from decimal import Decimal
        total = (
            Decimal(str(obj.venta_gravada or 0)) +
            Decimal(str(obj.venta_exenta or 0)) +
            Decimal(str(obj.venta_no_sujeta or 0)) +
            Decimal(str(obj.debito_fiscal or 0)) -
            Decimal(str(obj.iva_retenido_1 or 0)) -
            Decimal(str(obj.iva_retenido_2 or 0))
        )
        return f"${total:,.2f}"
    total_pagar.short_description = 'Total a Pagar'
    total_pagar.admin_order_field = 'venta_gravada'
    
    def get_queryset(self, request):
        """Optimizar consultas con select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('empresa', 'cliente').prefetch_related('detalles')
    
    def save_model(self, request, obj, form, change):
        """Sobrescribir save para calcular totales después de guardar"""
        super().save_model(request, obj, form, change)
        # Recalcular totales desde los detalles si existen
        if obj.detalles.exists():
            obj.calcular_totales()
            obj.save()
    
    def save_formset(self, request, form, formset, change):
        """Sobrescribir save_formset para recalcular totales después de guardar detalles"""
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()
        
        # Recalcular totales de la venta después de guardar los detalles
        if form.instance.pk:
            form.instance.calcular_totales()
            form.instance.save()

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nrc', 'nit', 'ambiente', 'cod_actividad')
    list_filter = ('ambiente', 'es_importador')
    search_fields = ('nombre', 'nrc', 'nit', 'cod_actividad')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'nrc', 'nit', 'direccion', 'es_importador')
        }),
        ('Configuración de Facturación', {
            'fields': ('cod_actividad', 'desc_actividad', 'logo')
        }),
        ('Datos del Emisor (DTE)', {
            'fields': (
                'cod_establecimiento',
                'cod_punto_venta',
                'departamento',
                'municipio',
                'telefono',
                'correo'
            ),
            'description': 'Campos requeridos para la sección Emisor del DTE según especificación de Hacienda'
        }),
        ('Credenciales Ministerio de Hacienda', {
            'fields': (
                'ambiente',
                'user_api_mh',
                'clave_api_mh',
                'archivo_certificado',
                'clave_certificado'
            ),
            'description': '⚠️ Campos sensibles: Las contraseñas se almacenan en texto plano. Considerar encriptación en producción.'
        }),
        ('Módulo de Lectura de Correos', {
            'fields': ('email_lectura', 'clave_correo', 'hora_sync'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'precio_unitario', 'tipo_item', 'activo')
    list_filter = ('empresa', 'tipo_item', 'activo')
    search_fields = ('codigo', 'descripcion')  # Necesario para autocomplete

@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ('venta', 'producto', 'descripcion_libre', 'cantidad', 'precio_unitario', 'venta_gravada')
    list_filter = ('venta',)

@admin.register(Liquidacion)
class LiquidacionAdmin(admin.ModelAdmin):
    list_display = ('fecha_documento', 'nombre_agente', 'monto_operacion', 'liquido_pagar')

@admin.register(RetencionRecibida)
class RetencionRecibidaAdmin(admin.ModelAdmin):
    list_display = ('fecha_documento', 'nombre_agente', 'monto_retenido_1', 'estado')
    list_filter = ('estado', 'empresa')

@admin.register(TareaFacturacion)
class TareaFacturacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'venta', 'estado', 'intentos', 'proximo_reintento', 'creada_at')
    list_filter = ('estado',)
    search_fields = ('venta__id',)
    readonly_fields = ('venta', 'intentos', 'creada_at', 'actualizada_at')
    ordering = ('-creada_at',)

@admin.register(Correlativo)
class CorrelativoAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'tipo_dte', 'anio', 'ultimo_correlativo', 'fecha_actualizacion')
    list_filter = ('empresa', 'tipo_dte', 'anio')
    search_fields = ('empresa__nombre',)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    ordering = ['empresa', 'tipo_dte', '-anio', '-ultimo_correlativo']
    
    fieldsets = (
        ('Información del Correlativo', {
            'fields': ('empresa', 'tipo_dte', 'anio', 'ultimo_correlativo')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )

# --- PERFIL DE USUARIO (Sistema Multi-Empresa) ---
@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('user', 'empresa', 'rol', 'activo', 'fecha_creacion')
    list_filter = ('rol', 'activo', 'empresa', 'fecha_creacion')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'empresa__nombre')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    
    fieldsets = (
        ('Usuario y Empresa', {
            'fields': ('user', 'empresa', 'rol')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimizar consultas con select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'empresa')

# --- EXTENSIÓN DEL ADMIN DE USER PARA MOSTRAR PERFIL ---
class PerfilUsuarioInline(admin.StackedInline):
    """Inline para mostrar el perfil en el admin de User"""
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil de Usuario'
    fk_name = 'user'

class UserAdmin(BaseUserAdmin):
    """Admin personalizado de User que incluye el perfil"""
    inlines = (PerfilUsuarioInline,)
    
    def get_inline_instances(self, request, obj=None):
        """Solo mostrar inline si el objeto existe (no en creación)"""
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

# Desregistrar el admin de User por defecto y registrar el personalizado
admin.site.unregister(User)
admin.site.register(User, UserAdmin)