import calendar
import json
import csv
import logging
import zipfile
import io
from decimal import Decimal
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, F, Sum
from django.db.models.functions import TruncDay
from django.utils import timezone
from rest_framework.decorators import api_view, action, permission_classes as drf_permission_classes
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.renderers import BaseRenderer
from rest_framework.permissions import IsAuthenticated as DRFIsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from .models import Cliente, Compra, Venta, Retencion, Empresa, Liquidacion, RetencionRecibida, Producto, DetalleVenta, PerfilUsuario, ActividadEconomica
from .serializers import ClienteSerializer, CompraSerializer, VentaSerializer, RetencionSerializer, EmpresaSerializer, LiquidacionSerializer, RetencionRecibidaSerializer, ProductoSerializer, VentaConDetallesSerializer, ActividadEconomicaSerializer
from .dte_generator import DTEGenerator
from .utils.pdf_generator import generar_pdf_venta
from .utils.tenant import get_empresa_ids_allowlist, require_empresa_allowed, require_object_empresa_allowed, get_and_validate_empresa
from .services import FacturacionService, FacturacionServiceError, AutenticacionMHError, FirmaDTEError, EnvioMHError

logger = logging.getLogger(__name__)

# --- UTILIDADES ---
def safe_float(val):
    try: return float(val) if val else 0.0
    except: return 0.0

def limpiar(valor):
    if not valor: return ""
    return str(valor).replace("-", "").replace(" ", "").strip()

def limpiar_nit(valor):
    """Limpia NIT/NRC para búsqueda"""
    if not valor: return ""
    return str(valor).replace("-", "").replace(" ", "").strip()


# --- AUTH / LOGIN JWT ---
from rest_framework_simplejwt.tokens import RefreshToken

@csrf_exempt
@api_view(['POST'])
@drf_permission_classes([permissions.AllowAny])
def login_api(request):
    """
    Login con JWT. Acepta username+password o email+password.
    Regla: Superusuario ve todas las empresas. Usuario normal solo su empresa asignada.
    Respuesta incluye access, refresh, user, empresa_default, is_superuser.
    """
    username = request.data.get('username', '').strip()
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')
    login_input = username or email

    if not password or not login_input:
        return Response({'detail': 'Usuario/email y contraseña requeridos'}, status=status.HTTP_400_BAD_REQUEST)

    user = None
    if username:
        user = authenticate(request, username=username, password=password)
    if not user and email:
        try:
            u = User.objects.get(email__iexact=email)
            user = authenticate(request, username=u.username, password=password)
        except User.DoesNotExist:
            pass
    if not user and login_input and '@' not in login_input:
        user = authenticate(request, username=login_input, password=password)

    if not user or not user.is_active:
        return Response({'detail': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)
    empresa_default = None
    try:
        perfil = PerfilUsuario.objects.select_related('empresa').get(user=user, activo=True)
        if perfil.empresa:
            empresa_default = {'id': perfil.empresa.id, 'nombre': perfil.empresa.nombre}
    except PerfilUsuario.DoesNotExist:
        if user.is_superuser and Empresa.objects.exists():
            primera = Empresa.objects.first()
            empresa_default = {'id': primera.id, 'nombre': primera.nombre}

    from .permissions import get_user_role
    role = get_user_role(user)
    resp = {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email or '',
            'is_superuser': user.is_superuser,
            'role': role or 'VENDEDOR',
        },
        'empresa_default': empresa_default,
    }
    if user.is_superuser:
        resp['empresas'] = [
            {'id': e.id, 'nombre': e.nombre}
            for e in Empresa.objects.all().order_by('nombre')[:100]
        ]
    return Response(resp)


