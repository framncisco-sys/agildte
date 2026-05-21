"""
Envío de facturas por WhatsApp Cloud API (Meta) — exclusivo AgilDTE backend.

Documentación: https://developers.facebook.com/docs/whatsapp/cloud-api/messages/text-messages
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import requests

from api.models import Empresa, Venta

logger = logging.getLogger(__name__)

DEFAULT_GRAPH_VERSION = 'v18.0'
DEFAULT_DOWNLOAD_URL = (
    'https://edesaldocs.com/descargar-factura.php?nis={nis}'
)


class WhatsAppCloudError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def normalizar_telefono_meta(telefono: str) -> str | None:
    """E.164 sin '+' para el campo `to` de Meta (El Salvador: 503 + 8 dígitos)."""
    raw = (telefono or '').strip()
    if not raw:
        return None
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 8:
        return '503' + digits
    if digits.startswith('503') and len(digits) == 11:
        return digits
    if digits.startswith('00503') and len(digits) >= 13:
        return digits[-11:]
    if len(digits) >= 11:
        return digits
    return None


def resolver_nis_factura(venta: Venta) -> str:
    """Identificador en el enlace de descarga (código de generación MH o id interno)."""
    cg = (getattr(venta, 'codigo_generacion', None) or '').strip()
    if cg:
        return cg
    return str(venta.pk)


def construir_mensaje_factura(*, nombre_cliente: str, nis: str) -> str:
    nombre = (nombre_cliente or 'cliente').strip() or 'cliente'
    url_tpl = (
        os.environ.get('WHATSAPP_FACTURA_DOWNLOAD_URL')
        or DEFAULT_DOWNLOAD_URL
    )
    enlace = url_tpl.format(nis=nis)
    return (
        f'Estimado {nombre} aqui envio la factura que puede descargar haciendo click '
        f'en el siguiente enlace: {enlace} Gracias por su compra'
    )


def _graph_version() -> str:
    return (os.environ.get('WHATSAPP_GRAPH_API_VERSION') or DEFAULT_GRAPH_VERSION).strip()


def enviar_mensaje_texto_meta(
    empresa: Empresa,
    telefono_destino: str,
    cuerpo: str,
) -> dict[str, Any]:
    """
    POST /{phone_number_id}/messages con credenciales de la empresa.
    Retorna el JSON de Meta (messages[0].id, etc.).
    """
    if not empresa.whatsapp_premium_enabled:
        raise WhatsAppCloudError(
            'WhatsApp premium no está habilitado para esta empresa.',
            status_code=403,
        )

    phone_number_id = (empresa.whatsapp_phone_number_id or '').strip()
    access_token = (empresa.whatsapp_access_token or '').strip()
    if not phone_number_id or not access_token:
        raise WhatsAppCloudError(
            'Configure whatsapp_phone_number_id y whatsapp_access_token en la empresa.',
            status_code=400,
        )

    to = normalizar_telefono_meta(telefono_destino)
    if not to:
        raise WhatsAppCloudError('Número de teléfono inválido para WhatsApp.', status_code=400)

    url = f'https://graph.facebook.com/{_graph_version()}/{phone_number_id}/messages'
    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': to,
        'type': 'text',
        'text': {
            'preview_url': True,
            'body': (cuerpo or '')[:4096],
        },
    }
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.RequestException as exc:
        logger.warning('WhatsApp Cloud request error: %s', exc)
        raise WhatsAppCloudError(f'Error de red al contactar Meta: {exc}', status_code=502) from exc

    try:
        data = r.json() if r.content else {}
    except ValueError:
        data = {'raw': (r.text or '')[:500]}

    if r.status_code >= 400:
        err_msg = _extraer_error_meta(data) or f'Error Meta HTTP {r.status_code}'
        raise WhatsAppCloudError(err_msg, status_code=r.status_code, body=data)

    return data if isinstance(data, dict) else {'response': data}


def _mensaje_error_meta_amigable(data: Any, raw_message: str) -> str:
    """Traduce códigos frecuentes de Meta a instrucciones operativas."""
    msg = (raw_message or '').strip()
    code = None
    subcode = None
    if isinstance(data, dict):
        err = data.get('error')
        if isinstance(err, dict):
            code = err.get('code')
            subcode = err.get('error_subcode')
    texto = f'{msg} {code} {subcode}'
    if '131030' in texto or 'not in allowed list' in msg.lower():
        return (
            'El número del cliente no está en la lista permitida de Meta. '
            'En modo desarrollo/prueba: Meta Business → WhatsApp → API Setup → '
            '«To» / números de prueba, agrega el celular en formato 503XXXXXXXX.'
        )
    return msg[:500] if msg else 'Error al enviar mensaje por WhatsApp (Meta).'


def _extraer_error_meta(data: Any) -> str:
    if not isinstance(data, dict):
        return ''
    err = data.get('error')
    if isinstance(err, dict):
        raw = str(err.get('message') or err.get('error_user_msg') or err)
        return _mensaje_error_meta_amigable(data, raw)
    raw = str(data.get('message') or data)
    return _mensaje_error_meta_amigable(data, raw)


def enviar_factura_whatsapp(
    venta: Venta,
    telefono: str,
    *,
    nombre_cliente: str | None = None,
) -> dict[str, Any]:
    """
    Envía el mensaje de factura para una venta usando la empresa asociada.
    """
    empresa = venta.empresa
    if empresa is None:
        raise WhatsAppCloudError('La venta no tiene empresa asociada.', status_code=400)

    nombre = nombre_cliente
    if not nombre:
        if venta.cliente_id and venta.cliente:
            nombre = venta.cliente.nombre
        else:
            nombre = venta.nombre_receptor or 'cliente'

    nis = resolver_nis_factura(venta)
    mensaje = construir_mensaje_factura(nombre_cliente=nombre or 'cliente', nis=nis)
    meta_resp = enviar_mensaje_texto_meta(empresa, telefono, mensaje)

    message_id = None
    msgs = meta_resp.get('messages') if isinstance(meta_resp, dict) else None
    if isinstance(msgs, list) and msgs and isinstance(msgs[0], dict):
        message_id = msgs[0].get('id')

    return {
        'ok': True,
        'mensaje': 'Mensaje enviado por WhatsApp.',
        'whatsapp_message_id': message_id,
        'meta': meta_resp,
    }
