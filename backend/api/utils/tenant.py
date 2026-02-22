"""
Filtro multi-tenant: impide que una empresa vea datos de otra.
Usar en todas las vistas que acceden a datos por empresa.

Reglas de acceso a empresas:
  - No autenticado          → []
  - Superusuario Django     → todas las empresas
  - Con PerfilUsuario.empresa=None → todas las empresas (admin global)
  - Con PerfilUsuario.empresa=X   → solo empresa X
  - Sin PerfilUsuario       → [] (sin acceso)
"""
from typing import List, Optional
from django.http import HttpRequest
from rest_framework.response import Response
from rest_framework import status


def get_empresa_ids_allowlist(request: HttpRequest) -> List[int]:
    """
    Devuelve los IDs de empresa a los que el usuario tiene acceso.
    La empresa asignada se lee de PerfilUsuario (única fuente para tenant).
    El rol (qué puede hacer) se lee de los Grupos Django (única fuente para permisos).
    """
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return []

    # Superusuario: acceso a todas las empresas
    if getattr(request.user, 'is_superuser', False):
        from ..models import Empresa
        return list(Empresa.objects.values_list('id', flat=True))

    # Usuario normal: empresa desde PerfilUsuario
    try:
        from ..models import PerfilUsuario
        perfil = PerfilUsuario.objects.select_related('empresa').get(
            user=request.user, activo=True
        )
        # empresa=None en el perfil → acceso global (admin multi-empresa)
        if perfil.empresa_id is None:
            from ..models import Empresa
            return list(Empresa.objects.values_list('id', flat=True))
        return [perfil.empresa_id]
    except Exception:
        return []


def require_empresa_allowed(request: HttpRequest, empresa_id) -> Optional[Response]:
    """
    Verifica que empresa_id esté en la allowlist del usuario.
    Devuelve None si está permitido, o Response con error si no.
    """
    if empresa_id is None:
        return Response(
            {"error": "empresa_id requerido"},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        eid = int(empresa_id)
    except (TypeError, ValueError):
        return Response(
            {"error": "empresa_id inválido"},
            status=status.HTTP_400_BAD_REQUEST
        )
    allowlist = get_empresa_ids_allowlist(request)
    if not allowlist:
        return Response(
            {"error": "No autorizado"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    if eid not in allowlist:
        return Response(
            {"error": "No tiene permiso para acceder a esta empresa"},
            status=status.HTTP_403_FORBIDDEN
        )
    return None


def require_authenticated_tenant(request: HttpRequest) -> Optional[Response]:
    """
    Si el usuario no tiene al menos una empresa permitida, devuelve 401.
    """
    allowlist = get_empresa_ids_allowlist(request)
    if not allowlist:
        return Response(
            {"error": "Autenticación requerida"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    return None


def object_empresa_id(obj) -> Optional[int]:
    """Obtiene el empresa_id de un modelo (Venta, Compra, Producto, etc.)."""
    return getattr(obj, 'empresa_id', None) or (
        getattr(obj, 'empresa', None) and obj.empresa.id
    )


def require_object_empresa_allowed(request: HttpRequest, obj) -> Optional[Response]:
    """
    Verifica que el objeto pertenezca a una empresa del usuario.
    Devuelve None si permitido, 404 si no.
    """
    eid = object_empresa_id(obj)
    if eid is None:
        return Response({"error": "Recurso sin empresa"}, status=status.HTTP_404_NOT_FOUND)
    allowlist = get_empresa_ids_allowlist(request)
    if not allowlist:
        return Response({"error": "No autorizado"}, status=status.HTTP_401_UNAUTHORIZED)
    if eid not in allowlist:
        return Response({"error": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)
    return None


def get_and_validate_empresa(request: HttpRequest, from_body: bool = False, required: bool = True):
    """
    Obtiene empresa_id de query_params o body, valida tenant y devuelve la Empresa.
    Returns: (Empresa, None) si ok | (None, Response) si error.
    """
    if from_body:
        empresa_id = request.data.get('empresa_id')
    else:
        empresa_id = request.query_params.get('empresa_id') or request.data.get('empresa_id')

    if not empresa_id and required:
        return None, Response(
            {"error": "empresa_id requerido"}, status=status.HTTP_400_BAD_REQUEST
        )
    if not empresa_id:
        return None, None

    r = require_empresa_allowed(request, empresa_id)
    if r is not None:
        return None, r

    try:
        from ..models import Empresa
        return Empresa.objects.get(id=int(empresa_id)), None
    except (ValueError, TypeError):
        return None, Response(
            {"error": "empresa_id inválido"}, status=status.HTTP_400_BAD_REQUEST
        )
    except Empresa.DoesNotExist:
        return None, Response(
            {"error": "Empresa no encontrada"}, status=status.HTTP_404_NOT_FOUND
        )
