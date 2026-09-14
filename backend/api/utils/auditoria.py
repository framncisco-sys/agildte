"""Bitácora de accesos y fallos de factura. Nunca guarda contraseñas."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def client_ip(request) -> str:
    if request is None:
        return ""
    meta = getattr(request, "META", None) or {}
    xff = (meta.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff:
        return xff.split(",")[0].strip()[:45]
    real = (meta.get("HTTP_X_REAL_IP") or "").strip()
    if real:
        return real[:45]
    return (meta.get("REMOTE_ADDR") or "").strip()[:45]


def registrar_evento(
    *,
    evento: str,
    username: str = "",
    detalle: str = "",
    request: Any = None,
    venta_id: int | None = None,
    empresa_id: int | None = None,
) -> None:
    """Inserta un registro. Si falla la bitácora, no interrumpe login ni facturación."""
    try:
        from api.models import RegistroAuditoria

        ua = ""
        if request is not None:
            ua = ((getattr(request, "META", None) or {}).get("HTTP_USER_AGENT") or "")[:500]
        RegistroAuditoria.objects.create(
            evento=(evento or "")[:40],
            username=(username or "")[:150],
            ip_address=client_ip(request),
            user_agent=ua,
            detalle=(detalle or "")[:4000],
            venta_id=venta_id,
            empresa_id=empresa_id,
        )
    except Exception:
        logger.exception("No se pudo guardar registro de auditoría (%s)", evento)
