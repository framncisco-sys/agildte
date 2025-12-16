from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import EmpresaViewSet

router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet, basename='empresa')

urlpatterns = [
    path('clientes/', views.clientes_api, name='clientes_api'),
    
    # COMPRAS
    path('compras/crear/', views.crear_compra),
    path('compras/listar/', views.listar_compras),
    path('compras/<int:pk>/', views.obtener_compra),
    path('compras/borrar/<int:pk>/', views.borrar_compra),
    path('compras/actualizar/<int:pk>/', views.actualizar_compra),
    
    # VENTAS
    path('ventas/crear/', views.crear_venta),
    path('ventas/listar/', views.listar_ventas),
    path('ventas/<int:pk>/', views.obtener_venta),
    path('ventas/borrar/<int:pk>/', views.borrar_venta),
    path('ventas/actualizar/<int:pk>/', views.actualizar_venta),
    
    # RETENCIONES
    path('retenciones/crear/', views.crear_retencion),
    path('retenciones/listar/', views.listar_retenciones),
    
    # FINANZAS
    path('finanzas/resumen/', views.resumen_fiscal),
    
    # SISTEMA MASIVO
    path('sistema/procesar-lote/', views.procesar_lote_dtes),
    path('sistema/guardar-lote/', views.guardar_lote_aprobado),
    
    # REPORTES CSV
    path('reportes/csv-compras/', views.generar_csv_compras),
    path('reportes/csv-ventas-ccf/', views.generar_csv_ventas_ccf),
    path('reportes/csv-ventas-cf/', views.generar_csv_ventas_cf),
    path('reportes/csv-161/', views.generar_csv_161),
    path('reportes/csv-162/', views.generar_csv_162),
    path('reportes/csv-163/', views.generar_csv_163),
    
    # REPORTES PDF
    path('reportes/pdf-compras/', views.generar_pdf_compras),
    path('reportes/pdf-ventas-cf/', views.generar_pdf_ventas_cf),
    path('reportes/pdf-ventas-ccf/', views.generar_pdf_ventas_ccf),
    
    # LIBROS DE IVA - VISTA PREVIA (JSON)
    path('libros-iva/vista-previa-compras/', views.vista_previa_compras),
    path('libros-iva/vista-previa-ventas-ccf/', views.vista_previa_ventas_ccf),
    path('libros-iva/vista-previa-ventas-cf/', views.vista_previa_ventas_cf),
    
    # LIBROS DE IVA - REPORTES CSV/PDF POR EMPRESA
    path('libros-iva/csv-compras/', views.reporte_csv_compras_empresa),
    path('libros-iva/pdf-compras/', views.reporte_pdf_compras_empresa),
    path('libros-iva/csv-ventas-ccf/', views.reporte_csv_ventas_ccf_empresa),
    path('libros-iva/pdf-ventas-ccf/', views.reporte_pdf_ventas_ccf_empresa),
    path('libros-iva/csv-ventas-cf/', views.reporte_csv_ventas_cf_empresa),
    path('libros-iva/pdf-ventas-cf/', views.reporte_pdf_ventas_cf_empresa),
]

urlpatterns += router.urls