"""
Filtro multi-tenant: impide que una empresa vea datos de otra.
Usar en todas las vistas que tocan datos por empresa.
"""
from typing import List, Optional
from django.http import HttpRequest
from rest_framework.response import Response
from rest_framework import status


def get_empresa_ids_allowlist(request: HttpRequest) -> List[int]:
    """
    Devuelve la lista de IDs de empresa a los que el usuario tiene derecho.
    - No autenticado -> []
    - Superuser -> todos los IDs
    - PerfilUsuario con empresa=None (MASTER) -> todos los IDs
    - PerfilUsuario con empresa=X -> [X]
    - Sin perfil -> []
    """
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return []

    if getattr(request.user, 'is_superuser', False) and request.user.is_superuser:
        from ..models import Empresa
        return list(Empresa.objects.values_list('id', flat=True))

    try:
        from ..models import PerfilUsuario
        perfil = PerfilUsuario.objects.select_related('empresa').get(user=request.user, activo=True)
        if perfil.empresa_id is None:
            from ..models import Empresa
            return list(Empresa.objects.values_list('id', flat=True))
        return [perfil.empresa_id]
    except Exception:
        return []


def require_empresa_allowed(request: HttpRequest, empresa_id) -> Optional[Response]:
    """
    Si empresa_id no está en la allowlist del usuario, devuelve Response 403.
    Si todo ok, devuelve None (seguir con la vista).
    empresa_id puede ser int o str.
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
    Útil al inicio de vistas que siempre requieren tenant.
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
    return getattr(obj, 'empresa_id', None) or (getattr(obj, 'empresa', None) and obj.empresa.id)


def require_object_empresa_allowed(request: HttpRequest, obj) -> Optional[Response]:
    """
    Si el objeto (venta, compra, etc.) no pertenece a una empresa permitida, devuelve 404.
    Devuelve None si está permitido.
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
    Obtiene empresa_id de query_params o body, valida tenant y devuelve Empresa.
    Returns: (Empresa, None) si ok, o (None, Response) si hay error.
    """
    if from_body:
        empresa_id = request.data.get('empresa_id')
    else:
        empresa_id = request.query_params.get('empresa_id') or request.data.get('empresa_id')
    if not empresa_id and required:
        return None, Response({"error": "empresa_id requerido"}, status=status.HTTP_400_BAD_REQUEST)
    if not empresa_id:
        return None, None
    r = require_empresa_allowed(request, empresa_id)
    if r is not None:
        return None, r
    try:
        from ..models import Empresa
        return Empresa.objects.get(id=int(empresa_id)), None
    except (ValueError, TypeError):
        return None, Response({"error": "empresa_id inválido"}, status=status.HTTP_400_BAD_REQUEST)
    except Empresa.DoesNotExist:
        return None, Response({"error": "Empresa no encontrada"}, status=status.HTTP_404_NOT_FOUND)
