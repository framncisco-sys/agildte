"""Envío opcional de WhatsApp tras correo de factura aceptada por MH."""
from __future__ import annotations

import logging

from ..models import Venta
from .whatsapp_cloud_service import WhatsAppCloudError, enviar_factura_whatsapp

logger = logging.getLogger(__name__)


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


def parse_enviar_whatsapp_desde_request(request_data, *, telefono_formulario: str = '') -> tuple[bool, str]:
    """Lee enviar_whatsapp y teléfono desde el body del POST crear-con-detalles."""
    enviar = _coerce_bool(request_data.get('enviar_whatsapp'))
    telefono = (
        (request_data.get('whatsapp_telefono') or request_data.get('telefono_whatsapp') or telefono_formulario or '')
        .strip()
    )
    return enviar, telefono


def enviar_whatsapp_tras_correo_si_aplica(
    venta: Venta,
    *,
    enviar: bool,
    telefono: str,
) -> str | None:
    """
    Envía WhatsApp si está pedido y la empresa tiene premium.
    Retorna None si no aplica o éxito; mensaje de error si falla Meta.
    """
    if not enviar:
        return None
    if not telefono:
        return 'WhatsApp: falta teléfono del cliente.'
    empresa = venta.empresa
    if not empresa or not empresa.whatsapp_premium_enabled:
        return 'WhatsApp premium no habilitado para esta empresa.'
    try:
        enviar_factura_whatsapp(venta, telefono)
        return None
    except WhatsAppCloudError as exc:
        logger.warning('WhatsApp post-correo venta %s: %s', venta.pk, exc)
        return str(exc)
