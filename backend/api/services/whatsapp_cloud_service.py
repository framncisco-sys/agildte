"""
Envío de facturas por WhatsApp Cloud API (Meta) — número único centralizado AgilDTE.

Credenciales maestras: WHATSAPP_PHONE_NUMBER_ID + WHATSAPP_ACCESS_TOKEN (env/settings).
El flag premium por empresa se valida en la capa de vistas/API, no aquí.

Plantilla tipica (agildte_factura / en):
  - Header: DOCUMENT (PDF de la factura)
  - Body: {{1}} nombre, {{2}} empresa, {{3}} enlace
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


def _header_document_enabled() -> bool:
    """Si la plantilla Meta tiene header DOCUMENT, hay que subir el PDF."""
    raw = getattr(settings, 'WHATSAPP_TEMPLATE_HEADER_DOCUMENT', None)
    if raw is None:
        return True
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ('1', 'true', 'yes', 'on')


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
    if '132012' in texto or ('header' in msg.lower() and 'media' in msg.lower()):
        return (
            'La plantilla exige un PDF en el encabezado y no se pudo adjuntar. '
            'Verifique generación del PDF y permisos del token de WhatsApp.'
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


def _sanitizar_nombre_pdf(nombre: str) -> str:
    base = re.sub(r'[^\w.\-]+', '_', (nombre or 'factura').strip())[:80] or 'factura'
    if not base.lower().endswith('.pdf'):
        base = f'{base}.pdf'
    return base


def subir_pdf_media_whatsapp(
    *,
    phone_number_id: str,
    access_token: str,
    pdf_bytes: bytes,
    filename: str = 'factura.pdf',
) -> str:
    """
    Sube un PDF a Graph API y devuelve el media id para el header DOCUMENT de la plantilla.
    POST /{phone-number-id}/media
    """
    if not pdf_bytes:
        raise WhatsAppCloudError('PDF vacío: no se puede subir a WhatsApp.', status_code=400)

    url = f'https://graph.facebook.com/{_graph_version()}/{phone_number_id}/media'
    headers = {'Authorization': f'Bearer {access_token}'}
    files = {
        'file': (_sanitizar_nombre_pdf(filename), pdf_bytes, 'application/pdf'),
    }
    data = {
        'messaging_product': 'whatsapp',
        'type': 'application/pdf',
    }
    try:
        r = requests.post(url, headers=headers, data=data, files=files, timeout=60)
    except requests.RequestException as exc:
        logger.warning('WhatsApp media upload error: %s', exc)
        raise WhatsAppCloudError(f'Error de red al subir PDF a Meta: {exc}', status_code=502) from exc

    try:
        body = r.json() if r.content else {}
    except ValueError:
        body = {'raw': (r.text or '')[:500]}

    if r.status_code >= 400:
        err_msg = _extraer_error_meta(body) or f'Error Meta al subir PDF HTTP {r.status_code}'
        raise WhatsAppCloudError(err_msg, status_code=r.status_code, body=body)

    media_id = body.get('id') if isinstance(body, dict) else None
    if not media_id:
        raise WhatsAppCloudError(
            'Meta no devolvió media id al subir el PDF.',
            status_code=502,
            body=body,
        )
    return str(media_id)


def _generar_pdf_bytes_venta(venta: Venta) -> bytes:
    from api.utils.pdf_generator import generar_pdf_venta

    buffer = generar_pdf_venta(venta)
    if hasattr(buffer, 'getvalue'):
        return buffer.getvalue()
    if hasattr(buffer, 'read'):
        return buffer.read()
    if isinstance(buffer, (bytes, bytearray)):
        return bytes(buffer)
    raise WhatsAppCloudError('No se pudo generar el PDF de la factura.', status_code=500)


def _componentes_plantilla(
    *,
    body_params: int,
    nombre: str,
    empresa: str,
    enlace: str,
    media_id: str | None = None,
    pdf_filename: str = 'factura.pdf',
) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    if media_id:
        components.append(
            {
                'type': 'header',
                'parameters': [
                    {
                        'type': 'document',
                        'document': {
                            'id': media_id,
                            'filename': _sanitizar_nombre_pdf(pdf_filename),
                        },
                    }
                ],
            }
        )

    if body_params >= 3:
        components.append(
            {
                'type': 'body',
                'parameters': [
                    {'type': 'text', 'text': nombre[:1024]},
                    {'type': 'text', 'text': empresa[:1024]},
                    {'type': 'text', 'text': enlace[:1024]},
                ],
            }
        )
    elif body_params >= 2:
        components.append(
            {
                'type': 'body',
                'parameters': [
                    {'type': 'text', 'text': nombre[:1024]},
                    {'type': 'text', 'text': enlace[:1024]},
                ],
            }
        )
    elif body_params == 1:
        components.append(
            {
                'type': 'body',
                'parameters': [
                    {'type': 'text', 'text': nombre[:1024]},
                ],
            }
        )
    return components


def enviar_plantilla_factura_agildte(
    *,
    telefono: str,
    nombre_cliente: str,
    codigo_generacion: str,
    nombre_empresa: str = '',
    pdf_bytes: bytes | None = None,
    pdf_filename: str = 'factura.pdf',
) -> dict[str, Any]:
    """
    Dispara la plantilla oficial de AgilDTE con el número centralizado.

      - telefono: celular del cliente
      - nombre_cliente: {{1}}
      - nombre_empresa: {{2}} si body_params>=3
      - codigo_generacion: nis / enlace ({{3}} o {{2}})
      - pdf_bytes: PDF para header DOCUMENT (requerido si la plantilla lo exige)
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

    media_id = None
    if _header_document_enabled():
        if not pdf_bytes:
            raise WhatsAppCloudError(
                'La plantilla WhatsApp exige PDF en el encabezado y no se generó el archivo.',
                status_code=500,
            )
        media_id = subir_pdf_media_whatsapp(
            phone_number_id=phone_number_id,
            access_token=access_token,
            pdf_bytes=pdf_bytes,
            filename=pdf_filename or f'factura_{nis[:20]}.pdf',
        )

    components = _componentes_plantilla(
        body_params=body_params,
        nombre=nombre,
        empresa=empresa,
        enlace=enlace,
        media_id=media_id,
        pdf_filename=pdf_filename or f'factura_{nis[:20]}.pdf',
    )

    template_body: dict[str, Any] = {
        'name': template_name,
        'language': {'code': language_code},
    }
    if components:
        template_body['components'] = components

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
        'media_id': media_id,
        'meta': meta_resp,
    }


def enviar_factura_whatsapp(
    venta: Venta,
    telefono: str,
    *,
    nombre_cliente: str | None = None,
) -> dict[str, Any]:
    """
    Wrapper sobre venta: genera PDF, extrae nombre/empresa/código y envía la plantilla.
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

    nis = resolver_nis_factura(venta)
    pdf_bytes = None
    pdf_filename = f'factura_{nis[:32]}.pdf'
    if _header_document_enabled():
        try:
            pdf_bytes = _generar_pdf_bytes_venta(venta)
        except WhatsAppCloudError:
            raise
        except Exception as exc:
            logger.exception('Error generando PDF para WhatsApp venta_id=%s', getattr(venta, 'pk', None))
            raise WhatsAppCloudError(
                f'No se pudo generar el PDF de la factura para WhatsApp: {exc}',
                status_code=500,
            ) from exc

    return enviar_plantilla_factura_agildte(
        telefono=telefono,
        nombre_cliente=nombre or 'cliente',
        codigo_generacion=nis,
        nombre_empresa=nombre_empresa,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_filename,
    )
