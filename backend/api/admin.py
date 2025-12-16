from django.contrib import admin
from .models import Cliente, Compra, Venta  # <--- Agrega Venta aquí
from .models import Empresa  # Asegúrate de que esté importado arriba

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nrc', 'nombre')

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('fecha_emision', 'nombre_proveedor', 'monto_total', 'estado')

# --- NUEVO ---
@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('fecha_emision', 'tipo_venta', 'venta_gravada', 'debito_fiscal')
    list_filter = ('cliente', 'periodo_aplicado', 'tipo_venta')

admin.site.register(Empresa)