@api_view(['POST'])
def change_password_api(request):
    """
    Cambio de contraseña del usuario autenticado.
    Body: { "old_password": "...", "new_password": "..." }
    """
    if not request.user or not request.user.is_authenticated:
        return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    old_password = request.data.get('old_password') or ''
    new_password = request.data.get('new_password') or ''
    if not old_password or not new_password:
        return Response(
            {'detail': 'Debe indicar contraseña actual y nueva contraseña'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not request.user.check_password(old_password):
        return Response({'detail': 'Contraseña actual incorrecta'}, status=status.HTTP_400_BAD_REQUEST)
    if len(new_password) < 8:
        return Response(
            {'detail': 'La nueva contraseña debe tener al menos 8 caracteres'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    request.user.set_password(new_password)
    request.user.save()
    return Response({'detail': 'Contraseña actualizada correctamente'})


@api_view(['GET'])
def auth_me_api(request):
    """
    Devuelve el usuario actual, rol, empresa_default y empresas (requiere JWT).
    Útil tras login con /api/token/ para poblar el estado del frontend.
    """
    if not request.user or not request.user.is_authenticated:
        return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
    user = request.user
    from .permissions import get_user_role
    role = get_user_role(user)
    empresa_default = None
    try:
        perfil = PerfilUsuario.objects.select_related('empresa').get(user=user, activo=True)
        if perfil.empresa:
            empresa_default = {'id': perfil.empresa.id, 'nombre': perfil.empresa.nombre}
    except PerfilUsuario.DoesNotExist:
        if user.is_superuser and Empresa.objects.exists():
            primera = Empresa.objects.first()
            empresa_default = {'id': primera.id, 'nombre': primera.nombre}
    resp = {
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email or '',
            'is_superuser': user.is_superuser,
            'role': role or 'VENDEDOR',
        },
        'empresa_default': empresa_default,
    }
    if user.is_superuser:
        resp['empresas'] = [
            {'id': e.id, 'nombre': e.nombre}
            for e in Empresa.objects.all().order_by('nombre')[:100]
        ]
    return Response(resp)


class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer


class ActividadEconomicaLimitPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 50


class ActividadEconomicaViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de actividades económicas (MH). Solo lectura. ?search= filtra por código o descripción."""
    serializer_class = ActividadEconomicaSerializer
    pagination_class = ActividadEconomicaLimitPagination

    def get_queryset(self):
        qs = ActividadEconomica.objects.all().order_by('codigo')
        search = (self.request.query_params.get('search') or '').strip()
        if search:
            qs = qs.filter(
                Q(codigo__icontains=search) | Q(descripcion__icontains=search)
            )
        return qs


class VentaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar ventas con acciones personalizadas.
    Crear venta: VENDEDOR o ADMIN. Invalidar DTE: solo ADMIN.
    """
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer

    def get_permissions(self):
        from .permissions import IsAdminUser, IsVendedorUser
        if self.action in ('invalidar', 'destroy'):
            return [DRFIsAuthenticated(), IsAdminUser()]
        if self.action in ('create', 'update', 'partial_update'):
            return [DRFIsAuthenticated(), IsVendedorUser()]
        return [DRFIsAuthenticated()]

    @action(detail=False, methods=['get'], url_path='descargar-lote')
    def descargar_lote(self, request):
        """GET ?format=pdf|json - Descarga ZIP de PDFs o JSONs filtrados (generación dinámica en memoria)."""
        return download_batch_ventas(request)

    @action(detail=True, methods=['post'], url_path='emitir-factura')
    def emitir_factura(self, request, pk=None):
        """
        Emite una factura electrónica procesándola con el Ministerio de Hacienda.
        Con USE_ASYNC_FACTURACION=True, encola la tarea y responde de inmediato.
        
        Endpoint: POST /api/ventas/{id}/emitir-factura/
        """
        from django.conf import settings
        from .models import TareaFacturacion

        try:
            venta = self.get_object()
        except Venta.DoesNotExist:
            return Response({
                "error": "Venta no encontrada",
                "mensaje": f"No existe una venta con el ID {pk}"
            }, status=status.HTTP_404_NOT_FOUND)

        r = require_object_empresa_allowed(request, venta)
        if r is not None:
            return r

        # Procesamiento asíncrono
        if getattr(settings, 'USE_ASYNC_FACTURACION', True):
            TareaFacturacion.objects.get_or_create(
                venta=venta,
                defaults={'estado': 'Pendiente'}
            )
            return Response({
                "mensaje": "Factura en cola. Se procesará en breve (firma, envío a Hacienda y correo).",
                "venta_id": venta.id,
                "procesamiento": "asincrono",
                "estado_dte": venta.estado_dte or 'Borrador',
            }, status=status.HTTP_200_OK)

        # Procesamiento síncrono (legacy)
        if not venta.empresa:
            return Response({
                "error": "La venta no tiene una empresa asociada",
                "mensaje": "Debes asociar una empresa a la venta antes de emitir la factura"
            }, status=status.HTTP_400_BAD_REQUEST)

        empresa = venta.empresa

        # Validar que la empresa tenga credenciales configuradas
        if not empresa.user_api_mh or not empresa.clave_api_mh:
            return Response({
                "error": "La empresa no tiene credenciales de MH configuradas",
                "mensaje": "Debes configurar user_api_mh y clave_api_mh en la empresa",
                "empresa_id": empresa.id,
                "empresa_nombre": empresa.nombre
            }, status=status.HTTP_400_BAD_REQUEST)

        if not empresa.archivo_certificado or not empresa.clave_certificado:
            return Response({
                "error": "La empresa no tiene certificado digital configurado",
                "mensaje": "Debes configurar archivo_certificado y clave_certificado en la empresa",
                "empresa_id": empresa.id,
                "empresa_nombre": empresa.nombre
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            servicio = FacturacionService(empresa)
        except ValueError as e:
            return Response({
                "error": "Error al inicializar el servicio de facturación",
                "mensaje": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            resultado = servicio.procesar_factura(venta)
            if resultado.get('exito'):
                return Response({
                    "mensaje": "Factura emitida exitosamente",
                    "venta_id": resultado['venta_id'],
                    "codigo_generacion": resultado['codigo_generacion'],
                    "numero_control": resultado['numero_control'],
                    "sello_recibido": resultado['sello_recibido'],
                    "estado": resultado['estado'],
                    "datos_completos": resultado
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "La factura fue rechazada por el Ministerio de Hacienda",
                    "mensaje": resultado.get('mensaje', 'Sin mensaje'),
                    "observaciones": resultado.get('observaciones', 'Sin observaciones'),
                    "estado": resultado.get('estado'),
                    "venta_id": resultado['venta_id'],
                    "codigo_generacion": resultado.get('codigo_generacion'),
                    "numero_control": resultado.get('numero_control')
                }, status=status.HTTP_400_BAD_REQUEST)
        except AutenticacionMHError as e:
            logger.error(f"Error de autenticación MH para venta {venta.id}: {str(e)}")
            return Response({
                "error": "Error de autenticación con el Ministerio de Hacienda",
                "mensaje": str(e),
                "tipo_error": "AutenticacionMHError",
                "venta_id": venta.id
            }, status=status.HTTP_400_BAD_REQUEST)
        except FirmaDTEError as e:
            logger.error(f"Error de firma DTE para venta {venta.id}: {str(e)}")
            return Response({
                "error": "Error al firmar el documento DTE",
                "mensaje": str(e),
                "tipo_error": "FirmaDTEError",
                "venta_id": venta.id
            }, status=status.HTTP_400_BAD_REQUEST)
        except EnvioMHError as e:
            logger.error(f"Error de envío a MH para venta {venta.id}: {str(e)}")
            venta.estado_dte = 'ErrorEnvio'
            venta.error_envio_mensaje = str(e)[:500] if str(e) else None
            venta.save(update_fields=['estado_dte', 'error_envio_mensaje'])
            return Response({
                "exito": False,
                "error": "Error al enviar el DTE al Ministerio de Hacienda",
                "mensaje": str(e),
                "reintentar": True,
                "venta_id": venta.id,
                "estado_dte": "ErrorEnvio"
            }, status=status.HTTP_200_OK)
        except FacturacionServiceError as e:
            logger.error(f"Error en servicio de facturación para venta {venta.id}: {str(e)}")
            return Response({
                "error": "Error en el proceso de facturación",
                "mensaje": str(e),
                "tipo_error": "FacturacionServiceError",
                "venta_id": venta.id
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error inesperado al emitir factura {venta.id}: {str(e)}", exc_info=True)
            return Response({
                "error": "Error inesperado al procesar la factura",
                "mensaje": str(e),
                "tipo_error": "Exception",
                "venta_id": venta.id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='invalidar')
    def invalidar(self, request, pk=None):
        """
        Invalida (anula) un DTE ya procesado por MH.
        Endpoint: POST /api/ventas/{id}/invalidar/
        Body: { motivoInvalidacion, tipoInvalidacion, responsable: {nombre, tipoDocumento, numeroDocumento},
                solicitante: {nombre, tipoDocumento, numeroDocumento}, codigoGeneracionDocumentoReemplazo? }
        """
        try:
            venta = self.get_object()
        except Venta.DoesNotExist:
            return Response({
                "error": "Venta no encontrada",
                "mensaje": f"No existe una venta con el ID {pk}"
            }, status=status.HTTP_404_NOT_FOUND)

        if not venta.sello_recepcion:
            return Response({
                "error": "No se puede invalidar",
                "mensaje": "Solo se pueden invalidar documentos ya procesados por MH"
            }, status=status.HTTP_400_BAD_REQUEST)

        if venta.estado_dte == 'Anulado':
            return Response({
                "error": "Documento ya anulado",
                "mensaje": "Este documento ya fue invalidado"
            }, status=status.HTTP_400_BAD_REQUEST)

        if not venta.empresa:
            return Response({
                "error": "La venta no tiene empresa asociada"
            }, status=status.HTTP_400_BAD_REQUEST)

        empresa = venta.empresa
        if not empresa.user_api_mh or not empresa.clave_api_mh or not empresa.archivo_certificado or not empresa.clave_certificado:
            return Response({
                "error": "Empresa sin credenciales de MH configuradas"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            servicio = FacturacionService(empresa)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        datos = request.data or {}
        datos_invalidacion = {
            "motivoInvalidacion": datos.get("motivoInvalidacion", "").strip() or "Solicitud del contribuyente",
            "tipoInvalidacion": datos.get("tipoInvalidacion", "Rescisión"),
            "responsable": {
                "nombre": datos.get("nombreResponsable", "").strip(),
                "tipoDocumento": datos.get("tipoDocResponsable", "NIT"),
                "numeroDocumento": (datos.get("numeroDocResponsable") or "").strip(),
            },
            "solicitante": {
                "nombre": datos.get("nombreSolicitante", "").strip(),
                "tipoDocumento": datos.get("tipoDocSolicitante", "NIT"),
                "numeroDocumento": (datos.get("numeroDocSolicitante") or "").strip(),
            },
            "codigoGeneracionDocumentoReemplazo": datos.get("codigoGeneracionDocumentoReemplazo"),
        }

        try:
            resultado = servicio.invalidar_dte(venta, datos_invalidacion)
            if resultado.get("exito"):
                venta.refresh_from_db()
                return Response({
                    "mensaje": resultado.get("mensaje", "Documento invalidado correctamente"),
                    "venta_id": venta.id,
                    "estado_dte": venta.estado_dte,
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Invalidación rechazada por MH",
                    "mensaje": resultado.get("mensaje", "Sin mensaje"),
                    "observaciones": resultado.get("observaciones", []),
                }, status=status.HTTP_400_BAD_REQUEST)
        except (FacturacionServiceError, AutenticacionMHError, FirmaDTEError, EnvioMHError) as e:
            return Response({
                "error": "Error en invalidación",
                "mensaje": str(e),
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error inesperado al invalidar venta {venta.id}: {str(e)}", exc_info=True)
            return Response({
                "error": "Error inesperado",
                "mensaje": str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- CLIENTES ---
# --- CLIENTES (UNIFICADO) ---
from .permissions import IsVendedorUser

@api_view(['GET', 'POST'])
@drf_permission_classes([DRFIsAuthenticated, IsVendedorUser])
def clientes_api(request):
    if request.method == 'GET':
        clientes = Cliente.objects.all()
        search = request.query_params.get('search', '').strip()
        nrc = request.query_params.get('nrc', None)
        if search:
            clientes = clientes.filter(
                Q(nombre__icontains=search) |
                Q(nrc__icontains=search) |
                Q(nit__icontains=search) |
                Q(dui__icontains=search) |
                Q(documento_identidad__icontains=search)
            )
        elif nrc:
            clientes = clientes.filter(nrc=nrc)
        serializer = ClienteSerializer(clientes, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Lógica de crear
        serializer = ClienteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@drf_permission_classes([DRFIsAuthenticated, IsVendedorUser])
def cliente_detail_api(request, pk):
    """GET, actualizar o eliminar un cliente por ID."""
    try:
        cliente = Cliente.objects.get(pk=pk)
    except Cliente.DoesNotExist:
        return Response({'detail': 'Cliente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        serializer = ClienteSerializer(cliente)
        return Response(serializer.data)
    if request.method in ('PUT', 'PATCH'):
        partial = (request.method == 'PATCH')
        serializer = ClienteSerializer(cliente, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    if request.method == 'DELETE':
        cliente.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


# --- DASHBOARD ---
def _total_pagar_venta(venta):
    """Calcula total a pagar de una Venta (venta_gravada + exenta + no_sujeta + iva - retenciones)."""
    vg = float(venta.venta_gravada or 0)
    ve = float(venta.venta_exenta or 0)
    vn = float(venta.venta_no_sujeta or 0)
    df = float(venta.debito_fiscal or 0)
    i1 = float(venta.iva_retenido_1 or 0)
    i2 = float(venta.iva_retenido_2 or 0)
    return round(vg + ve + vn + df - i1 - i2, 2)


@api_view(['GET'])
def dashboard_stats_api(request):
    """
    KPIs y datos para el dashboard: ventas del mes actual (estado AceptadoMH/Enviado = procesado),
    tendencia por día y últimas 5 ventas. Requiere empresa_id o filtra por empresas permitidas.
    """
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return Response({"error": "Autenticación requerida"}, status=status.HTTP_401_UNAUTHORIZED)

    empresa_id = request.query_params.get('empresa_id')
    if empresa_id:
        r = require_empresa_allowed(request, int(empresa_id))
        if r is not None:
            return r
        empresa_ids = [int(empresa_id)]

    now = timezone.now().date()
    year, month = now.year, now.month
    first_day = timezone.datetime(year, month, 1).date()
    _, last_day_num = calendar.monthrange(year, month)
    last_day = timezone.datetime(year, month, last_day_num).date()

    filtro_tenant = Q(empresa_id__in=empresa_ids)
    filtro_procesado = Q(estado_dte__in=['AceptadoMH', 'Enviado'])
    filtro_mes = Q(fecha_emision__gte=first_day, fecha_emision__lte=last_day)
    filtro_hoy = Q(fecha_emision=now)

    base_mes = Venta.objects.filter(filtro_tenant, filtro_procesado, filtro_mes)
    base_hoy = Venta.objects.filter(filtro_tenant, filtro_procesado, filtro_hoy)

    # total_ventas_mes: suma de total_pagar
    total_ventas_mes = Decimal('0.00')
    for v in base_mes.only('venta_gravada', 'venta_exenta', 'venta_no_sujeta', 'debito_fiscal', 'iva_retenido_1', 'iva_retenido_2'):
        total_ventas_mes += Decimal(str(_total_pagar_venta(v)))
    total_ventas_mes = float(total_ventas_mes)

    cantidad_dtes_mes = base_mes.count()

    ventas_hoy = Decimal('0.00')
    for v in base_hoy.only('venta_gravada', 'venta_exenta', 'venta_no_sujeta', 'debito_fiscal', 'iva_retenido_1', 'iva_retenido_2'):
        ventas_hoy += Decimal(str(_total_pagar_venta(v)))
    ventas_hoy = float(ventas_hoy)

    # ventas_por_dia: agrupar por día del mes actual (todos los días 1..last_day_num)
    ventas_por_dia_map = {}
    for d in range(1, last_day_num + 1):
        ventas_por_dia_map[d] = 0.0
    ventas_mes = Venta.objects.filter(filtro_tenant, filtro_procesado, filtro_mes).only(
        'fecha_emision', 'venta_gravada', 'venta_exenta', 'venta_no_sujeta', 'debito_fiscal', 'iva_retenido_1', 'iva_retenido_2'
    )
    for v in ventas_mes:
        dia = v.fecha_emision.day
        ventas_por_dia_map[dia] = ventas_por_dia_map.get(dia, 0) + _total_pagar_venta(v)
    ventas_por_dia = [
        {"dia": f"{d:02d}", "total": round(ventas_por_dia_map[d], 2)}
        for d in range(1, last_day_num + 1)
    ]

    # ultimas_ventas: últimos 5 (cualquier estado), serializado simple
    ultimas = Venta.objects.filter(filtro_tenant).select_related('cliente').order_by('-fecha_emision', '-id')[:5]
    ultimas_ventas = []
    for v in ultimas:
        cliente_nombre = v.nombre_receptor or (v.cliente.nombre if v.cliente else '') or 'N/A'
        total = _total_pagar_venta(v)
        ultimas_ventas.append({
            "id": v.id,
            "numero_control": v.numero_control or v.numero_documento or str(v.id),
            "cliente": cliente_nombre,
            "total": total,
            "estado": v.estado_dte or 'Borrador',
        })

    return Response({
        "total_ventas_mes": total_ventas_mes,
        "cantidad_dtes_mes": cantidad_dtes_mes,
        "ventas_hoy": ventas_hoy,
        "ventas_por_dia": ventas_por_dia,
        "ultimas_ventas": ultimas_ventas,
    })


# --- CARGA MASIVA ---
@api_view(['POST'])
def procesar_lote_dtes(request):
    cliente_nrc = request.data.get('nrc_activo')
    archivos = request.FILES.getlist('archivos')
    if not cliente_nrc: return Response({"error": "Sin cliente"}, status=400)
    
    mi_nrc = limpiar(cliente_nrc)
    reporte = { "compras": [], "ventas": [], "retenciones": [], "ignorados": [], "resumen": {"total_iva_compras": 0, "total_iva_ventas": 0} }

    for archivo in archivos:
        try:
            contenido = json.load(archivo)
            ident = contenido.get('identificacion', {})
            tipo_dte = ident.get('tipoDte')
            codigo = str(ident.get('codigoGeneracion', '')).strip()
            num_control = ident.get('numeroControl', '')
            fecha = ident.get('fecEmi')
            sello = ident.get('selloRecibido') or contenido.get('selloRecibido')
            
            emisor = contenido.get('emisor', {})
            receptor = contenido.get('receptor') or {}
            cuerpo = contenido.get('resumen', {})
            
            nrc_emis = limpiar(emisor.get('nrc'))
            nrc_recep = limpiar(receptor.get('nrc'))
            soy_emisor = (nrc_emis == mi_nrc)
            soy_receptor = (nrc_recep == mi_nrc)

            if not soy_emisor and not soy_receptor:
                reporte["ignorados"].append({"archivo": archivo.name, "motivo": f"NRC Ajeno ({nrc_emis} vs {nrc_recep})"})
                continue 

            gravado = safe_float(cuerpo.get('totalGravada'))
            iva = safe_float(cuerpo.get('totalIva'))
            total = safe_float(cuerpo.get('totalPagar'))
            percepcion = safe_float(cuerpo.get('totalIvaPercibido')) # <--- PERCEPCIÓN

            if iva == 0 and tipo_dte != '14':
                tributos = cuerpo.get('tributos') or []
                if not tributos and 'cuerpoDocumento' in contenido:
                     for item in contenido['cuerpoDocumento']: iva += safe_float(item.get('ivaItem'))
                else:
                    for t in tributos:
                        if t.get('codigo') == '20': iva += safe_float(t.get('valor'))

            if soy_receptor: # COMPRA
                if tipo_dte == '03' or tipo_dte == '14': 
                    existe = Compra.objects.filter(cliente__nrc=cliente_nrc, codigo_generacion=codigo).exists()
                    estado = "Duplicado" if existe else "Nuevo"
                    item = { "archivo": archivo.name, "codigo": codigo, "fecha": fecha, "tipo_dte": tipo_dte, "emisor_nombre": emisor.get('nombre'), "emisor_nrc": emisor.get('nrc'), "gravado": gravado, "iva": iva, "percepcion": percepcion, "total": total, "sello": sello, "clasificacion_1": "Gravada", "clasificacion_2": "Gasto", "estado_validacion": estado }
                    if estado == "Duplicado": reporte["ignorados"].append({"archivo": archivo.name, "motivo": "Ya registrada"})
                    else: 
                        reporte["compras"].append(item)
                        reporte["resumen"]["total_iva_compras"] += iva
                elif tipo_dte == '07':
                    item = { "archivo": archivo.name, "codigo": codigo, "fecha": fecha, "tipo_dte": tipo_dte, "emisor_nombre": emisor.get('nombre'), "emisor_nrc": emisor.get('nit'), "monto_sujeto": safe_float(cuerpo.get('totalSujetoRetencion')), "monto_retenido": safe_float(cuerpo.get('totalIVAretenido')), "sello": sello }
                    reporte["retenciones"].append(item)

            elif soy_emisor: # VENTA
                if tipo_dte in ['01', '03']:
                    existe = Venta.objects.filter(cliente__nrc=cliente_nrc, numero_documento=codigo).exists()
                    estado = "Duplicado" if existe else "Nuevo"
                    if tipo_dte == '01' and iva == 0 and gravado > 0:
                         real_gravado = gravado / 1.13; iva = gravado - real_gravado; gravado = real_gravado
                    item = { "archivo": archivo.name, "codigo": codigo, "num_control": num_control, "fecha": fecha, "tipo_dte": tipo_dte, "receptor_nombre": receptor.get('nombre') or "Consumidor Final", "receptor_nrc": receptor.get('nrc'), "gravado": gravado, "iva": iva, "total": total, "sello": sello, "clasificacion_venta": "1", "tipo_ingreso": "3", "estado_validacion": estado }
                    if estado == "Duplicado": reporte["ignorados"].append({"archivo": archivo.name, "motivo": "Ya registrada"})
                    else:
                        reporte["ventas"].append(item)
                        reporte["resumen"]["total_iva_ventas"] += iva

        except Exception as e:
            reporte["ignorados"].append({"archivo": archivo.name, "motivo": f"Error: {str(e)}"})
    return Response(reporte)

@api_view(['POST'])
def guardar_lote_aprobado(request):
    data = request.data
    cliente_nrc = data.get('nrc_activo')
    try: cliente_obj = Cliente.objects.get(nrc=cliente_nrc)
    except: return Response({"error": "Cliente no existe"}, status=404)
    res = {"compras": 0, "ventas": 0, "retenciones": 0, "duplicados": 0}

    for c in data.get('compras', []):
        if not Compra.objects.filter(cliente=cliente_obj, codigo_generacion=c['codigo']).exists():
            Compra.objects.create(cliente=cliente_obj, fecha_emision=c['fecha'], tipo_documento=c['tipo_dte'], codigo_generacion=c['codigo'], nrc_proveedor=c['emisor_nrc'], nombre_proveedor=c['emisor_nombre'], monto_gravado=c['gravado'], monto_iva=c['iva'], monto_percepcion=c.get('percepcion', 0), monto_total=c['total'], periodo_aplicado=c['fecha'][:7], estado="Registrado", clasificacion_1=c.get('clasificacion_1', 'Gravada'), clasificacion_2=c.get('clasificacion_2', 'Gasto'))
            res["compras"] += 1
        else: res["duplicados"] += 1

    for v in data.get('ventas', []):
        if not Venta.objects.filter(cliente=cliente_obj, numero_documento=v['codigo']).exists():
            tipo = 'CCF' if v['tipo_dte'] == '03' else 'CF'
            Venta.objects.create(cliente=cliente_obj, fecha_emision=v['fecha'], periodo_aplicado=v['fecha'][:7], tipo_venta=tipo, clase_documento='4', numero_documento=v['codigo'], numero_control=v.get('num_control'), sello_recepcion=v.get('sello'), nombre_receptor=v.get('receptor_nombre'), nrc_receptor=v.get('receptor_nrc'), venta_gravada=v.get('gravado',0), debito_fiscal=v.get('iva',0), clasificacion_venta=v.get('clasificacion_venta', '1'), tipo_ingreso=v.get('tipo_ingreso', '3'))
            res["ventas"] += 1
        else: res["duplicados"] += 1

    for r in data.get('retenciones', []):
        if not Retencion.objects.filter(cliente=cliente_obj, codigo_generacion=r['codigo']).exists():
            Retencion.objects.create(cliente=cliente_obj, fecha_emision=r['fecha'], periodo_aplicado=r['fecha'][:7], tipo_retencion='162', codigo_generacion=r['codigo'], sello_recepcion=r.get('sello'), nombre_emisor=r.get('emisor_nombre'), nit_emisor=r.get('nit_emisor') or "", monto_sujeto=r.get('monto_sujeto', 0), monto_retenido=r.get('monto_retenido', 0))
            res["retenciones"] += 1
        else: res["duplicados"] += 1
    return Response({"status": "ok", "resumen": res})

# --- PROCESADOR INTELIGENTE DE DTEs (EL CLASIFICADOR) ---
@api_view(['POST'])
def procesar_json_dte(request):
    """
    Endpoint que recibe archivos JSON de DTEs y los clasifica automáticamente:
    - DTE-09 (Liquidación) -> Modelo Liquidacion
    - DTE-07 (Retención) -> Modelo RetencionRecibida
    - DTE-03/14 (CCF/Factura) -> Modelo Compra
    """
    empresa, err = get_and_validate_empresa(request, from_body=True)
    if err is not None:
        return err
    if empresa is None:
        return Response({"error": "Falta empresa_id"}, status=400)

    archivos = request.FILES.getlist('archivos')
    if not archivos:
        return Response({"error": "No se proporcionaron archivos"}, status=400)
    
    reporte = {
        "liquidaciones": [],
        "retenciones": [],
        "compras": [],
        "errores": [],
        "resumen": {
            "liquidaciones_guardadas": 0,
            "retenciones_guardadas": 0,
            "compras_guardadas": 0,
            "duplicados": 0,
            "errores": 0
        }
    }
    
    for archivo in archivos:
        try:
            contenido = json.load(archivo)
            ident = contenido.get('identificacion', {})
            tipo_dte = ident.get('tipoDte', '').strip()
            codigo = str(ident.get('codigoGeneracion', '')).strip()
            fecha_str = ident.get('fecEmi', '')
            sello = ident.get('selloRecibido') or contenido.get('selloRecibido', '')
            
            if not codigo:
                reporte["errores"].append({"archivo": archivo.name, "motivo": "Sin código de generación"})
                reporte["resumen"]["errores"] += 1
                continue
            
            # Extraer datos del emisor (agente/proveedor)
            emisor = contenido.get('emisor', {})
            nit_emisor = limpiar_nit(emisor.get('nit') or emisor.get('nrc', ''))
            nombre_emisor = emisor.get('nombre', 'Proveedor Desconocido')
            
            # Extraer datos del cuerpo/resumen
            cuerpo = contenido.get('resumen', {})
            cuerpo_doc = contenido.get('cuerpoDocumento', [])
            
            # Procesar según tipo de DTE
            if tipo_dte == '09':  # LIQUIDACIÓN
                # Extraer datos para Liquidacion
                monto_operacion = safe_float(cuerpo.get('totalSujetoPercepcion')) or safe_float(cuerpo.get('valorOperaciones', 0))
                iva_percibido_2 = safe_float(cuerpo.get('ivaPercibido', 0))
                
                # Calcular comisión y líquido (si no vienen en el JSON, calcular)
                comision = safe_float(cuerpo.get('comision', 0))
                liquido_pagar = safe_float(cuerpo.get('liquidoPagar', 0)) or (monto_operacion - iva_percibido_2 - comision)
                
                # Verificar si ya existe
                if Liquidacion.objects.filter(codigo_generacion=codigo).exists():
                    reporte["resumen"]["duplicados"] += 1
                    reporte["liquidaciones"].append({
                        "archivo": archivo.name,
                        "codigo": codigo,
                        "estado": "Duplicado"
                    })
                else:
                    # Crear o obtener agente (Cliente)
                    agente, _ = Cliente.objects.get_or_create(
                        nrc=nit_emisor if nit_emisor else f"AGENTE-{codigo[:8]}",
                        defaults={
                            'nombre': nombre_emisor,
                            'nit': nit_emisor or '',
                        }
                    )
                    
                    # Parsear fecha
                    from datetime import datetime
                    try:
                        fecha_doc = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    except:
                        fecha_doc = datetime.now().date()
                    
                    periodo = fecha_doc.strftime('%Y-%m')
                    
                    # Crear Liquidacion
                    liquidacion = Liquidacion.objects.create(
                        empresa=empresa,
                        fecha_documento=fecha_doc,
                        codigo_generacion=codigo,
                        sello_recibido=sello,
                        nit_agente=nit_emisor or agente.nrc,
                        nombre_agente=nombre_emisor,
                        monto_operacion=monto_operacion,
                        iva_percibido_2=iva_percibido_2,
                        comision=comision,
                        liquido_pagar=liquido_pagar,
                        periodo_aplicado=periodo
                    )
                    
                    reporte["liquidaciones"].append({
                        "archivo": archivo.name,
                        "codigo": codigo,
                        "fecha": fecha_str,
                        "agente": nombre_emisor,
                        "monto": float(monto_operacion),
                        "estado": "Guardado"
                    })
                    reporte["resumen"]["liquidaciones_guardadas"] += 1
                    
            elif tipo_dte == '07':  # RETENCIÓN RECIBIDA
                # Extraer datos para RetencionRecibida
                monto_sujeto = safe_float(cuerpo.get('totalSujetoRetencion', 0))
                monto_retenido_1 = safe_float(cuerpo.get('totalIVAretenido', 0))
                
                # Verificar si ya existe
                if RetencionRecibida.objects.filter(codigo_generacion=codigo).exists():
                    reporte["resumen"]["duplicados"] += 1
                    reporte["retenciones"].append({
                        "archivo": archivo.name,
                        "codigo": codigo,
                        "estado": "Duplicado"
                    })
                else:
                    # Crear o obtener agente
                    agente, _ = Cliente.objects.get_or_create(
                        nrc=nit_emisor if nit_emisor else f"AGENTE-{codigo[:8]}",
                        defaults={
                            'nombre': nombre_emisor,
                            'nit': nit_emisor or '',
                        }
                    )
                    
                    # Parsear fecha
                    from datetime import datetime
                    try:
                        fecha_doc = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    except:
                        fecha_doc = datetime.now().date()
                    
                    periodo = fecha_doc.strftime('%Y-%m')
                    
                    # Crear RetencionRecibida
                    retencion = RetencionRecibida.objects.create(
                        empresa=empresa,
                        fecha_documento=fecha_doc,
                        codigo_generacion=codigo,
                        sello_recibido=sello,
                        nit_agente=nit_emisor or agente.nrc,
                        nombre_agente=nombre_emisor,
                        monto_sujeto=monto_sujeto,
                        monto_retenido_1=monto_retenido_1,
                        estado='Pendiente',
                        periodo_aplicado=periodo
                    )
                    
                    reporte["retenciones"].append({
                        "archivo": archivo.name,
                        "codigo": codigo,
                        "fecha": fecha_str,
                        "agente": nombre_emisor,
                        "monto_sujeto": float(monto_sujeto),
                        "monto_retenido": float(monto_retenido_1),
                        "estado": "Guardado"
                    })
                    reporte["resumen"]["retenciones_guardadas"] += 1
                    
            elif tipo_dte in ['03', '14']:  # CCF / FACTURA (COMPRA)
                # Extraer datos para Compra
                gravado = safe_float(cuerpo.get('totalGravada', 0))
                iva = safe_float(cuerpo.get('totalIva', 0))
                total = safe_float(cuerpo.get('totalPagar', 0))
                percepcion = safe_float(cuerpo.get('totalIvaPercibido', 0))  # Percepción IVA
                
                # Si no viene IVA en resumen, calcular desde cuerpoDocumento
                if iva == 0 and cuerpo_doc:
                    for item in cuerpo_doc:
                        iva += safe_float(item.get('ivaItem', 0))
                
                # Verificar si ya existe
                if Compra.objects.filter(empresa=empresa, codigo_generacion=codigo).exists():
                    reporte["resumen"]["duplicados"] += 1
                    reporte["compras"].append({
                        "archivo": archivo.name,
                        "codigo": codigo,
                        "estado": "Duplicado"
                    })
                else:
                    # Crear o obtener proveedor
                    proveedor, _ = Cliente.objects.get_or_create(
                        nrc=nit_emisor if nit_emisor else f"PROV-{codigo[:8]}",
                        defaults={
                            'nombre': nombre_emisor,
                            'nit': nit_emisor or '',
                        }
                    )
                    
                    # Parsear fecha
                    from datetime import datetime
                    try:
                        fecha_doc = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    except:
                        fecha_doc = datetime.now().date()
                    
                    periodo = fecha_doc.strftime('%Y-%m')
                    
                    # Crear Compra
                    compra = Compra.objects.create(
                        empresa=empresa,
                        proveedor=proveedor,
                        fecha_emision=fecha_doc,
                        tipo_documento=tipo_dte,
                        codigo_generacion=codigo,
                        nrc_proveedor=nit_emisor or proveedor.nrc,
                        nombre_proveedor=nombre_emisor,
                        monto_gravado=gravado,
                        monto_iva=iva,
                        monto_percepcion=percepcion,  # Percepción IVA
                        monto_total=total,
                        periodo_aplicado=periodo,
                        estado="Registrado",
                        clasificacion_1="Gravada",
                        clasificacion_2="Gasto"
                    )
                    
                    reporte["compras"].append({
                        "archivo": archivo.name,
                        "codigo": codigo,
                        "fecha": fecha_str,
                        "proveedor": nombre_emisor,
                        "gravado": float(gravado),
                        "iva": float(iva),
                        "percepcion": float(percepcion),
                        "total": float(total),
                        "estado": "Guardado"
                    })
                    reporte["resumen"]["compras_guardadas"] += 1
            else:
                reporte["errores"].append({
                    "archivo": archivo.name,
                    "motivo": f"Tipo DTE no soportado: {tipo_dte}"
                })
                reporte["resumen"]["errores"] += 1
                
        except Exception as e:
            reporte["errores"].append({
                "archivo": archivo.name,
                "motivo": f"Error al procesar: {str(e)}"
            })
            reporte["resumen"]["errores"] += 1
    
    return Response(reporte, status=200)

# --- CRUD INDIVIDUAL ---
@api_view(['POST'])
def crear_compra(request):
    empresa_id = request.data.get('empresa_id')
    if empresa_id is not None:
        r = require_empresa_allowed(request, empresa_id)
        if r is not None:
            return r
    serializer = CompraSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
@api_view(['GET'])
def listar_compras(request):
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return Response({"error": "Autenticación requerida"}, status=status.HTTP_401_UNAUTHORIZED)
    empresa_id = request.query_params.get('empresa_id')
    if empresa_id:
        r = require_empresa_allowed(request, int(empresa_id))
        if r is not None:
            return r
        compras = Compra.objects.filter(empresa_id=empresa_id)
    else:
        compras = Compra.objects.filter(empresa_id__in=empresa_ids)
    nrc = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    if nrc:
        compras = compras.filter(proveedor__nrc=nrc)
    if periodo:
        compras = compras.filter(periodo_aplicado=periodo)
    compras = compras.order_by('fecha_emision')
    serializer = CompraSerializer(compras, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def obtener_compra(request, pk):
    """Obtiene una compra específica por ID para edición"""
    try:
        compra = Compra.objects.get(pk=pk)
    except Compra.DoesNotExist:
        return Response({"error": "Compra no encontrada"}, status=404)
    r = require_object_empresa_allowed(request, compra)
    if r is not None:
        return r
    serializer = CompraSerializer(compra)
    return Response(serializer.data)
@api_view(['DELETE'])
def borrar_compra(request, pk):
    try:
        compra = Compra.objects.get(pk=pk)
    except Compra.DoesNotExist:
        return Response(status=404)
    r = require_object_empresa_allowed(request, compra)
    if r is not None:
        return r
    compra.delete()
    return Response(status=204)
@api_view(['PUT'])
def actualizar_compra(request, pk):
    try:
        compra = Compra.objects.get(pk=pk)
    except Compra.DoesNotExist:
        return Response(status=404)
    r = require_object_empresa_allowed(request, compra)
    if r is not None:
        return r
    serializer = CompraSerializer(compra, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)
@api_view(['POST'])
def crear_venta(request):
    empresa_id = request.data.get('empresa_id')
    if empresa_id is not None:
        r = require_empresa_allowed(request, empresa_id)
        if r is not None:
            return r
    serializer = VentaSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

@api_view(['POST'])
def crear_venta_con_detalles(request):
    """Crea una venta con sus detalles y envía a Hacienda (síncrono o asíncrono según USE_ASYNC_FACTURACION)."""
    from django.conf import settings
    from .models import TareaFacturacion
    from .services.facturacion_service import FacturacionService, FacturacionServiceError

    # Validar tenant: empresa_id del body debe estar permitida para el usuario
    empresa_id = request.data.get('empresa_id')
    if empresa_id is not None:
        r = require_empresa_allowed(request, empresa_id)
        if r is not None:
            return r

    serializer = VentaConDetallesSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    venta = serializer.save()

    if getattr(settings, 'USE_ASYNC_FACTURACION', True):
        # Procesamiento asíncrono: encolar y responder de inmediato
        TareaFacturacion.objects.get_or_create(
            venta=venta,
            defaults={'estado': 'Pendiente'}
        )
        data = VentaSerializer(venta).data
        data['mensaje'] = 'Factura registrada. Se procesará en breve (firma, envío a Hacienda y correo).'
        data['procesamiento'] = 'asincrono'
        return Response(data, status=201)

    # Procesamiento síncrono (legacy)
    mensaje = None
    try:
        servicio = FacturacionService(venta.empresa)
        resultado = servicio.procesar_factura(venta)
        venta.refresh_from_db()
        if resultado.get('exito'):
            mensaje = 'Factura enviada a Hacienda correctamente.'
        else:
            mensaje = resultado.get('mensaje') or resultado.get('observaciones') or 'Rechazado por Hacienda'
    except FacturacionServiceError as e:
        venta.refresh_from_db()
        mensaje = str(e)
    except Exception as e:
        venta.refresh_from_db()
        mensaje = f'Error al procesar: {str(e)}'

    data = VentaSerializer(venta).data
    data['mensaje'] = mensaje
    data['procesamiento'] = 'sincrono'
    return Response(data, status=201)

@api_view(['GET'])
def listar_productos(request):
    """Lista/busca productos de la empresa. GET: empresa_id (opcional; si no se envía y el usuario tiene una sola empresa, se usa esa), q (búsqueda)."""
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return Response({"detail": "Autenticación requerida"}, status=status.HTTP_401_UNAUTHORIZED)
    empresa_id = request.query_params.get('empresa_id')
    if empresa_id:
        r = require_empresa_allowed(request, int(empresa_id))
        if r is not None:
            return r
        productos = Producto.objects.filter(empresa_id=empresa_id)
    else:
        productos = Producto.objects.filter(empresa_id__in=empresa_ids)
        if len(empresa_ids) == 1:
            productos = productos.filter(empresa_id=empresa_ids[0])
    productos = productos.filter(activo=True)
    q = (request.query_params.get('q') or '').strip()
    if q:
        productos = productos.filter(
            Q(descripcion__icontains=q) | Q(codigo__icontains=q)
        )
    productos = productos.order_by('descripcion')
    serializer = ProductoSerializer(productos, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def crear_producto(request):
    """Crea un producto/ítem para la empresa. Asigna empresa_id explícitamente como owner."""
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return Response({"detail": "Autenticación requerida"}, status=status.HTTP_401_UNAUTHORIZED)
    raw_empresa = request.data.get('empresa_id')
    if raw_empresa is None or raw_empresa == '':
        return Response({"detail": "empresa_id es requerido"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        empresa_id = int(raw_empresa)
    except (TypeError, ValueError):
        return Response({"detail": "empresa_id debe ser un número"}, status=status.HTTP_400_BAD_REQUEST)
    r = require_empresa_allowed(request, empresa_id)
    if r is not None:
        return r
    data = dict(request.data)
    data['empresa_id'] = empresa_id
    if data.get('codigo') is None:
        data['codigo'] = ''
    serializer = ProductoSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save(empresa_id=empresa_id)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def producto_detalle(request, pk):
    """Obtiene, actualiza o elimina un producto (soft-delete: activo=False)."""
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return Response({"detail": "Autenticación requerida"}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        producto = Producto.objects.get(pk=pk)
    except Producto.DoesNotExist:
        return Response({"detail": "Producto no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    if producto.empresa_id not in empresa_ids:
        return Response({"detail": "No tiene permiso para este producto"}, status=status.HTTP_403_FORBIDDEN)
    if request.method == 'GET':
        serializer = ProductoSerializer(producto)
        return Response(serializer.data)
    if request.method == 'DELETE':
        producto.activo = False
        producto.save(update_fields=['activo'])
        return Response(status=status.HTTP_204_NO_CONTENT)
    if request.method in ('PUT', 'PATCH'):
        serializer = ProductoSerializer(producto, data=request.data, partial=(request.method == 'PATCH'))
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['GET'])
def listar_ventas(request):
    """Lista ventas con filtros opcionales.
    Parámetros GET: empresa_id, nrc, periodo, tipo, fecha_inicio, fecha_fin, search, tipo_dte
    Multi-tenant: solo se listan ventas de empresas permitidas para el usuario.
    """
    from django.db.models import Q
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return Response({"error": "Autenticación requerida"}, status=status.HTTP_401_UNAUTHORIZED)
    empresa_id = request.query_params.get('empresa_id')
    nrc = request.query_params.get('nrc')
    if empresa_id:
        r = require_empresa_allowed(request, empresa_id)
        if r is not None:
            return r
    periodo = request.query_params.get('periodo')
    tipo = request.query_params.get('tipo')
    fecha_inicio = request.query_params.get('fecha_inicio')
    fecha_fin = request.query_params.get('fecha_fin')
    search = request.query_params.get('search', '').strip()
    tipo_dte = request.query_params.get('tipo_dte')
    
    ventas = Venta.objects.select_related('empresa', 'cliente').filter(empresa_id__in=empresa_ids)
    if empresa_id:
        ventas = ventas.filter(empresa_id=int(empresa_id))
    elif nrc:
        ventas = ventas.filter(empresa__nrc=nrc)
    
    if periodo:
        ventas = ventas.filter(periodo_aplicado=periodo)
    
    if tipo:
        ventas = ventas.filter(tipo_venta=tipo)
    
    if fecha_inicio:
        ventas = ventas.filter(fecha_emision__gte=fecha_inicio)
    if fecha_fin:
        ventas = ventas.filter(fecha_emision__lte=fecha_fin)
    
    if tipo_dte == '01':
        ventas = ventas.filter(tipo_venta='CF')
    elif tipo_dte == '03':
        ventas = ventas.filter(tipo_venta='CCF')
    
    if search:
        ventas = ventas.filter(
            Q(numero_control__icontains=search) |
            Q(codigo_generacion__icontains=search) |
            Q(cliente__nombre__icontains=search) |
            Q(nombre_receptor__icontains=search)
        )
    
    solo_procesadas = request.query_params.get('solo_procesadas')
    if solo_procesadas:
        ventas = ventas.filter(sello_recepcion__isnull=False).exclude(sello_recepcion='')
    
    ventas = ventas.order_by('-fecha_emision', '-id')
    serializer = VentaSerializer(ventas, many=True, context={'request': request})
    return Response(serializer.data)


def _aplicar_filtros_ventas(queryset, request):
    """Aplica los mismos filtros que listar_ventas (para reutilizar en download_batch)."""
    empresa_id = request.GET.get('empresa_id')
    nrc = request.GET.get('nrc')
    periodo = request.GET.get('periodo')
    tipo = request.GET.get('tipo')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    search = request.GET.get('search', '').strip()
    tipo_dte = request.GET.get('tipo_dte')

    if empresa_id:
        queryset = queryset.filter(empresa_id=empresa_id)
    elif nrc:
        queryset = queryset.filter(empresa__nrc=nrc)
    if periodo:
        queryset = queryset.filter(periodo_aplicado=periodo)
    if tipo:
        queryset = queryset.filter(tipo_venta=tipo)
    if fecha_inicio:
        queryset = queryset.filter(fecha_emision__gte=fecha_inicio)
    if fecha_fin:
        queryset = queryset.filter(fecha_emision__lte=fecha_fin)
    if tipo_dte == '01':
        queryset = queryset.filter(tipo_venta='CF')
    elif tipo_dte == '03':
        queryset = queryset.filter(tipo_venta='CCF')
    if search:
        queryset = queryset.filter(
            Q(numero_control__icontains=search) |
            Q(cliente__nombre__icontains=search) |
            Q(nombre_receptor__icontains=search)
        )
    return queryset.order_by('-fecha_emision', '-id')


@api_view(['GET'])
def download_batch_ventas(request):
    """
    Descarga PDFs o JSONs de ventas en un archivo ZIP.
    Acepta los mismos filtros que listar: fecha_inicio, fecha_fin, search, tipo_dte, empresa_id.
    GET ?format=pdf|json

    Genera archivos dinámicamente (no usa rutas de disco). Si un documento falla,
    agrega error_factura_X.txt en lugar de romper el ciclo.
    """
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return JsonResponse({'error': 'Autenticación requerida'}, status=401)
    empresa_id = request.GET.get('empresa_id')
    if empresa_id:
        r = require_empresa_allowed(request, int(empresa_id))
        if r is not None:
            return r
        empresa_ids = [int(empresa_id)]

    format_type = (request.GET.get('format') or 'pdf').lower()
    if format_type not in ('pdf', 'json'):
        return JsonResponse({'error': 'format debe ser pdf o json'}, status=400)

    ventas_qs = Venta.objects.filter(empresa_id__in=empresa_ids).select_related('empresa', 'cliente').prefetch_related('detalles__producto')
    ventas_qs = _aplicar_filtros_ventas(ventas_qs, request)
    ventas = list(ventas_qs[:100])  # Límite razonable

    if not ventas:
        return JsonResponse({'error': 'No hay ventas que coincidan con los filtros'}, status=400)

    buffer = io.BytesIO()
    ext = 'pdf' if format_type == 'pdf' else 'json'

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for v in ventas:
            nombre_base = v.numero_control or f"venta_{v.id}"
            nombre_safe = "".join(c if c.isalnum() or c in '-_' else '_' for c in str(nombre_base))
            nombre_archivo = f"{nombre_safe}.{ext}"

            try:
                # Caso A: Archivo físico (si Venta tiene archivo_pdf FileField)
                if hasattr(v, 'archivo_pdf') and v.archivo_pdf:
                    import os
                    path_fisico = v.archivo_pdf.path
                    if os.path.exists(path_fisico):
                        with open(path_fisico, 'rb') as f:
                            zf.writestr(nombre_archivo, f.read())
                    else:
                        raise FileNotFoundError(f"Archivo no encontrado: {path_fisico}")
                else:
                    # Caso B: Generación dinámica (actual - PDF/JSON en memoria)
                    if format_type == 'pdf':
                        pdf_buffer = generar_pdf_venta(v)
                        pdf_bytes = pdf_buffer.getvalue() if hasattr(pdf_buffer, 'getvalue') else pdf_buffer.read()
                        zf.writestr(nombre_archivo, pdf_bytes)
                    else:
                        gen = DTEGenerator(v)
                        ambiente = request.GET.get('ambiente', '01')
                        dte_json = gen.generar_json(ambiente=ambiente)
                        json_bytes = json.dumps(dte_json, indent=2, ensure_ascii=False).encode('utf-8')
                        zf.writestr(nombre_archivo, json_bytes)
            except Exception as e:
                logger.warning(f"Error generando {ext} para venta {v.id}: {e}")
                msg_error = f"No se pudo generar este documento.\nVenta ID: {v.id}\nError: {str(e)}"
                zf.writestr(f"error_factura_{v.id}.txt", msg_error.encode('utf-8'))

    buffer.seek(0)
    resp = HttpResponse(buffer.getvalue(), content_type='application/zip')
    resp['Content-Disposition'] = 'attachment; filename="facturas.zip"'
    return resp


@api_view(['GET'])
def obtener_venta(request, pk):
    """Obtiene una venta específica por ID para edición. Multi-tenant: solo si pertenece a empresa permitida."""
    try:
        venta = Venta.objects.get(pk=pk)
    except Venta.DoesNotExist:
        return Response({"error": "Venta no encontrada"}, status=404)
    r = require_object_empresa_allowed(request, venta)
    if r is not None:
        return r
    serializer = VentaSerializer(venta)
    return Response(serializer.data)

def generar_pdf_venta_endpoint(request, pk):
    """
    Genera y retorna el PDF de una factura individual.
    NO usa @api_view para evitar negociación de contenido de DRF.
    Devuelve HttpResponse directamente para PDFs binarios.
    """
    try:
        venta = Venta.objects.select_related('empresa', 'cliente').prefetch_related('detalles__producto').get(pk=pk)
        
        # Generar el PDF
        buffer = generar_pdf_venta(venta)
        
        # Leer el contenido del buffer
        pdf_content = buffer.getvalue()
        
        # Crear la respuesta HTTP con el PDF (sin pasar por DRF)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="factura_{venta.numero_control or venta.id}.pdf"'
        response['Content-Length'] = len(pdf_content)
        
        return response
    except Venta.DoesNotExist:
        # Para errores, devolver JSON usando JsonResponse de Django
        return JsonResponse({'error': 'Venta no encontrada'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generando PDF para venta {pk}: {str(e)}")
        return JsonResponse({'error': f'Error al generar PDF: {str(e)}'}, status=500)

@api_view(['GET'])
def generar_dte_venta(request, pk):
    """
    Genera el archivo JSON DTE a partir de una venta.
    Endpoint: GET /api/ventas/{id}/generar-dte/
    """
    try:
        venta = Venta.objects.get(pk=pk)
    except Venta.DoesNotExist:
        return Response({"error": "Venta no encontrada"}, status=404)
    
    # Verificar que la venta tenga empresa asociada
    if not venta.empresa:
        return Response({"error": "La venta debe tener una empresa asociada para generar el DTE"}, status=400)
    
    try:
        # Crear generador de DTE
        generator = DTEGenerator(venta)
        
        # Obtener ambiente desde query params (default: pruebas)
        ambiente = request.query_params.get('ambiente', '01')  # '00' = Producción, '01' = Pruebas
        
        # Generar el JSON
        dte_json = generator.generar_json(ambiente=ambiente)
        
        # Guardar código y número de control en la venta si se generaron
        if generator.venta.codigo_generacion and not venta.codigo_generacion:
            venta.codigo_generacion = generator.venta.codigo_generacion
        if generator.venta.numero_control and not venta.numero_control:
            venta.numero_control = generator.venta.numero_control
        venta.save()
        
        return Response({
            "venta_id": venta.id,
            "numero_control": venta.numero_control,
            "codigo_generacion": venta.codigo_generacion,
            "dte_json": dte_json,
            "mensaje": "DTE generado correctamente"
        }, status=200)
        
    except Exception as e:
        return Response({
            "error": f"Error al generar DTE: {str(e)}"
        }, status=500)
@api_view(['DELETE'])
def borrar_venta(request, pk):
    try: Venta.objects.get(pk=pk).delete(); return Response(status=204)
    except: return Response(status=404)

@api_view(['PUT'])
def actualizar_venta(request, pk):
    """Actualiza una venta existente"""
    try:
        venta = Venta.objects.get(pk=pk)
    except Venta.DoesNotExist:
        return Response({"error": "Venta no encontrada"}, status=404)
    
    serializer = VentaSerializer(venta, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)
@api_view(['POST'])
def crear_retencion(request):
    serializer = RetencionSerializer(data=request.data)
    if serializer.is_valid(): serializer.save(); return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
@api_view(['GET'])
def listar_retenciones(request):
    cliente_id = request.query_params.get('nrc'); periodo = request.query_params.get('periodo')
    rets = Retencion.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo).order_by('fecha_emision')
    serializer = RetencionSerializer(rets, many=True); return Response(serializer.data)

# --- LIQUIDACIONES ---
@api_view(['GET'])
def listar_liquidaciones(request):
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return Response({"error": "Autenticación requerida"}, status=status.HTTP_401_UNAUTHORIZED)
    empresa_id = request.query_params.get('empresa_id')
    if empresa_id:
        r = require_empresa_allowed(request, int(empresa_id))
        if r is not None:
            return r
        liquidaciones = Liquidacion.objects.filter(empresa_id=empresa_id)
    else:
        liquidaciones = Liquidacion.objects.filter(empresa_id__in=empresa_ids)
    periodo = request.query_params.get('periodo')
    if periodo:
        liquidaciones = liquidaciones.filter(periodo_aplicado=periodo)
    liquidaciones = liquidaciones.order_by('-fecha_documento')
    serializer = LiquidacionSerializer(liquidaciones, many=True)
    return Response(serializer.data)

# --- RETENCIONES RECIBIDAS ---
@api_view(['GET'])
def listar_retenciones_recibidas(request):
    empresa_ids = get_empresa_ids_allowlist(request)
    if not empresa_ids:
        return Response({"error": "Autenticación requerida"}, status=status.HTTP_401_UNAUTHORIZED)
    empresa_id = request.query_params.get('empresa_id')
    if empresa_id:
        r = require_empresa_allowed(request, int(empresa_id))
        if r is not None:
            return r
        retenciones = RetencionRecibida.objects.filter(empresa_id=empresa_id)
    else:
        retenciones = RetencionRecibida.objects.filter(empresa_id__in=empresa_ids)
    periodo = request.query_params.get('periodo')
    estado = request.query_params.get('estado')
    if periodo:
        retenciones = retenciones.filter(periodo_aplicado=periodo)
    if estado:
        retenciones = retenciones.filter(estado=estado)
    
    retenciones = retenciones.order_by('-fecha_documento')
    serializer = RetencionRecibidaSerializer(retenciones, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def obtener_retencion_recibida(request, pk):
    """Obtiene una retención recibida específica por ID"""
    try:
        retencion = RetencionRecibida.objects.get(pk=pk)
    except RetencionRecibida.DoesNotExist:
        return Response({"error": "Retención no encontrada"}, status=404)
    r = require_object_empresa_allowed(request, retencion)
    if r is not None:
        return r
    serializer = RetencionRecibidaSerializer(retencion)
    return Response(serializer.data)

@api_view(['PUT'])
def aplicar_retencion(request, pk):
    """
    Aplica una retención recibida a ventas seleccionadas.
    Recibe: { "ventas_ids": [1, 2, 3], "justificacion": "..." }
    """
    try:
        retencion = RetencionRecibida.objects.get(pk=pk)
    except RetencionRecibida.DoesNotExist:
        return Response({"error": "Retención no encontrada"}, status=404)
    r = require_object_empresa_allowed(request, retencion)
    if r is not None:
        return r
    if retencion.estado == 'Aplicada':
        return Response({"error": "Esta retención ya fue aplicada"}, status=400)
    
    ventas_ids = request.data.get('ventas_ids', [])
    justificacion = request.data.get('justificacion', '')
    
    if not ventas_ids:
        return Response({"error": "Debes seleccionar al menos una venta"}, status=400)
    
    # Obtener ventas
    try:
        ventas = Venta.objects.filter(id__in=ventas_ids, empresa=retencion.empresa)
    except:
        return Response({"error": "Error al obtener ventas"}, status=400)
    
    # Validar: Suma(Ventas seleccionadas * 1%) <= Monto Retención Disponible
    suma_retencion_ventas = sum(float(v.venta_gravada) * 0.01 for v in ventas)
    monto_disponible = float(retencion.monto_retenido_1)
    
    diferencia = suma_retencion_ventas - monto_disponible
    
    if diferencia > 0.01:  # Tolerancia de centavos
        if not justificacion:
            return Response({
                "error": "La suma de retenciones de las ventas excede el monto disponible",
                "suma_ventas": suma_retencion_ventas,
                "monto_disponible": monto_disponible,
                "diferencia": diferencia,
                "requiere_justificacion": True
            }, status=400)
    
    # Aplicar retención
    retencion.ventas_aplicadas.set(ventas)
    retencion.estado = 'Aplicada'
    retencion.save()
    
    serializer = RetencionRecibidaSerializer(retencion)
    return Response({
        "mensaje": "Retención aplicada correctamente",
        "retencion": serializer.data
    })

# --- FINANZAS ---
@api_view(['GET'])
def resumen_fiscal(request):
    cliente_id = request.query_params.get('nrc'); periodo = request.query_params.get('periodo')
    compras = Compra.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo)
    s_comp = compras.aggregate(Sum('monto_gravado'))['monto_gravado__sum'] or 0
    s_cred = compras.aggregate(Sum('monto_iva'))['monto_iva__sum'] or 0
    s_perc = compras.aggregate(Sum('monto_percepcion'))['monto_percepcion__sum'] or 0 # <--- PERCEPCIÓN SUMADA
    ventas = Venta.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo)
    s_vent = ventas.aggregate(Sum('venta_gravada'))['venta_gravada__sum'] or 0
    s_deb = ventas.aggregate(Sum('debito_fiscal'))['debito_fiscal__sum'] or 0
    rets = Retencion.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo)
    s_ret1 = rets.filter(tipo_retencion='162').aggregate(Sum('monto_retenido'))['monto_retenido__sum'] or 0
    s_ret2 = rets.filter(tipo_retencion='161').aggregate(Sum('monto_retenido'))['monto_retenido__sum'] or 0
    return Response({ "ventasGravadas": s_vent, "debitoFiscal": s_deb, "comprasGravadas": s_comp, "creditoFiscal": s_cred, "percepcionesPagadas": s_perc, "retencionCliente1": s_ret1, "retencionTarjeta2": s_ret2 })

# --- CSV ---
@api_view(['GET'])
def generar_csv_163(request):
    cliente_id = request.query_params.get('nrc'); periodo = request.query_params.get('periodo')
    response = HttpResponse(content_type='text/csv'); response['Content-Disposition'] = f'attachment; filename="ANEXO_163_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    compras = Compra.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo, monto_percepcion__gt=0)
    for c in compras:
        fecha = c.fecha_emision.strftime("%d/%m/%Y")
        fila = ["", fecha, c.codigo_generacion, "SERIE", format(c.monto_gravado+c.monto_iva, '.2f'), format(c.monto_percepcion, '.2f'), "0.00", "10"]
        writer.writerow(fila)
    return response

# ==========================================
# 7. REPORTES CSV (FÁBRICA DE ANEXOS MH)
# ==========================================

@api_view(['GET'])
def generar_csv_compras(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="COMPRAS_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    compras = Compra.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo).order_by('fecha_emision')
    map_clasif_1 = {"Gravada": "1", "Exenta": "2", "No Sujeta": "3"}
    map_clasif_2 = {"Costo": "1", "Gasto": "2"}
    map_clasif_3 = { "Industria": "1", "Comercio": "2", "Servicios": "3", "Agropecuario": "4", "Administración": "1", "Ventas": "2", "Financiero": "3" }

    for c in compras:
        fecha_fmt = c.fecha_emision.strftime("%d/%m/%Y")
        clase_doc = "4" if c.codigo_generacion and len(str(c.codigo_generacion)) > 20 else "1"
        tipo_doc = c.tipo_documento.zfill(2)
        nombre_limpio = c.nombre_proveedor.replace(";", "") if c.nombre_proveedor else ""
        es_importacion = c.tipo_documento == '12'
        col_9_internas = format(c.monto_gravado, '.2f') if not es_importacion else "0.00"
        col_8_import = format(c.monto_gravado, '.2f') if es_importacion else "0.00"
        cod_1 = map_clasif_1.get(c.clasificacion_1, "1")
        cod_2 = map_clasif_2.get(c.clasificacion_2, "1")
        cod_3 = map_clasif_3.get(c.clasificacion_3, "1")
        
        fila = [
            fecha_fmt, clase_doc, tipo_doc, c.codigo_generacion, c.nrc_proveedor, nombre_limpio,
            "0.00", "0.00", col_8_import, col_9_internas, "0.00", "0.00", "0.00",
            format(c.monto_iva, '.2f'), format(c.monto_total, '.2f'), "", cod_1, cod_2, cod_3, "5", "3"
        ]
        writer.writerow(fila)
    return response

@api_view(['GET'])
def generar_csv_ventas_ccf(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="VENTAS_CCF_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    ventas = Venta.objects.filter(cliente__nrc=cliente_id, periodo_aplicado=periodo, tipo_venta='CCF').order_by('fecha_emision')

    for v in ventas:
        fecha_fmt = v.fecha_emision.strftime("%d/%m/%Y")
        clase_doc = v.clase_documento
        tipo_doc = "03"
        resolucion = v.numero_resolucion if clase_doc != '4' else ""
        serie = v.serie_documento if clase_doc != '4' else ""
        num_prin = v.numero_documento.strip()
        num_sec = v.numero_formulario_unico.strip() if (clase_doc == '2' and v.numero_formulario_unico) else num_prin
        nombre_limpio = v.nombre_receptor.replace(";", "") if v.nombre_receptor else ""
        
        monto_exento = "0.00"
        monto_gravado = "0.00"
        monto_nosujeto = "0.00"
        base = v.venta_gravada
        
        if v.clasificacion_venta == "2": monto_exento = format(base, '.2f')
        elif v.clasificacion_venta == "3": monto_nosujeto = format(base, '.2f')
        else: monto_gravado = format(base, '.2f')

        fila = [
            fecha_fmt, clase_doc, tipo_doc, resolucion, serie, num_prin, num_sec,
            v.nrc_receptor, nombre_limpio, monto_exento, "0.00", monto_gravado, 
            format(v.debito_fiscal, '.2f'), monto_nosujeto, "0.00", format(v.venta_gravada + v.debito_fiscal, '.2f'),
            "", v.clasificacion_venta.zfill(2), v.tipo_ingreso.zfill(2), "1"
        ]
        writer.writerow(fila)
    return response

# 9. Generar CSV Ventas Consumidor Final (Anexo 2) - ¡MEJORADO!
# 9. Generar CSV Ventas Consumidor Final (Anexo 2) - ¡VERSIÓN FINAL CORREGIDA MH!
@api_view(['GET'])
def generar_csv_ventas_cf(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    
    response = HttpResponse(content_type='text/csv')
    nombre_archivo = f"VENTAS_CF_{periodo}.csv"
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'

    writer = csv.writer(response, delimiter=';')

    ventas = Venta.objects.filter(
        cliente__nrc=cliente_id, 
        periodo_aplicado=periodo,
        tipo_venta='CF'
    ).order_by('fecha_emision') # O por numero_control si prefieres

    for v in ventas:
        fecha_fmt = v.fecha_emision.strftime("%d/%m/%Y")
        clase_doc = v.clase_documento
        
        # 1. LIMPIEZA DE DATOS (Quitar guiones)
        cod_gen_limpio = str(v.codigo_generacion or "").replace("-", "").upper()
        num_ctrl_limpio = str(v.numero_control or "").replace("-", "").upper()
        sello_limpio = str(v.sello_recepcion or "").replace("-", "").upper()

        # 2. ASIGNACIÓN DE COLUMNAS SEGÚN CLASE
        # Si es DTE (4)
        if clase_doc == '4':
            tipo_doc_mh = "01"   # Col 2: MH usa '01' para Factura Electrónica en este anexo
            col_3_res = num_ctrl_limpio  # Col 3: Número de Control
            col_4_ser = sello_limpio     # Col 4: Sello
            
            # Col 5, 6, 7, 8: Código de Generación repetido
            col_5_ci_del = cod_gen_limpio
            col_6_ci_al = cod_gen_limpio
            col_7_del = cod_gen_limpio
            col_8_al = cod_gen_limpio
            
            col_9_maq = "" # Col 9: Vacío para DTE
            
        else: 
            # Si es Físico (1, 2, 3)
            tipo_doc_mh = "01" # O "10" para Tiquete, "2" para Factura física
            col_3_res = v.numero_resolucion or ""
            col_4_ser = v.serie_documento or ""
            col_5_ci_del = ""
            col_6_ci_al = ""
            col_7_del = v.numero_control_desde or v.numero_documento
            col_8_al = v.numero_control_hasta or v.numero_documento
            col_9_maq = "" # O número de máquina si es ticket

        # 3. MONTOS
        monto_exento = "0.00"
        monto_gravado = "0.00"
        
        # Para CF, el monto reportado suele ser el TOTAL de la venta (con IVA) o la Base.
        # En tu archivo correcto (64.0) parece ser la Venta Total.
        # Si tu base de datos tiene 'venta_gravada' como base, sumamos IVA.
        
        total_venta_dia = v.venta_gravada + v.debito_fiscal
        
        if v.clasificacion_venta == "2": # Exenta
             monto_exento = format(total_venta_dia, '.2f')
        else:
             # Si es gravada, en este anexo MH suele pedir el valor de la venta
             monto_gravado = format(v.venta_gravada, '.2f') # Probemos con la Base
             # Si MH rechaza, cambia esta línea por: format(total_venta_dia, '.2f')

        total_fmt = format(total_venta_dia, '.2f')

        # --- FILA DE 23 COLUMNAS (0 a 22) ---
        fila = [
            fecha_fmt,          # 0. Fecha
            clase_doc,          # 1. Clase (4)
            tipo_doc_mh,        # 2. Tipo (1)
            col_3_res,          # 3. Resolución / Num Control
            col_4_ser,          # 4. Serie / Sello
            col_5_ci_del,       # 5. Control Interno Del (CodGen)
            col_6_ci_al,        # 6. Control Interno Al (CodGen)
            col_7_del,          # 7. Del Numero (CodGen)
            col_8_al,           # 8. Al Numero (CodGen)
            col_9_maq,          # 9. Maquina
            monto_exento,       # 10. Exentas
            "0.00",             # 11. Int. Exentas No Sujetas
            "0.00",             # 12. No Sujetas
            monto_gravado,      # 13. Gravadas
            "0.00",             # 14. Exp Centroamérica
            "0.00",             # 15. Exp Fuera
            "0.00",             # 16. Exp Servicios
            "0.00",             # 17. Zonas Francas
            "0.00",             # 18. Terceros
            total_fmt,          # 19. Total
            v.clasificacion_venta, # 20. Tipo Op (1) - Sin ceros extra si tu ejemplo tiene 1
            v.tipo_ingreso,        # 21. Tipo Ing (2 o 3) - Sin ceros extra
            "2"                    # 22. Tipo Anexo
        ]
        writer.writerow(fila)

    return response

@api_view(['GET'])
def generar_csv_161(request):
    """
    CSV 161: Liquidaciones (DTE-09)
    Formato: NIT;Fecha;Sello;CodGen;MontoOp;Retencion2%;[Vacio];6
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return HttpResponse("Falta periodo", status=400)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ANEXO_161_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    
    liquidaciones = Liquidacion.objects.filter(empresa=empresa, periodo_aplicado=periodo).order_by('fecha_documento')
    
    for liq in liquidaciones:
        fecha_fmt = liq.fecha_documento.strftime("%d/%m/%Y")
        nit_limpio = limpiar_nit(liq.nit_agente)
        sello_limpio = (liq.sello_recibido or "").replace("-", "").replace(" ", "")
        cod_gen_limpio = (liq.codigo_generacion or "").replace("-", "").replace(" ", "")
        
        # Formato: NIT;Fecha;Sello;CodGen;MontoOp;Retencion2%;[Vacio];6
        fila = [
            nit_limpio,
            fecha_fmt,
            sello_limpio,
            cod_gen_limpio,
            format(liq.monto_operacion, '.2f'),
            format(liq.iva_percibido_2, '.2f'),  # Retención 2% (anticipo IVA)
            "",  # Vacío
            "6"  # Tipo anexo
        ]
        writer.writerow(fila)
    
    return response

@api_view(['GET'])
def generar_csv_162(request):
    """
    CSV 162: Retenciones Recibidas (DTE-07)
    Formato: NIT;Fecha;07;Sello;CodGen;MontoSujeto;Retencion1%;[Vacio];7
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return HttpResponse("Falta periodo", status=400)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ANEXO_162_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    
    retenciones = RetencionRecibida.objects.filter(empresa=empresa, periodo_aplicado=periodo).order_by('fecha_documento')
    
    for ret in retenciones:
        fecha_fmt = ret.fecha_documento.strftime("%d/%m/%Y")
        nit_limpio = limpiar_nit(ret.nit_agente)
        sello_limpio = (ret.sello_recibido or "").replace("-", "").replace(" ", "")
        cod_gen_limpio = (ret.codigo_generacion or "").replace("-", "").replace(" ", "")
        
        # Formato: NIT;Fecha;07;Sello;CodGen;MontoSujeto;Retencion1%;[Vacio];7
        fila = [
            nit_limpio,
            fecha_fmt,
            "07",  # Tipo documento
            sello_limpio,
            cod_gen_limpio,
            format(ret.monto_sujeto, '.2f'),
            format(ret.monto_retenido_1, '.2f'),  # Retención 1%
            "",  # Vacío
            "7"  # Tipo anexo
        ]
        writer.writerow(fila)
    
    return response

# 10. PDF COMPRAS (CARTA / LETTER) - ¡ACTUALIZADO!
@api_view(['GET'])
def generar_pdf_compras(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    
    # CAMBIO 1: Importamos 'letter' en vez de 'legal'
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib import colors
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_COMPRAS_{periodo}.pdf"'

    try:
        cliente = Cliente.objects.get(nrc=cliente_id)
        compras = Compra.objects.filter(cliente=cliente, periodo_aplicado=periodo).order_by('fecha_emision')
    except Cliente.DoesNotExist:
        return HttpResponse("Cliente no encontrado", status=404)

    # CAMBIO 2: Usamos 'pagesize=landscape(letter)'
    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=15, leftMargin=15, topMargin=30, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    # Encabezado
    estilo_titulo = ParagraphStyle(name='Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=14, spaceAfter=2)
    estilo_sub = ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)

    elements.append(Paragraph("LIBRO DE COMPRAS", estilo_titulo))
    elements.append(Paragraph(f"CONTRIBUYENTE: {cliente.nombre}", estilo_sub))
    elements.append(Paragraph(f"NRC: {cliente.nrc}  |  NIT: {cliente.nit}", estilo_sub))
    elements.append(Paragraph(f"PERÍODO: {periodo}  |  MONEDA: USD", estilo_sub))
    elements.append(Spacer(1, 10))

    # Tabla
    # Ajusté ligeramente los anchos para asegurar que quepan en Carta (Total aprox 750 pts)
    col_widths = [30, 55, 160, 50, 140, 50, 50, 50, 45, 55, 45, 45]
    headers = ['No.', 'FECHA', 'Nº COMPROBANTE / DTE', 'NRC', 'PROVEEDOR', 'EXENTAS', 'GRAV. LOC', 'GRAV. IMP', 'IVA', 'TOTAL', 'RET 1%', 'RET 13%']
    data = [headers]

    t_exenta = 0; t_grav_loc = 0; t_grav_imp = 0; t_iva = 0; t_total = 0; t_ret1 = 0; t_ret13 = 0
    correlativo = 1
    
    estilo_celda = ParagraphStyle(name='Celda', fontSize=7, leading=8, alignment=TA_LEFT)
    estilo_celda_num = ParagraphStyle(name='CeldaNum', fontSize=7, leading=8, alignment=TA_RIGHT)

    for c in compras:
        es_importacion = c.tipo_documento == '12'
        exenta = 0.00
        grav_loc = float(c.monto_gravado) if not es_importacion else 0.00
        grav_imp = float(c.monto_gravado) if es_importacion else 0.00
        iva = float(c.monto_iva)
        total = float(c.monto_total)
        ret1 = 0.00 
        ret13 = 0.00

        t_exenta += exenta; t_grav_loc += grav_loc; t_grav_imp += grav_imp
        t_iva += iva; t_total += total; t_ret1 += ret1; t_ret13 += ret13

        fila = [
            str(correlativo),
            c.fecha_emision.strftime("%d/%m/%Y"),
            Paragraph(c.codigo_generacion or "", estilo_celda),
            c.nrc_proveedor,
            Paragraph(c.nombre_proveedor, estilo_celda),
            Paragraph(f"{exenta:,.2f}", estilo_celda_num),
            Paragraph(f"{grav_loc:,.2f}", estilo_celda_num),
            Paragraph(f"{grav_imp:,.2f}", estilo_celda_num),
            Paragraph(f"{iva:,.2f}", estilo_celda_num),
            Paragraph(f"{total:,.2f}", estilo_celda_num),
            Paragraph(f"{ret1:,.2f}", estilo_celda_num),
            Paragraph(f"{ret13:,.2f}", estilo_celda_num),
        ]
        data.append(fila)
        correlativo += 1

    data.append(['', '', 'TOTALES:', '', '', f"${t_exenta:,.2f}", f"${t_grav_loc:,.2f}", f"${t_grav_imp:,.2f}", f"${t_iva:,.2f}", f"${t_total:,.2f}", f"${t_ret1:,.2f}", f"${t_ret13:,.2f}"])

    tabla = Table(data, colWidths=col_widths, repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
    ]))
    elements.append(tabla)

    elements.append(Spacer(1, 50))
    data_firmas = [['_________________________', '_________________________'], ['F. CONTADOR', 'F. REPRESENTANTE LEGAL']]
    tabla_firmas = Table(data_firmas, colWidths=[250, 250]) # Ajustado para Carta
    tabla_firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(tabla_firmas)

    doc.build(elements)
    return response
# 11. PDF VENTAS CONSUMIDOR FINAL (CARTA) -

@api_view(['GET'])
def generar_pdf_ventas_cf(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib import colors
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_VENTAS_CF_{periodo}.pdf"'

    try:
        cliente = Cliente.objects.get(nrc=cliente_id)
        ventas = Venta.objects.filter(cliente=cliente, periodo_aplicado=periodo, tipo_venta='CF').order_by('fecha_emision', 'numero_control')
    except Cliente.DoesNotExist:
        return HttpResponse("Cliente no encontrado", status=404)

    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(name='Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=12, spaceAfter=2)
    estilo_sub = ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)

    elements.append(Paragraph("LIBRO DE VENTAS A CONSUMIDOR FINAL", estilo_titulo))
    elements.append(Paragraph(f"{cliente.nombre}", estilo_sub))
    elements.append(Paragraph(f"Periodo del: {periodo} | DUI:{cliente.dui} NRC: {cliente.nrc}", estilo_sub))
    elements.append(Paragraph("(Cifras Expresadas en Dolares de los Estados Unidos de America)", estilo_sub))
    elements.append(Spacer(1, 15))

    resumen_diario = {}
    
    for v in ventas:
        fecha = v.fecha_emision.strftime("%d/%m/%Y")
        
        # --- CORRECCIÓN CRÍTICA "NONE" ---
        if v.clase_documento == '4': # DTE
            # Buscamos el Código Generación. Si está vacío, usamos numero_documento. Si ambos fallan, string vacío.
            # IMPORTANTE: Convertimos a string (str) para evitar que salga "None" literal.
            raw_val = v.codigo_generacion or v.numero_documento or ""
            valor_visual = str(raw_val)
        else:
            # Físico
            raw_val = v.numero_control_desde or v.numero_documento or ""
            valor_visual = str(raw_val)

        if fecha not in resumen_diario:
            resumen_diario[fecha] = {
                "caja": "GEN", # Puedes mapear esto a un campo de caja si lo tuvieras
                "del_num": valor_visual,
                "al_num": valor_visual,
                "exentas": 0.0, "no_sujetas": 0.0, "gravadas": 0.0, "total": 0.0
            }
        
        # Actualizamos "Al"
        resumen_diario[fecha]["al_num"] = valor_visual
        
        total_venta = float(v.venta_gravada) + float(v.debito_fiscal)
        
        if v.clasificacion_venta == "2": resumen_diario[fecha]["exentas"] += total_venta
        elif v.clasificacion_venta == "3": resumen_diario[fecha]["no_sujetas"] += total_venta
        else: resumen_diario[fecha]["gravadas"] += total_venta
        
        resumen_diario[fecha]["total"] += total_venta

    # Tabla
    headers_1 = ['Día', 'Nº de CAJA', 'Correlativo', '', 'Ventas', '', '', 'Export.', 'Retención', 'Venta']
    headers_2 = ['', '', 'Del Nº', 'Al Nº', 'No Sujetas', 'Exentas', 'Gravadas', '', 'IVA 1%', 'Total']
    data = [headers_1, headers_2]

    t_no_suj = 0; t_exenta = 0; t_grav = 0; t_total = 0
    
    # Estilo UUID (letra muy pequeña para que quepa el código largo)
    estilo_uuid = ParagraphStyle(name='UUID', fontSize=5, alignment=TA_CENTER, leading=6)
    estilo_celda = ParagraphStyle(name='Celda', fontSize=8, alignment=TA_CENTER)

    for fecha, info in resumen_diario.items():
        t_no_suj += info["no_sujetas"]; t_exenta += info["exentas"]; t_grav += info["gravadas"]; t_total += info["total"]

        # Determinamos si usamos estilo pequeño (UUID largo) o normal
        estilo_uso = estilo_uuid if len(info["del_num"]) > 15 else estilo_celda

        row = [
            fecha,
            info["caja"],
            Paragraph(info["del_num"], estilo_uso), # ¡Ahora sí mostrará el código!
            Paragraph(info["al_num"], estilo_uso),
            f"${info['no_sujetas']:,.2f}" if info['no_sujetas'] > 0 else "",
            f"${info['exentas']:,.2f}" if info['exentas'] > 0 else "",
            f"${info['gravadas']:,.2f}",
            "", "",
            f"${info['total']:,.2f}"
        ]
        data.append(row)

    data.append(['', '', 'TOTALES:', '', f"${t_no_suj:,.2f}", f"${t_exenta:,.2f}", f"${t_grav:,.2f}", '', '', f"${t_total:,.2f}"])

    col_widths = [50, 40, 130, 130, 60, 60, 70, 50, 60, 70] # Columnas UUID más anchas
    
    tabla = Table(data, colWidths=col_widths, repeatRows=2)
    tabla.setStyle(TableStyle([
        ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (1,1)), ('SPAN', (2,0), (3,0)), ('SPAN', (4,0), (6,0)), ('SPAN', (7,0), (7,1)), ('SPAN', (8,0), (8,1)), ('SPAN', (9,0), (9,1)),
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
        ('ALIGN', (4, 2), (-1, -1), 'RIGHT'),
    ]))
    elements.append(tabla)

    elements.append(Spacer(1, 40))
    data_firmas = [['_________________________', '_________________________'], ['F. CONTADOR', 'F. REPRESENTANTE LEGAL']]
    tabla_firmas = Table(data_firmas, colWidths=[250, 250])
    tabla_firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(tabla_firmas)

    doc.build(elements)
    return response

    # 12. PDF VENTAS CONTRIBUYENTES (CCF) - ¡NUEVA!
@api_view(['GET'])
def generar_pdf_ventas_ccf(request):
    cliente_id = request.query_params.get('nrc')
    periodo = request.query_params.get('periodo')
    
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.lib import colors
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_VENTAS_CCF_{periodo}.pdf"'

    try:
        cliente = Cliente.objects.get(nrc=cliente_id)
        # Solo Ventas CCF
        ventas = Venta.objects.filter(cliente=cliente, periodo_aplicado=periodo, tipo_venta='CCF').order_by('fecha_emision', 'numero_documento')
    except Cliente.DoesNotExist:
        return HttpResponse("Cliente no encontrado", status=404)

    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()

    # --- ENCABEZADO ---
    estilo_titulo = ParagraphStyle(name='Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=12, spaceAfter=2)
    estilo_sub = ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)

    # Articulo a la derecha (como en tu ejemplo)
    estilo_derecha = ParagraphStyle(name='Der', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=8)
    elements.append(Paragraph("Art. 85 R.A.C.T.", estilo_derecha))
    
    elements.append(Paragraph("LIBRO DE VENTAS A CONTRIBUYENTES", estilo_titulo))
    elements.append(Paragraph(f"{cliente.nombre}", estilo_sub))
    elements.append(Paragraph(f"Periodo del: {periodo} | DUI:{cliente.dui} NRC: {cliente.nrc}", estilo_sub))
    elements.append(Paragraph("(Cifras Expresadas en Dolares de los Estados Unidos de America)", estilo_sub))
    elements.append(Spacer(1, 15))

    # --- TABLA DE DATOS ---
    # Encabezados (Fila 1 y 2 para agrupar títulos)
    headers_1 = ['No', 'Día', 'Nº de', 'Nombre del', 'Nº de', 'Ventas Internas', '', '', 'Débito', 'IVA 1%', 'Venta']
    headers_2 = ['Corr.', '', 'Comprob.', 'Cliente', 'Reg.', 'Exentas', 'Gravadas', '', 'Fiscal', 'Retenido', 'Total']
    
    # Nota: Simplifiqué algunas columnas vacías (Exportaciones, Terceros) para que quepa mejor y se vea limpio, 
    # pero si las necesitas obligatoriamente las agregamos.

    data = [headers_1, headers_2]

    # Variables de Totales
    t_exenta = 0; t_gravada = 0; t_debito = 0; t_ret1 = 0; t_total = 0
    correlativo = 1

    estilo_celda = ParagraphStyle(name='Celda', fontSize=7, leading=8, alignment=TA_LEFT)
    estilo_num = ParagraphStyle(name='Num', fontSize=7, leading=8, alignment=TA_RIGHT)

    for v in ventas:
        # Cálculos
        gravada = float(v.venta_gravada)
        debito = float(v.debito_fiscal)
        exenta = 0.00 # (Si tuvieras ventas exentas CCF, iría aquí)
        if v.clasificacion_venta == "2": # Si marcaste exenta
             exenta = gravada
             gravada = 0.00
             debito = 0.00
        
        # OJO: El total suele ser Gravado + IVA
        total = gravada + debito + exenta
        ret1 = float(v.iva_retenido_1) # Retención que nos hicieron (si aplica)

        # Sumar Totales Generales
        t_exenta += exenta; t_gravada += gravada; t_debito += debito
        t_ret1 += ret1; t_total += total

        # Formato de Fecha (Solo día o dd/mm)
        dia = v.fecha_emision.strftime("%d/%m") 

        row = [
            str(correlativo),
            dia,
            v.numero_documento or v.codigo_generacion, # Prioridad al corto
            Paragraph(v.nombre_receptor[:35], estilo_celda), # Recortar nombre largo
            v.nrc_receptor,
            f"${exenta:,.2f}" if exenta > 0 else "",
            f"${gravada:,.2f}",
            "", # Espacio extra visual
            f"${debito:,.2f}",
            f"${ret1:,.2f}" if ret1 > 0 else "",
            f"${total:,.2f}"
        ]
        data.append(row)
        correlativo += 1

    # Fila de Totales
    data.append([
        '', '', '', 'TOTALES:', '',
        f"${t_exenta:,.2f}", f"${t_gravada:,.2f}", '', f"${t_debito:,.2f}", 
        f"${t_ret1:,.2f}", f"${t_total:,.2f}"
    ])

    # Anchos de Columna (Total ~750 puntos)
    col_widths = [25, 35, 70, 180, 50, 55, 55, 10, 55, 55, 60]
    
    tabla = Table(data, colWidths=col_widths, repeatRows=2)
    tabla.setStyle(TableStyle([
        ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (1,1)), ('SPAN', (2,0), (2,1)), ('SPAN', (3,0), (3,1)), 
        ('SPAN', (4,0), (4,1)), ('SPAN', (5,0), (7,0)), # Unir Ventas Internas
        ('SPAN', (8,0), (8,1)), ('SPAN', (9,0), (9,1)), ('SPAN', (10,0), (10,1)),
        
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
        ('ALIGN', (5, 2), (-1, -1), 'RIGHT'), # Números a la derecha
    ]))
    elements.append(tabla)

    elements.append(Spacer(1, 50))
    data_firmas = [['_________________________', '_________________________'], ['F. CONTADOR', 'F. REPRESENTANTE LEGAL']]
    tabla_firmas = Table(data_firmas, colWidths=[250, 250])
    tabla_firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(tabla_firmas)

    doc.build(elements)
    return response
# --- REPORTES CSV (INCLUYENDO EL NUEVO DE PERCEPCIONES) ---

@api_view(['GET'])
def generar_csv_163(request):
    """
    CSV 163: Percepciones IVA en Compras (DTE-03/14 con percepción)
    Formato: NIT;Fecha;03;CodGen;NumDoc;MontoGrav;Percepcion;[Vacio];8
    Filtra solo compras con percepción > 0
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return HttpResponse("Falta periodo", status=400)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="ANEXO_163_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    
    # Filtrar solo compras con percepción > 0
    compras = Compra.objects.filter(
        empresa=empresa,
        periodo_aplicado=periodo,
        monto_percepcion__gt=0
    ).order_by('fecha_emision')
    
    for c in compras:
        fecha_fmt = c.fecha_emision.strftime("%d/%m/%Y")
        nit_limpio = limpiar_nit(c.nrc_proveedor)
        cod_gen_limpio = (c.codigo_generacion or "").replace("-", "").replace(" ", "")
        num_doc = cod_gen_limpio or c.nrc_proveedor  # Usar código o NRC como número de documento
        
        # Formato: NIT;Fecha;03;CodGen;NumDoc;MontoGrav;Percepcion;[Vacio];8
        fila = [
            nit_limpio,
            fecha_fmt,
            "03",  # Tipo documento (03 = CCF)
            cod_gen_limpio,
            num_doc,
            format(c.monto_gravado, '.2f'),  # Monto Gravado
            format(c.monto_percepcion, '.2f'),  # Percepción
            "",  # Vacío
            "8"  # Tipo anexo
        ]
        writer.writerow(fila)
    
    return response

# --- ENDPOINT PARA OBTENER VENTAS PARA CONCILIACIÓN ---
@api_view(['GET'])
def obtener_ventas_para_conciliacion(request):
    """
    Obtiene ventas de un cliente/empresa en un rango de fechas para conciliación de retenciones.
    Parámetros: empresa_id, fecha_desde, fecha_hasta, tipo_doc (opcional: CCF/CF)
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    fecha_desde = request.query_params.get('fecha_desde')
    fecha_hasta = request.query_params.get('fecha_hasta')
    tipo_doc = request.query_params.get('tipo_doc')  # CCF o CF
    if not fecha_desde or not fecha_hasta:
        return Response({"error": "Faltan fecha_desde o fecha_hasta"}, status=400)
    
    from datetime import datetime
    try:
        fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
        fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
    except:
        return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=400)
    
    ventas = Venta.objects.filter(
        empresa=empresa,
        fecha_emision__gte=fecha_desde_obj,
        fecha_emision__lte=fecha_hasta_obj
    )
    
    if tipo_doc:
        if tipo_doc == 'CCF':
            ventas = ventas.filter(tipo_venta='CCF')
        elif tipo_doc == 'CF':
            ventas = ventas.filter(tipo_venta='CF')
    
    # Excluir ventas que ya tienen retenciones aplicadas
    ventas = ventas.exclude(retenciones_aplicadas__isnull=False)
    
    ventas = ventas.order_by('fecha_emision')
    
    datos = []
    for v in ventas:
        retencion_calculada = float(v.venta_gravada) * 0.01  # 1% de retención
        datos.append({
            'id': v.id,
            'fecha_emision': v.fecha_emision.strftime('%Y-%m-%d'),
            'numero_documento': v.numero_documento or v.codigo_generacion or '',
            'tipo_venta': v.tipo_venta,
            'nombre_receptor': v.nombre_receptor or '',
            'nrc_receptor': v.nrc_receptor or '',
            'venta_gravada': float(v.venta_gravada),
            'debito_fiscal': float(v.debito_fiscal),
            'total': float(v.venta_gravada + v.debito_fiscal),
            'retencion_calculada': retencion_calculada  # 1% de la venta gravada
        })
    
    return Response({
        'total': len(datos),
        'ventas': datos
    })

# ==========================================
# MÓDULO DE LIBROS DE IVA - VISTA PREVIA Y REPORTES
# ==========================================

# --- VISTA PREVIA (JSON) PARA FRONTEND ---
@api_view(['GET'])
def vista_previa_compras(request):
    """
    Devuelve las compras de una empresa en formato JSON para vista previa.
    Parámetros: empresa_id, periodo (YYYY-MM)
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return Response({"error": "Falta periodo"}, status=400)
    compras = Compra.objects.filter(empresa=empresa, periodo_aplicado=periodo).order_by('fecha_emision')
    datos = []
    for c in compras:
        datos.append({
            'id': c.id,
            'fecha_emision': c.fecha_emision.strftime('%Y-%m-%d'),
            'tipo_documento': c.tipo_documento,
            'codigo_generacion': c.codigo_generacion or '',
            'nrc_proveedor': c.nrc_proveedor,
            'nombre_proveedor': c.nombre_proveedor,
            'monto_gravado': float(c.monto_gravado),
            'monto_iva': float(c.monto_iva),
            'monto_total': float(c.monto_total),
            'clasificacion_1': c.clasificacion_1,
            'clasificacion_2': c.clasificacion_2,
            'clasificacion_3': c.clasificacion_3,
        })
    totales = compras.aggregate(
        total_gravado=Sum('monto_gravado'),
        total_iva=Sum('monto_iva'),
        total_general=Sum('monto_total')
    )
    return Response({
        'empresa': empresa.nombre,
        'periodo': periodo,
        'total_registros': len(datos),
        'totales': {
            'gravado': float(totales['total_gravado'] or 0),
            'iva': float(totales['total_iva'] or 0),
            'total': float(totales['total_general'] or 0),
        },
        'datos': datos
    })

@api_view(['GET'])
def vista_previa_ventas_ccf(request):
    """
    Devuelve las ventas a Contribuyentes de una empresa en formato JSON.
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return Response({"error": "Falta periodo"}, status=400)
    ventas = Venta.objects.filter(empresa=empresa, periodo_aplicado=periodo, tipo_venta='CCF').order_by('fecha_emision')
    datos = []
    for v in ventas:
        datos.append({
            'id': v.id,
            'fecha_emision': v.fecha_emision.strftime('%Y-%m-%d'),
            'numero_documento': v.numero_documento or '',
            'codigo_generacion': v.codigo_generacion or '',
            'nombre_receptor': v.nombre_receptor or '',
            'nrc_receptor': v.nrc_receptor or '',
            'venta_gravada': float(v.venta_gravada),
            'debito_fiscal': float(v.debito_fiscal),
            'total': float(v.venta_gravada + v.debito_fiscal),
        })

    totales = ventas.aggregate(
        total_gravado=Sum('venta_gravada'),
        total_iva=Sum('debito_fiscal')
    )

    return Response({
        'empresa': empresa.nombre,
        'periodo': periodo,
        'total_registros': len(datos),
        'totales': {
            'gravado': float(totales['total_gravado'] or 0),
            'iva': float(totales['total_iva'] or 0),
            'total': float((totales['total_gravado'] or 0) + (totales['total_iva'] or 0)),
        },
        'datos': datos
    })

@api_view(['GET'])
def vista_previa_ventas_cf(request):
    """
    Devuelve las ventas a Consumidor Final de una empresa en formato JSON.
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return Response({"error": "Falta periodo"}, status=400)
    ventas = Venta.objects.filter(empresa=empresa, periodo_aplicado=periodo, tipo_venta='CF').order_by('fecha_emision')
    datos = []
    for v in ventas:
        datos.append({
            'id': v.id,
            'fecha_emision': v.fecha_emision.strftime('%Y-%m-%d'),
            'numero_documento': v.numero_documento or '',
            'codigo_generacion': v.codigo_generacion or '',
            'numero_control': v.numero_control or '',
            'venta_gravada': float(v.venta_gravada),
            'debito_fiscal': float(v.debito_fiscal),
            'total': float(v.venta_gravada + v.debito_fiscal),
        })

    totales = ventas.aggregate(
        total_gravado=Sum('venta_gravada'),
        total_iva=Sum('debito_fiscal')
    )

    return Response({
        'empresa': empresa.nombre,
        'periodo': periodo,
        'total_registros': len(datos),
        'totales': {
            'gravado': float(totales['total_gravado'] or 0),
            'iva': float(totales['total_iva'] or 0),
            'total': float((totales['total_gravado'] or 0) + (totales['total_iva'] or 0)),
        },
        'datos': datos
    })

# --- REPORTES CSV/PDF ADAPTADOS PARA EMPRESA ---
@api_view(['GET'])
def reporte_csv_compras_empresa(request):
    """
    Genera CSV de compras usando empresa_id.
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return HttpResponse("Falta periodo", status=400)
    compras = Compra.objects.filter(empresa=empresa, periodo_aplicado=periodo).order_by('fecha_emision')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_COMPRAS_{empresa.nombre}_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['FECHA', 'CLASE', 'TIPO', 'CODIGO', 'NRC', 'PROVEEDOR', 'EXENTAS', 'NO_SUJETAS', 
                     'IMPORT', 'INTERNAS', 'SERV_EXENTOS', 'SERV_GRAVADOS', 'OTROS', 'IVA', 'TOTAL', 
                     'OBSERV', 'CLASIF1', 'CLASIF2', 'CLASIF3', 'TIPO_OP', 'TIPO_ING'])
    map_clasif_1 = {"Gravada": "1", "Exenta": "2", "No Sujeta": "3"}
    map_clasif_2 = {"Costo": "1", "Gasto": "2"}
    map_clasif_3 = {"Industria": "1", "Comercio": "2", "Servicios": "3", "Agropecuario": "4", 
                    "Administración": "1", "Ventas": "2", "Financiero": "3"}
    for c in compras:
        fecha_fmt = c.fecha_emision.strftime("%d/%m/%Y")
        clase_doc = "4" if c.codigo_generacion and len(str(c.codigo_generacion)) > 20 else "1"
        tipo_doc = c.tipo_documento.zfill(2)
        nombre_limpio = c.nombre_proveedor.replace(";", "") if c.nombre_proveedor else ""
        es_importacion = c.tipo_documento == '12'
        col_9_internas = format(c.monto_gravado, '.2f') if not es_importacion else "0.00"
        col_8_import = format(c.monto_gravado, '.2f') if es_importacion else "0.00"
        cod_1 = map_clasif_1.get(c.clasificacion_1, "1")
        cod_2 = map_clasif_2.get(c.clasificacion_2, "1")
        cod_3 = map_clasif_3.get(c.clasificacion_3, "1")
        fila = [
            fecha_fmt, clase_doc, tipo_doc, c.codigo_generacion or '', c.nrc_proveedor, nombre_limpio,
            "0.00", "0.00", col_8_import, col_9_internas, "0.00", "0.00", "0.00",
            format(c.monto_iva, '.2f'), format(c.monto_total, '.2f'), "", cod_1, cod_2, cod_3, "5", "3"
        ]
        writer.writerow(fila)
    return response

@api_view(['GET'])
def reporte_pdf_compras_empresa(request):
    """
    Genera PDF de compras usando empresa_id.
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return HttpResponse("Falta periodo", status=400)
    compras = Compra.objects.filter(empresa=empresa, periodo_aplicado=periodo).order_by('fecha_emision')
    
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib import colors
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_COMPRAS_{empresa.nombre}_{periodo}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=15, leftMargin=15, topMargin=30, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()
    
    estilo_titulo = ParagraphStyle(name='Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=14, spaceAfter=2)
    estilo_sub = ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)
    
    elements.append(Paragraph("LIBRO DE COMPRAS", estilo_titulo))
    elements.append(Paragraph(f"CONTRIBUYENTE: {empresa.nombre}", estilo_sub))
    elements.append(Paragraph(f"NRC: {empresa.nrc}  |  NIT: {empresa.nit or 'N/A'}", estilo_sub))
    elements.append(Paragraph(f"PERÍODO: {periodo}  |  MONEDA: USD", estilo_sub))
    elements.append(Spacer(1, 10))
    
    col_widths = [30, 55, 160, 50, 140, 50, 50, 50, 45, 55, 45, 45]
    headers = ['No.', 'FECHA', 'Nº COMPROBANTE / DTE', 'NRC', 'PROVEEDOR', 'EXENTAS', 'GRAV. LOC', 'GRAV. IMP', 'IVA', 'TOTAL', 'RET 1%', 'RET 13%']
    data = [headers]
    
    t_exenta = 0; t_grav_loc = 0; t_grav_imp = 0; t_iva = 0; t_total = 0; t_ret1 = 0; t_ret13 = 0
    correlativo = 1
    
    estilo_celda = ParagraphStyle(name='Celda', fontSize=7, leading=8, alignment=TA_LEFT)
    estilo_celda_num = ParagraphStyle(name='CeldaNum', fontSize=7, leading=8, alignment=TA_RIGHT)
    
    for c in compras:
        es_importacion = c.tipo_documento == '12'
        exenta = 0.00
        grav_loc = float(c.monto_gravado) if not es_importacion else 0.00
        grav_imp = float(c.monto_gravado) if es_importacion else 0.00
        iva = float(c.monto_iva)
        total = float(c.monto_total)
        ret1 = 0.00
        ret13 = 0.00
        
        t_exenta += exenta; t_grav_loc += grav_loc; t_grav_imp += grav_imp
        t_iva += iva; t_total += total; t_ret1 += ret1; t_ret13 += ret13
        
        fila = [
            str(correlativo),
            c.fecha_emision.strftime("%d/%m/%Y"),
            Paragraph(c.codigo_generacion or "", estilo_celda),
            c.nrc_proveedor,
            Paragraph(c.nombre_proveedor, estilo_celda),
            Paragraph(f"{exenta:,.2f}", estilo_celda_num),
            Paragraph(f"{grav_loc:,.2f}", estilo_celda_num),
            Paragraph(f"{grav_imp:,.2f}", estilo_celda_num),
            Paragraph(f"{iva:,.2f}", estilo_celda_num),
            Paragraph(f"{total:,.2f}", estilo_celda_num),
            Paragraph(f"{ret1:,.2f}", estilo_celda_num),
            Paragraph(f"{ret13:,.2f}", estilo_celda_num),
        ]
        data.append(fila)
        correlativo += 1
    
    data.append(['', '', 'TOTALES:', '', '', f"${t_exenta:,.2f}", f"${t_grav_loc:,.2f}", f"${t_grav_imp:,.2f}", f"${t_iva:,.2f}", f"${t_total:,.2f}", f"${t_ret1:,.2f}", f"${t_ret13:,.2f}"])
    
    tabla = Table(data, colWidths=col_widths, repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
    ]))
    elements.append(tabla)
    
    elements.append(Spacer(1, 50))
    data_firmas = [['_________________________', '_________________________'], ['F. CONTADOR', 'F. REPRESENTANTE LEGAL']]
    tabla_firmas = Table(data_firmas, colWidths=[250, 250])
    tabla_firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(tabla_firmas)
    
    doc.build(elements)
    return response

@api_view(['GET'])
def reporte_csv_ventas_ccf_empresa(request):
    """
    Genera CSV de ventas a Contribuyentes usando empresa_id.
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return HttpResponse("Falta periodo", status=400)
    ventas = Venta.objects.filter(empresa=empresa, periodo_aplicado=periodo, tipo_venta='CCF').order_by('fecha_emision')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_VENTAS_CCF_{empresa.nombre}_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    for v in ventas:
        fecha_fmt = v.fecha_emision.strftime("%d/%m/%Y")
        clase_doc = v.clase_documento
        tipo_doc = "03"
        resolucion = v.numero_resolucion if clase_doc != '4' else ""
        serie = v.serie_documento if clase_doc != '4' else ""
        num_prin = v.numero_documento or ""
        num_sec = v.numero_formulario_unico if (clase_doc == '2' and v.numero_formulario_unico) else num_prin
        nombre_limpio = (v.nombre_receptor or "").replace(";", "")
        monto_exento = "0.00"
        monto_gravado = "0.00"
        monto_nosujeto = "0.00"
        base = v.venta_gravada
        if v.clasificacion_venta == "2":
            monto_exento = format(base, '.2f')
        elif v.clasificacion_venta == "3":
            monto_nosujeto = format(base, '.2f')
        else:
            monto_gravado = format(base, '.2f')
        fila = [
            fecha_fmt, clase_doc, tipo_doc, resolucion, serie, num_prin, num_sec,
            v.nrc_receptor or "", nombre_limpio, monto_exento, "0.00", monto_gravado,
            format(v.debito_fiscal, '.2f'), monto_nosujeto, "0.00", format(v.venta_gravada + v.debito_fiscal, '.2f'),
            "", v.clasificacion_venta.zfill(2), v.tipo_ingreso.zfill(2), "1"
        ]
        writer.writerow(fila)
    return response

@api_view(['GET'])
def reporte_pdf_ventas_ccf_empresa(request):
    """
    Genera PDF de ventas a Contribuyentes usando empresa_id.
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return HttpResponse("Falta periodo", status=400)
    ventas = Venta.objects.filter(empresa=empresa, periodo_aplicado=periodo, tipo_venta='CCF').order_by('fecha_emision', 'numero_documento')
    
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.lib import colors
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_VENTAS_CCF_{empresa.nombre}_{periodo}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()
    
    estilo_titulo = ParagraphStyle(name='Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=12, spaceAfter=2)
    estilo_sub = ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)
    estilo_derecha = ParagraphStyle(name='Der', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=8)
    
    elements.append(Paragraph("Art. 85 R.A.C.T.", estilo_derecha))
    elements.append(Paragraph("LIBRO DE VENTAS A CONTRIBUYENTES", estilo_titulo))
    elements.append(Paragraph(f"{empresa.nombre}", estilo_sub))
    elements.append(Paragraph(f"Periodo del: {periodo} | NRC: {empresa.nrc}", estilo_sub))
    elements.append(Paragraph("(Cifras Expresadas en Dolares de los Estados Unidos de America)", estilo_sub))
    elements.append(Spacer(1, 15))
    
    headers_1 = ['No', 'Día', 'Nº de', 'Nombre del', 'Nº de', 'Ventas Internas', '', '', 'Débito', 'IVA 1%', 'Venta']
    headers_2 = ['Corr.', '', 'Comprob.', 'Cliente', 'Reg.', 'Exentas', 'Gravadas', '', 'Fiscal', 'Retenido', 'Total']
    data = [headers_1, headers_2]
    
    t_exenta = 0; t_gravada = 0; t_debito = 0; t_ret1 = 0; t_total = 0
    correlativo = 1
    
    estilo_celda = ParagraphStyle(name='Celda', fontSize=7, leading=8, alignment=TA_LEFT)
    estilo_num = ParagraphStyle(name='Num', fontSize=7, leading=8, alignment=TA_RIGHT)
    
    for v in ventas:
        gravada = float(v.venta_gravada)
        debito = float(v.debito_fiscal)
        exenta = 0.00
        if v.clasificacion_venta == "2":
            exenta = gravada
            gravada = 0.00
            debito = 0.00
        
        total = gravada + debito + exenta
        ret1 = float(v.iva_retenido_1)
        
        t_exenta += exenta; t_gravada += gravada; t_debito += debito
        t_ret1 += ret1; t_total += total
        
        dia = v.fecha_emision.strftime("%d/%m")
        
        row = [
            str(correlativo),
            dia,
            v.numero_documento or v.codigo_generacion or '',
            Paragraph((v.nombre_receptor or '')[:35], estilo_celda),
            v.nrc_receptor or '',
            f"${exenta:,.2f}" if exenta > 0 else "",
            f"${gravada:,.2f}",
            "",
            f"${debito:,.2f}",
            f"${ret1:,.2f}" if ret1 > 0 else "",
            f"${total:,.2f}"
        ]
        data.append(row)
        correlativo += 1
    
    data.append([
        '', '', '', 'TOTALES:', '',
        f"${t_exenta:,.2f}", f"${t_gravada:,.2f}", '', f"${t_debito:,.2f}", 
        f"${t_ret1:,.2f}", f"${t_total:,.2f}"
    ])
    
    col_widths = [25, 35, 70, 180, 50, 55, 55, 10, 55, 55, 60]
    
    tabla = Table(data, colWidths=col_widths, repeatRows=2)
    tabla.setStyle(TableStyle([
        ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (1,1)), ('SPAN', (2,0), (2,1)), ('SPAN', (3,0), (3,1)), 
        ('SPAN', (4,0), (4,1)), ('SPAN', (5,0), (7,0)),
        ('SPAN', (8,0), (8,1)), ('SPAN', (9,0), (9,1)), ('SPAN', (10,0), (10,1)),
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
        ('ALIGN', (5, 2), (-1, -1), 'RIGHT'),
    ]))
    elements.append(tabla)
    
    elements.append(Spacer(1, 50))
    data_firmas = [['_________________________', '_________________________'], ['F. CONTADOR', 'F. REPRESENTANTE LEGAL']]
    tabla_firmas = Table(data_firmas, colWidths=[250, 250])
    tabla_firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(tabla_firmas)
    
    doc.build(elements)
    return response

@api_view(['GET'])
def reporte_csv_ventas_cf_empresa(request):
    """
    Genera CSV de ventas a Consumidor Final usando empresa_id.
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return HttpResponse("Falta periodo", status=400)
    ventas = Venta.objects.filter(empresa=empresa, periodo_aplicado=periodo, tipo_venta='CF').order_by('fecha_emision')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_VENTAS_CF_{empresa.nombre}_{periodo}.csv"'
    writer = csv.writer(response, delimiter=';')
    for v in ventas:
        fecha_fmt = v.fecha_emision.strftime("%d/%m/%Y")
        clase_doc = v.clase_documento
        cod_gen_limpio = str(v.codigo_generacion or "").replace("-", "").upper()
        num_ctrl_limpio = str(v.numero_control or "").replace("-", "").upper()
        sello_limpio = str(v.sello_recepcion or "").replace("-", "").upper()
        if clase_doc == '4':
            tipo_doc_mh = "01"
            col_3_res = num_ctrl_limpio
            col_4_ser = sello_limpio
            col_5_ci_del = cod_gen_limpio
            col_6_ci_al = cod_gen_limpio
            col_7_del = cod_gen_limpio
            col_8_al = cod_gen_limpio
            col_9_maq = ""
        else:
            tipo_doc_mh = "01"
            col_3_res = v.numero_resolucion or ""
            col_4_ser = v.serie_documento or ""
            col_5_ci_del = ""
            col_6_ci_al = ""
            col_7_del = v.numero_control_desde or v.numero_documento or ""
            col_8_al = v.numero_control_hasta or v.numero_documento or ""
            col_9_maq = ""
        monto_exento = "0.00"
        monto_gravado = "0.00"
        total_venta_dia = v.venta_gravada + v.debito_fiscal
        if v.clasificacion_venta == "2":
            monto_exento = format(total_venta_dia, '.2f')
        else:
            monto_gravado = format(v.venta_gravada, '.2f')
        total_fmt = format(total_venta_dia, '.2f')
        fila = [
            fecha_fmt, clase_doc, tipo_doc_mh, col_3_res, col_4_ser, col_5_ci_del, col_6_ci_al,
            col_7_del, col_8_al, col_9_maq, monto_exento, "0.00", "0.00", monto_gravado,
            "0.00", "0.00", "0.00", "0.00", "0.00", total_fmt,
            v.clasificacion_venta, v.tipo_ingreso, "2"
        ]
        writer.writerow(fila)
    return response

@api_view(['GET'])
def reporte_pdf_ventas_cf_empresa(request):
    """
    Genera PDF de ventas a Consumidor Final usando empresa_id.
    """
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    periodo = request.query_params.get('periodo')
    if not periodo:
        return HttpResponse("Falta periodo", status=400)
    ventas = Venta.objects.filter(empresa=empresa, periodo_aplicado=periodo, tipo_venta='CF').order_by('fecha_emision', 'numero_control')
    
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib import colors
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="LIBRO_VENTAS_CF_{empresa.nombre}_{periodo}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=landscape(letter), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()
    
    estilo_titulo = ParagraphStyle(name='Titulo', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=12, spaceAfter=2)
    estilo_sub = ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)
    
    elements.append(Paragraph("LIBRO DE VENTAS A CONSUMIDOR FINAL", estilo_titulo))
    elements.append(Paragraph(f"{empresa.nombre}", estilo_sub))
    elements.append(Paragraph(f"Periodo del: {periodo} | NRC: {empresa.nrc}", estilo_sub))
    elements.append(Paragraph("(Cifras Expresadas en Dolares de los Estados Unidos de America)", estilo_sub))
    elements.append(Spacer(1, 15))
    
    resumen_diario = {}
    
    for v in ventas:
        fecha = v.fecha_emision.strftime("%d/%m/%Y")
        
        if v.clase_documento == '4':
            raw_val = v.codigo_generacion or v.numero_documento or ""
            valor_visual = str(raw_val)
        else:
            raw_val = v.numero_control_desde or v.numero_documento or ""
            valor_visual = str(raw_val)
        
        if fecha not in resumen_diario:
            resumen_diario[fecha] = {
                "caja": "GEN",
                "del_num": valor_visual,
                "al_num": valor_visual,
                "exentas": 0.0, "no_sujetas": 0.0, "gravadas": 0.0, "total": 0.0
            }
        
        resumen_diario[fecha]["al_num"] = valor_visual
        
        total_venta = float(v.venta_gravada) + float(v.debito_fiscal)
        
        if v.clasificacion_venta == "2":
            resumen_diario[fecha]["exentas"] += total_venta
        elif v.clasificacion_venta == "3":
            resumen_diario[fecha]["no_sujetas"] += total_venta
        else:
            resumen_diario[fecha]["gravadas"] += total_venta
        
        resumen_diario[fecha]["total"] += total_venta
    
    headers_1 = ['Día', 'Nº de CAJA', 'Correlativo', '', 'Ventas', '', '', 'Export.', 'Retención', 'Venta']
    headers_2 = ['', '', 'Del Nº', 'Al Nº', 'No Sujetas', 'Exentas', 'Gravadas', '', 'IVA 1%', 'Total']
    data = [headers_1, headers_2]
    
    t_no_suj = 0; t_exenta = 0; t_grav = 0; t_total = 0
    
    estilo_uuid = ParagraphStyle(name='UUID', fontSize=5, alignment=TA_CENTER, leading=6)
    estilo_celda = ParagraphStyle(name='Celda', fontSize=8, alignment=TA_CENTER)
    
    for fecha, info in resumen_diario.items():
        t_no_suj += info["no_sujetas"]
        t_exenta += info["exentas"]
        t_grav += info["gravadas"]
        t_total += info["total"]
        
        estilo_uso = estilo_uuid if len(info["del_num"]) > 15 else estilo_celda
        
        row = [
            fecha,
            info["caja"],
            Paragraph(info["del_num"], estilo_uso),
            Paragraph(info["al_num"], estilo_uso),
            f"${info['no_sujetas']:,.2f}" if info['no_sujetas'] > 0 else "",
            f"${info['exentas']:,.2f}" if info['exentas'] > 0 else "",
            f"${info['gravadas']:,.2f}",
            "", "",
            f"${info['total']:,.2f}"
        ]
        data.append(row)
    
    data.append(['', '', 'TOTALES:', '', f"${t_no_suj:,.2f}", f"${t_exenta:,.2f}", f"${t_grav:,.2f}", '', '', f"${t_total:,.2f}"])
    
    col_widths = [50, 40, 130, 130, 60, 60, 70, 50, 60, 70]
    
    tabla = Table(data, colWidths=col_widths, repeatRows=2)
    tabla.setStyle(TableStyle([
        ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (1,1)), ('SPAN', (2,0), (3,0)), ('SPAN', (4,0), (6,0)), ('SPAN', (7,0), (7,1)), ('SPAN', (8,0), (8,1)), ('SPAN', (9,0), (9,1)),
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
        ('ALIGN', (4, 2), (-1, -1), 'RIGHT'),
    ]))
    elements.append(tabla)
    
    elements.append(Spacer(1, 40))
    data_firmas = [['_________________________', '_________________________'], ['F. CONTADOR', 'F. REPRESENTANTE LEGAL']]
    tabla_firmas = Table(data_firmas, colWidths=[250, 250])
    tabla_firmas.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    elements.append(tabla_firmas)
    
    doc.build(elements)
    return response


# --- LIBROS DE IVA UNIFICADO (mes / anio / tipo_libro / format) ---
from rest_framework.permissions import IsAuthenticated
from .permissions import IsContadorUser

@api_view(['GET'])
@drf_permission_classes([IsAuthenticated, IsContadorUser])
def libros_iva_reporte_api(request):
    """
    Vista unificada Libros de IVA.
    Parámetros: mes (1-12), anio (ej. 2026), tipo_libro ('consumidor' | 'contribuyente'), empresa_id (opcional si se usa header).
    Si format=pdf o format=csv devuelve el archivo; si no, devuelve JSON (vista previa).
    """
    from .utils.reportes_iva import (
        get_datos_libro_consumidor,
        get_datos_libro_contribuyentes,
        generar_csv_libro,
        generar_pdf_libro,
    )
    mes = request.query_params.get('mes')
    anio = request.query_params.get('anio')
    tipo_libro = (request.query_params.get('tipo_libro') or '').strip().lower()
    empresa, err = get_and_validate_empresa(request)
    if err is not None:
        return err
    empresa_id = empresa.id
    fmt = (request.query_params.get('export') or request.query_params.get('format') or '').strip().lower()
    try:
        mes = int(mes)
        anio = int(anio)
    except (TypeError, ValueError):
        return Response({"error": "mes y anio deben ser números (mes 1-12, anio ej. 2026)"}, status=400)
    if mes < 1 or mes > 12:
        return Response({"error": "mes debe estar entre 1 y 12"}, status=400)
    if tipo_libro not in ('consumidor', 'contribuyente'):
        return Response({"error": "tipo_libro debe ser 'consumidor' o 'contribuyente'"}, status=400)
    if tipo_libro == 'consumidor':
        resultado = get_datos_libro_consumidor(empresa_id, mes, anio)
    else:
        resultado = get_datos_libro_contribuyentes(empresa_id, mes, anio)
    if fmt == 'pdf':
        return generar_pdf_libro(tipo_libro, resultado, empresa)
    if fmt == 'csv':
        return generar_csv_libro(tipo_libro, resultado, empresa)
    return Response({
        'empresa': empresa.nombre,
        'periodo': resultado['periodo'],
        'tipo_libro': tipo_libro,
        'total_registros': len(resultado['datos']),
        'datos': resultado['datos'],
        'totales': resultado['totales'],
    })