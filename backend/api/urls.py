from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from .views import EmpresaViewSet, VentaViewSet, ActividadEconomicaViewSet

router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet, basename='empresa')
router.register(r'ventas', VentaViewSet, basename='venta')
router.register(r'actividades', ActividadEconomicaViewSet, basename='actividadeconomica')

urlpatterns = [
    path('auth/login/', views.login_api, name='login_api'),
    path('auth/me/', views.auth_me_api, name='auth_me'),
    path('auth/change-password/', views.change_password_api, name='change_password_api'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    path('clientes/', views.clientes_api, name='clientes_api'),
    path('clientes/<int:pk>/', views.cliente_detail_api, name='cliente_detail_api'),
    
    # COMPRAS
    path('compras/crear/', views.crear_compra),
    path('compras/listar/', views.listar_compras),
    path('compras/<int:pk>/', views.obtener_compra),
    path('compras/borrar/<int:pk>/', views.borrar_compra),
    path('compras/actualizar/<int:pk>/', views.actualizar_compra),
    
    # VENTAS
    path('ventas/crear/', views.crear_venta),
    path('ventas/crear-con-detalles/', views.crear_venta_con_detalles),
    path('ventas/listar/', views.listar_ventas),
    path('ventas/<int:pk>/', views.obtener_venta),
    path('ventas/<int:pk>/generar-dte/', views.generar_dte_venta),
    path('ventas/<int:pk>/generar-pdf/', views.generar_pdf_venta_endpoint),
    path('ventas/borrar/<int:pk>/', views.borrar_venta),
    path('ventas/actualizar/<int:pk>/', views.actualizar_venta),
    
    # PRODUCTOS
    path('productos/', views.listar_productos),
    
    # RETENCIONES
    path('retenciones/crear/', views.crear_retencion),
    path('retenciones/listar/', views.listar_retenciones),
    
    # LIQUIDACIONES
    path('liquidaciones/listar/', views.listar_liquidaciones),
    
    # RETENCIONES RECIBIDAS
    path('retenciones-recibidas/listar/', views.listar_retenciones_recibidas),
    path('retenciones-recibidas/<int:pk>/', views.obtener_retencion_recibida),
    path('retenciones-recibidas/<int:pk>/aplicar/', views.aplicar_retencion),
    path('ventas/para-conciliacion/', views.obtener_ventas_para_conciliacion),
    
    # FINANZAS
    path('finanzas/resumen/', views.resumen_fiscal),
    
    # SISTEMA MASIVO
    path('sistema/procesar-lote/', views.procesar_lote_dtes),
    path('sistema/guardar-lote/', views.guardar_lote_aprobado),
    path('sistema/procesar-json-dte/', views.procesar_json_dte),
    
    # REPORTES CSV
    path('reportes/csv-compras/', views.generar_csv_compras),
    path('reportes/csv-ventas-ccf/', views.generar_csv_ventas_ccf),
    path('reportes/csv-ventas-cf/', views.generar_csv_ventas_cf),
    path('reportes/csv-161/', views.generar_csv_161),  # Liquidaciones
    path('reportes/csv-162/', views.generar_csv_162),  # Retenciones Recibidas
    path('reportes/csv-163/', views.generar_csv_163),  # Percepciones IVA
    
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
    # Libros IVA unificado: mes, anio, tipo_libro, format=pdf|csv (opcional)
    path('libros-iva/reporte/', views.libros_iva_reporte_api),
]

urlpatterns += router.urls