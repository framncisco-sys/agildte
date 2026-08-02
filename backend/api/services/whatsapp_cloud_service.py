"""
Envío de facturas por WhatsApp Cloud API (Meta) — número único centralizado AgilDTE.

Credenciales maestras: WHATSAPP_PHONE_NUMBER_ID + WHATSAPP_ACCESS_TOKEN (env/settings).
El flag premium por empresa se valida en la capa de vistas/API, no aquí.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import requests
from django.conf import settings

from api.models import Venta

logger = logging.getLogger(__name__)

DEFAULT_GRAPH_VERSION = 'v18.0'
DEFAULT_DOWNLOAD_URL = 'https://agildte.com/api/descargar-factura/?nis={nis}'
DEFAULT_TEMPLATE_NAME = 'agildte_factura'
DEFAULT_TEMPLATE_LANGUAGE = 'en'

# Mensaje canónico cuando la empresa no tiene el módulo premium.
MSG_WHATSAPP_NO_HABILITADO = 'Módulo de WhatsApp no habilitado'


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


def construir_enlace_descarga(codigo_generacion: str) -> str:
    """Arma la URL pública de descarga a partir del código de generación (nis)."""
    nis = (codigo_generacion or '').strip()
    url_tpl = (
        getattr(settings, 'WHATSAPP_FACTURA_DOWNLOAD_URL', None)
        or DEFAULT_DOWNLOAD_URL
    )
    return url_tpl.format(nis=nis)


def construir_mensaje_factura(*, nombre_cliente: str, nis: str) -> str:
    """Texto legible (diagnóstico / fallback). El envío oficial usa plantilla Meta."""
    nombre = (nombre_cliente or 'cliente').strip() or 'cliente'
    enlace = construir_enlace_descarga(nis)
    return (
        f'Estimado {nombre} aqui envio la factura que puede descargar haciendo click '
        f'en el siguiente enlace: {enlace} Gracias por su compra'
    )


def _graph_version() -> str:
    return (
        getattr(settings, 'WHATSAPP_GRAPH_API_VERSION', None) or DEFAULT_GRAPH_VERSION
    ).strip()


def _credenciales_agildte() -> tuple[str, str]:
    """Phone Number ID y token del número único AgilDTE (configuración del servidor)."""
    phone_number_id = (getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None) or '').strip()
    access_token = (getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None) or '').strip()
    if not phone_number_id or not access_token:
        raise WhatsAppCloudError(
            'WhatsApp AgilDTE no configurado: defina WHATSAPP_PHONE_NUMBER_ID y '
            'WHATSAPP_ACCESS_TOKEN en el servidor.',
            status_code=503,
        )
    return phone_number_id, access_token


def _template_config() -> tuple[str, str, int]:
    name = (getattr(settings, 'WHATSAPP_TEMPLATE_NAME', None) or DEFAULT_TEMPLATE_NAME).strip()
    language = (
        getattr(settings, 'WHATSAPP_TEMPLATE_LANGUAGE', None) or DEFAULT_TEMPLATE_LANGUAGE
    ).strip()
    # hello_world: 0 params. agildte_factura: 2 (nombre+enlace) o 3 (nombre+empresa+enlace).
    raw_params = getattr(settings, 'WHATSAPP_TEMPLATE_BODY_PARAMS', None)
    if raw_params is None or str(raw_params).strip() == '':
        body_params = 0 if name.lower() == 'hello_world' else 2
    else:
        try:
            body_params = max(0, int(raw_params))
        except (TypeError, ValueError):
            body_params = 2
    return name, language, body_params


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
    if '132001' in texto or 'template name does not exist' in msg.lower():
        name = getattr(settings, 'WHATSAPP_TEMPLATE_NAME', DEFAULT_TEMPLATE_NAME)
        lang = getattr(settings, 'WHATSAPP_TEMPLATE_LANGUAGE', DEFAULT_TEMPLATE_LANGUAGE)
        return (
            f'La plantilla «{name}» (idioma {lang}) no existe o no está aprobada en Meta. '
            'Créala en Meta Business → WhatsApp → Plantillas de mensaje, o usa '
            'WHATSAPP_TEMPLATE_NAME=hello_world y WHATSAPP_TEMPLATE_LANGUAGE=en_US para pruebas.'
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


def _post_meta_messages(phone_number_id: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f'https://graph.facebook.com/{_graph_version()}/{phone_number_id}/messages'
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


def _message_id_desde_meta(meta_resp: dict[str, Any]) -> str | None:
    msgs = meta_resp.get('messages') if isinstance(meta_resp, dict) else None
    if isinstance(msgs, list) and msgs and isinstance(msgs[0], dict):
        return msgs[0].get('id')
    return None


def enviar_plantilla_factura_agildte(
    *,
    telefono: str,
    nombre_cliente: str,
    codigo_generacion: str,
    nombre_empresa: str = '',
) -> dict[str, Any]:
    """
    Dispara la plantilla oficial de AgilDTE con el número centralizado.

    Solo recibe datos de destino:
      - telefono: celular del cliente
      - nombre_cliente: nombre para {{1}}
      - nombre_empresa: razón social emisora ({{2}} si body_params>=3)
      - codigo_generacion: nis / enlace de descarga

    Plantilla Meta esperada (body, 3 params):
      {{1}} = nombre del cliente
      {{2}} = nombre de la empresa
      {{3}} = URL de descarga
    Con 2 params: {{1}}=nombre, {{2}}=enlace.
    """
    phone_number_id, access_token = _credenciales_agildte()
    to = normalizar_telefono_meta(telefono)
    if not to:
        raise WhatsAppCloudError('Número de teléfono inválido para WhatsApp.', status_code=400)

    nombre = (nombre_cliente or 'cliente').strip() or 'cliente'
    empresa = (nombre_empresa or '').strip() or 'la empresa'
    nis = (codigo_generacion or '').strip()
    if not nis:
        raise WhatsAppCloudError('Falta el código de generación / enlace de descarga.', status_code=400)

    enlace = construir_enlace_descarga(nis)
    template_name, language_code, body_params = _template_config()

    template_body: dict[str, Any] = {
        'name': template_name,
        'language': {'code': language_code},
    }
    if body_params >= 3:
        template_body['components'] = [
            {
                'type': 'body',
                'parameters': [
                    {'type': 'text', 'text': nombre[:1024]},
                    {'type': 'text', 'text': empresa[:1024]},
                    {'type': 'text', 'text': enlace[:1024]},
                ],
            },
        ]
    elif body_params >= 2:
        template_body['components'] = [
            {
                'type': 'body',
                'parameters': [
                    {'type': 'text', 'text': nombre[:1024]},
                    {'type': 'text', 'text': enlace[:1024]},
                ],
            },
        ]
    elif body_params == 1:
        template_body['components'] = [
            {
                'type': 'body',
                'parameters': [
                    {'type': 'text', 'text': nombre[:1024]},
                ],
            },
        ]

    payload: dict[str, Any] = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': to,
        'type': 'template',
        'template': template_body,
    }

    meta_resp = _post_meta_messages(phone_number_id, access_token, payload)
    message_id = _message_id_desde_meta(meta_resp)

    return {
        'ok': True,
        'mensaje': 'Mensaje enviado por WhatsApp.',
        'whatsapp_message_id': message_id,
        'enlace': enlace,
        'meta': meta_resp,
    }


def enviar_factura_whatsapp(
    venta: Venta,
    telefono: str,
    *,
    nombre_cliente: str | None = None,
) -> dict[str, Any]:
    """
    Wrapper sobre venta: extrae nombre, empresa y código de generación y envía la plantilla.
    No valida el flag premium (eso lo hacen las vistas / post_factura).
    """
    if venta.empresa_id is None and getattr(venta, 'empresa', None) is None:
        raise WhatsAppCloudError('La venta no tiene empresa asociada.', status_code=400)

    nombre = nombre_cliente
    if not nombre:
        if venta.cliente_id and venta.cliente:
            nombre = venta.cliente.nombre
        else:
            nombre = venta.nombre_receptor or 'cliente'

    empresa_obj = getattr(venta, 'empresa', None)
    nombre_empresa = ''
    if empresa_obj is not None:
        nombre_empresa = (
            (getattr(empresa_obj, 'nombre_comercial', None) or '').strip()
            or (getattr(empresa_obj, 'nombre', None) or '').strip()
        )

    return enviar_plantilla_factura_agildte(
        telefono=telefono,
        nombre_cliente=nombre or 'cliente',
        codigo_generacion=resolver_nis_factura(venta),
        nombre_empresa=nombre_empresa,
    )
