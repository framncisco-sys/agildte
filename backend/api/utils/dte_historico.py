"""Lectura inmutable del DTE histórico almacenado como JWS."""
from __future__ import annotations

import base64
import json
from typing import Any


def decodificar_payload_jws(jws: str | bytes | None) -> dict[str, Any] | None:
    """Extrae el payload original sin verificar la firma ni regenerar el DTE."""
    if not jws:
        return None
    try:
        texto = jws.decode('utf-8') if isinstance(jws, bytes) else str(jws)
        partes = texto.strip().split('.')
        if len(partes) < 2:
            return None
        payload = partes[1]
        payload += '=' * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload).decode('utf-8'))
        return data if isinstance(data, dict) else None
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def obtener_dte_historico(venta, *, incluir_constancias: bool = True) -> dict[str, Any] | None:
    """
    Devuelve una copia del JSON originalmente firmado y aceptado por MH.

    Nunca usa builders actuales. Si la venta no conserva un JWS decodificable,
    retorna None para que el llamador decida si permite una reconstrucción.
    """
    payload = decodificar_payload_jws(getattr(venta, 'dte_firmado', None))
    if payload is None:
        return None

    documento = dict(payload)
    if incluir_constancias:
        documento['firmaElectronica'] = getattr(venta, 'dte_firmado', None)
        sello = (getattr(venta, 'sello_recepcion', None) or '').strip()
        if sello:
            documento['selloRecibido'] = sello
    return documento
