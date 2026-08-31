"""Acceso a PDF/JSON DTE: autenticación, tenant y coincidencia de documento.

Nadie puede abrir el PDF/JSON de otra empresa adivinando el ID numérico
(POS 819 ≠ AgilDTE 819). Se exige código de generación o número de control
que coincida con la venta, y que la venta sea de una empresa permitida.
Denegaciones se registran para auditoría.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from django.http import HttpRequest

from .tenant import get_empresa_ids_allowlist, object_empresa_id

logger = logging.getLogger("api.dte_acceso")

# Mismo cuerpo 404 en todos los denegados autenticados: no confirmar que el ID existe.
_BODY_404 = {"error": "No encontrado"}
_BODY_401 = {"error": "Autenticación requerida"}


def coincidencia_documento_dte(
    venta: Any,
    codigo_generacion: str | None,
    numero_control: str | None,
) -> bool:
    """True solo si el código o el número de control coinciden exactamente (sin usar el PK)."""
    cg = (codigo_generacion or "").strip().upper()
    nc = (numero_control or "").strip().upper()
    if not cg and not nc:
        return False
    vcg = str(getattr(venta, "codigo_generacion", None) or "").strip().upper()
    vnc = str(getattr(venta, "numero_control", None) or "").strip().upper()
    if cg and vcg and cg == vcg:
        return True
    if nc and vnc and nc == vnc:
        return True
    return False


def _qp(request: HttpRequest, *names: str) -> str:
    for name in names:
        qp = getattr(request, "query_params", None)
        if qp is not None:
            val = qp.get(name)
            if val is not None and str(val).strip():
                return str(val).strip()
        val = request.GET.get(name)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def empresa_id_solicitada(request: HttpRequest) -> Optional[int]:
    raw = _qp(request, "empresa_id", "empresa")
    if not raw:
        raw = (
            request.headers.get("X-Company-ID")
            or request.META.get("HTTP_X_COMPANY_ID")
            or ""
        ).strip()
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def autenticar_request_jwt(request: HttpRequest) -> bool:
    """Rellena request.user desde JWT. Las vistas PDF no pasan por DRF @api_view."""
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return True
    try:
        from rest_framework.request import Request
        from rest_framework_simplejwt.authentication import JWTAuthentication

        auth = JWTAuthentication().authenticate(Request(request))
        if auth is not None:
            request.user, request.auth = auth
            return True
    except Exception:
        pass
    return False


def auditar_acceso_dte(
    *,
    request: HttpRequest,
    resultado: str,
    recurso: str,
    venta_id: int | None,
    empresa_venta: int | None = None,
    empresa_query: int | None = None,
) -> None:
    user = getattr(request, "user", None)
    uid = getattr(user, "pk", None) if user is not None else None
    uname = getattr(user, "username", "") if user is not None else ""
    msg = (
        "dte_acceso resultado=%s recurso=%s venta_id=%s empresa_venta=%s "
        "empresa_query=%s user_id=%s username=%s"
    )
    args = (resultado, recurso, venta_id, empresa_venta, empresa_query, uid, uname)
    if resultado in ("denegado_tenant", "denegado_empresa", "denegado_documento"):
        logger.warning(msg, *args)
    else:
        logger.info(msg, *args)


def evaluar_acceso_dte_venta(
    request: HttpRequest,
    venta: Any,
    *,
    recurso: str,
) -> tuple[str, int, dict]:
    """
    Autenticación + tenant + empresa_id de la petición + código/número DTE.

    Retorna (resultado, http_status, body). Si resultado == 'ok', body vacío.
    Denegado autenticado → 404 (no filtrar existencia). Sin login → 401.
    """
    venta_id = getattr(venta, "pk", None) or getattr(venta, "id", None)
    eid_venta = object_empresa_id(venta)
    eid_query = empresa_id_solicitada(request)

    if not autenticar_request_jwt(request):
        auditar_acceso_dte(
            request=request,
            resultado="denegado_auth",
            recurso=recurso,
            venta_id=venta_id,
            empresa_venta=eid_venta,
            empresa_query=eid_query,
        )
        return "denegado_auth", 401, _BODY_401

    allowlist = get_empresa_ids_allowlist(request)
    if not allowlist:
        auditar_acceso_dte(
            request=request,
            resultado="denegado_auth",
            recurso=recurso,
            venta_id=venta_id,
            empresa_venta=eid_venta,
            empresa_query=eid_query,
        )
        return "denegado_auth", 401, _BODY_401

    if eid_venta is None or eid_venta not in allowlist:
        auditar_acceso_dte(
            request=request,
            resultado="denegado_tenant",
            recurso=recurso,
            venta_id=venta_id,
            empresa_venta=eid_venta,
            empresa_query=eid_query,
        )
        return "denegado_tenant", 404, _BODY_404

    if eid_query is not None and eid_query != eid_venta:
        auditar_acceso_dte(
            request=request,
            resultado="denegado_empresa",
            recurso=recurso,
            venta_id=venta_id,
            empresa_venta=eid_venta,
            empresa_query=eid_query,
        )
        return "denegado_empresa", 404, _BODY_404

    cg = _qp(request, "codigo_generacion")
    nc = _qp(request, "numero_control")
    if not coincidencia_documento_dte(venta, cg, nc):
        auditar_acceso_dte(
            request=request,
            resultado="denegado_documento",
            recurso=recurso,
            venta_id=venta_id,
            empresa_venta=eid_venta,
            empresa_query=eid_query,
        )
        return "denegado_documento", 404, _BODY_404

    auditar_acceso_dte(
        request=request,
        resultado="ok",
        recurso=recurso,
        venta_id=venta_id,
        empresa_venta=eid_venta,
        empresa_query=eid_query,
    )
    return "ok", 200, {}
