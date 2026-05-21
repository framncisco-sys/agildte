"""
Prueba aislada de WhatsApp Cloud API (Meta) — SIN Django ni variables .env.

Simula credenciales dinámicas por empresa (token y phone_id desde BD).

Ejecutar (reemplaza TOKEN, PHONE_ID y TARGET abajo):

  cd backend
  python test_whatsapp_cloud.py

Dentro de Docker:

  docker compose -f docker-compose.prod.yml exec backend python test_whatsapp_cloud.py

Requisitos: pip install requests
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any

import requests

GRAPH_API_VERSION = 'v18.0'
DEFAULT_TEMPLATE = 'hello_world'
DEFAULT_LANGUAGE = 'en_US'


def normalizar_numero_meta(telefono: str) -> str | None:
    """E.164 sin '+' para el campo `to` (El Salvador: 503 + 8 dígitos)."""
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


def verificar_credenciales_meta(
    token: str,
    phone_id: str,
    *,
    graph_version: str = GRAPH_API_VERSION,
) -> dict[str, Any]:
    """
    Comprueba token + Phone Number ID antes de enviar mensajes.
    GET /{phone-id}?fields=... — si falla con 401, el token está mal o expiró.
    """
    access_token = (token or '').strip()
    phone_number_id = (phone_id or '').strip()
    if not access_token or not phone_number_id:
        return {'ok': False, 'error': 'token o phone_id vacío'}

    url = (
        f'https://graph.facebook.com/{graph_version}/{phone_number_id}'
        '?fields=id,display_phone_number,verified_name,quality_rating'
    )
    print(f'\n--- Diagnóstico (GET phone number) ---\nGET {url.split("?")[0]}?fields=...')
    try:
        r = requests.get(url, params={'access_token': access_token}, timeout=20)
    except requests.RequestException as exc:
        return {'ok': False, 'error': f'Error de red: {exc}'}

    try:
        data = r.json() if r.content else {}
    except ValueError:
        data = {'raw': (r.text or '')[:500]}

    print(f'HTTP {r.status_code}')
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if r.status_code == 401:
        return {
            'ok': False,
            'error': (
                'Token inválido o expirado (OAuth 190). Genera un token nuevo en '
                'Meta → WhatsApp → API Setup, o un token permanente de System User '
                'con permiso whatsapp_business_messaging.'
            ),
            'response': data,
        }
    if r.status_code >= 400:
        err = data.get('error', data) if isinstance(data, dict) else data
        msg = err.get('message', str(err)) if isinstance(err, dict) else str(err)
        return {'ok': False, 'error': msg, 'response': data}

    return {'ok': True, 'phone': data}


def testWhatsAppConnection(
    token: str,
    phoneId: str,
    targetNumber: str,
    *,
    graph_version: str = GRAPH_API_VERSION,
    template_name: str = DEFAULT_TEMPLATE,
    language_code: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    """
    Envía la plantilla de prueba hello_world de Meta.

    Args:
        token: Access token permanente de la app (como whatsapp_access_token en BD).
        phoneId: Phone Number ID (como whatsapp_phone_number_id en BD).
        targetNumber: Celular destino (8 dígitos SV o 503XXXXXXXX).

    Returns:
        dict con ok, status_code, to, message_id, response o error.
    """
    access_token = (token or '').strip()
    phone_number_id = (phoneId or '').strip()
    to = normalizar_numero_meta(targetNumber)

    if not access_token:
        return {'ok': False, 'error': 'token vacío'}
    if not phone_number_id:
        return {'ok': False, 'error': 'phoneId vacío'}
    if not to:
        return {'ok': False, 'error': f'número inválido: {targetNumber!r}'}

    url = f'https://graph.facebook.com/{graph_version}/{phone_number_id}/messages'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    body = {
        'messaging_product': 'whatsapp',
        'to': to,
        'type': 'template',
        'template': {
            'name': template_name,
            'language': {'code': language_code},
        },
    }

    print(f'\nPOST {url}')
    print(f'to={to}  template={template_name}  lang={language_code}')
    print('body:', json.dumps(body, indent=2, ensure_ascii=False))

    try:
        r = requests.post(url, json=body, headers=headers, timeout=30)
    except requests.RequestException as exc:
        return {'ok': False, 'error': f'Error de red: {exc}'}

    try:
        data = r.json() if r.content else {}
    except ValueError:
        data = {'raw': (r.text or '')[:1000]}

    print(f'\nHTTP {r.status_code}')
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if r.status_code >= 400:
        err = data.get('error') if isinstance(data, dict) else data
        msg = err.get('message', str(err)) if isinstance(err, dict) else str(data)
        if r.status_code == 401 or (isinstance(err, dict) and err.get('code') == 190):
            msg += (
                '\n→ Token rechazado por Meta. Usa un token recién generado (API Setup) '
                'o permanente de System User. No uses App Secret ni token de usuario Facebook.'
            )
        if '131030' in str(data) or 'not in allowed list' in msg.lower():
            msg += (
                '\n→ Agrega este número en Meta Business → WhatsApp → API Setup → '
                'números de prueba (modo desarrollo).'
            )
        return {
            'ok': False,
            'status_code': r.status_code,
            'to': to,
            'error': msg,
            'response': data,
        }

    message_id = None
    msgs = data.get('messages') if isinstance(data, dict) else None
    if isinstance(msgs, list) and msgs and isinstance(msgs[0], dict):
        message_id = msgs[0].get('id')

    return {
        'ok': True,
        'status_code': r.status_code,
        'to': to,
        'message_id': message_id,
        'response': data,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sustituye con los valores de Django Admin → Empresa (WhatsApp Cloud API)
# y el celular donde quieres recibir hello_world (debe estar en lista de prueba Meta).
# ─────────────────────────────────────────────────────────────────────────────
TOKEN = 'EAAZAmfdbRYs0BRk4AScwz6Fi2dvlDqQDZAxQDgcClXJKyTyhEoi6eNWqNK17qmSSyCGX5tmS629ZAvrF5eZCgS9sGTwgBHwHrXTbXs2BgUkT93YNvzo1qcpk67GLpWoO5MoZADPa9ZAKcZCWP2ezULsRa4gvX1nngZAEWgYlE9tUr0MhjIZCmhoUgHd33Lu5iAZB3WpvFEtTp6eEuy3on67tmErhtRdOg9v7oP9WBHfQkDe9MgPPJwYBk4CwfBeziWXIAZCUX9JqOWVP8QnhAyAspqjZCfT94cJAR8csl9sZD'
PHONE_ID = '1128546427010891'
TARGET = '50378966925'  # 8 dígitos o con prefijo 503


def main() -> int:
    if 'PEGAR_AQUI' in TOKEN or 'PEGAR_AQUI' in PHONE_ID:
        print(
            'Edita TOKEN, PHONE_ID y TARGET al final de test_whatsapp_cloud.py '
            'y vuelve a ejecutar.',
            file=sys.stderr,
        )
        return 1

    diag = verificar_credenciales_meta(TOKEN, PHONE_ID)
    if not diag.get('ok'):
        print(f"\n✗ Credenciales: {diag.get('error')}", file=sys.stderr)
        return 1

    phone_info = diag.get('phone') or {}
    print(f"✓ Phone ID válido: {phone_info.get('display_phone_number') or PHONE_ID}")

    result = testWhatsAppConnection(TOKEN, PHONE_ID, TARGET)
    if result.get('ok'):
        print(f"\n✓ Mensaje enviado. message_id={result.get('message_id')}")
        return 0
    print(f"\n✗ Falló: {result.get('error')}", file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
