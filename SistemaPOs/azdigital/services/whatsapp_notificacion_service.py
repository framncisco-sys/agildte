# Programador: Oscar Amaya Romero
"""
Notificación de comprobante por WhatsApp al cliente con teléfono en el catálogo.

- Sin API: se genera enlace wa.me y el POS puede abrirlo automáticamente (el cliente confirma envío en WhatsApp).
- Con Twilio (opcional): variables TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM
  (ej. whatsapp:+14155238886 en sandbox) envían el mensaje sin abrir el navegador.
"""
from __future__ import annotations

import base64
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from azdigital.repositories import ventas_repo
from azdigital.services.dte_json_venta_mh import construir_json_dte_mh_venta
from azdigital.utils.ticket_publico_token import firmar_acceso_publico_venta

logger = logging.getLogger(__name__)


def _base_publica_para_enlaces(base_url: str) -> str:
    """
    Si el servidor corre en localhost, los enlaces en WhatsApp no sirven al cliente.
    Usar PUBLIC_BASE_URL o AZ_PUBLIC_BASE_URL (https://su-dominio.com sin barra final).
    """
    b = (base_url or "").strip().rstrip("/")
    low = b.lower()
    es_local = (
        not b
        or "127.0.0.1" in low
        or "localhost" in low
        or "0.0.0.0" in low
        or "[::1]" in low
    )
    if es_local:
        env = (os.environ.get("PUBLIC_BASE_URL") or os.environ.get("AZ_PUBLIC_BASE_URL") or "").strip().rstrip("/")
        if env:
            return env
    return b


def _montos_y_dte_desde_fila_venta(vr: tuple | None) -> tuple[float, str, str]:
    """(total a pagar aprox., código generación, número control) desde get_venta."""
    if not vr:
        return 0.0, "", ""
    tot = float(vr[2] or 0)
    ret = float(vr[11] or 0) if len(vr) > 11 else 0.0
    total_pagar = tot - ret
    cg = (vr[14] or "").strip() if len(vr) > 14 else ""
    nc = (vr[15] or "").strip() if len(vr) > 15 else ""
    return total_pagar, cg, nc


def normalizar_telefono_whatsapp_sv(telefono: str) -> str | None:
    """
    Devuelve solo dígitos con código país 503 para wa.me (sin +).
    Acepta 8 dígitos locales o 503 + 8 dígitos.
    """
    raw = (telefono or "").strip()
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 8:
        return "503" + digits
    if digits.startswith("503") and len(digits) >= 11:
        return digits[:11] if len(digits) > 11 else digits
    if len(digits) >= 10:
        return digits
    return None


def _etiqueta_comprobante(tipo_comp: str) -> str:
    t = (tipo_comp or "").strip().upper()
    if t == "CREDITO_FISCAL":
        return "Comprobante de Crédito Fiscal (CCF)"
    if t == "FACTURA":
        return "Factura consumidor final"
    return "Ticket / comprobante"


def _intentar_twilio_texto(numero_digits: str, mensaje: str) -> bool:
    sid = (os.environ.get("TWILIO_ACCOUNT_SID") or "").strip()
    token = (os.environ.get("TWILIO_AUTH_TOKEN") or "").strip()
    from_wa = (os.environ.get("TWILIO_WHATSAPP_FROM") or "").strip()
    if not sid or not token or not from_wa:
        return False
    to_wa = "whatsapp:+" + numero_digits
    if not from_wa.startswith("whatsapp:"):
        from_wa = "whatsapp:" + from_wa.replace("whatsapp:", "").lstrip("+")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    body = urllib.parse.urlencode(
        {"From": from_wa, "To": to_wa, "Body": mensaje[:1600]}
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    cred = f"{sid}:{token}".encode("utf-8")
    req.add_header("Authorization", "Basic " + base64.b64encode(cred).decode("ascii"))
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        logger.warning("Twilio WhatsApp HTTPError: %s %s", e.code, e.read()[:500])
    except Exception as e:
        logger.warning("Twilio WhatsApp error: %s", e)
    return False


def preparar_envio_whatsapp_venta(
    cur,
    venta_id: int,
    empresa_id: int,
    telefono_cliente: str,
    tipo_comprobante: str,
    base_url: str,
    secret_key: str,
    nombre_comercial_corto: str,
) -> dict[str, Any]:
    """
    Arma enlaces públicos, JSON MH y mensaje; intenta Twilio si está configurado.
    """
    digits = normalizar_telefono_whatsapp_sv(telefono_cliente)
    out: dict[str, Any] = {
        "ok": False,
        "motivo": "tel_invalido",
        "twilio_enviado": False,
        "wa_me_url": None,
        "url_comprobante": None,
        "url_json_mh": None,
    }
    if not digits:
        out["motivo"] = "telefono_vacio_o_invalido"
        out["detalle"] = (
            "El teléfono del cliente no es válido para WhatsApp. Use 8 dígitos locales o 503 + número."
        )
        return out

    token = firmar_acceso_publico_venta(secret_key, venta_id, empresa_id)
    base = _base_publica_para_enlaces(base_url)
    if not base:
        base = (base_url or "").strip().rstrip("/")
    lowb = base.lower()
    if "127.0.0.1" in lowb or "localhost" in lowb:
        logger.warning(
            "WhatsApp: los enlaces públicos usan host local (%s). "
            "Defina PUBLIC_BASE_URL en .env (ej. https://factura.suempresa.com) para que el cliente abra el comprobante.",
            base,
        )
    path_c = f"/publico/comprobante/{venta_id}?t={urllib.parse.quote(token, safe='')}"
    path_j = f"/publico/dte_json/{venta_id}?t={urllib.parse.quote(token, safe='')}"
    url_c = base + path_c
    url_j = base + path_j

    fila_v = ventas_repo.get_venta(cur, venta_id, empresa_id=None)
    total_fb, cg_fb, nc_fb = _montos_y_dte_desde_fila_venta(fila_v)

    json_mh = construir_json_dte_mh_venta(cur, venta_id, empresa_id) or {}
    iden = json_mh.get("identificacion") or {}
    res = json_mh.get("resumen") or {}

    raw_tp = res.get("totalPagar")
    if raw_tp is None:
        raw_tp = res.get("montoTotalOperacion")
    try:
        total_num = float(raw_tp) if raw_tp is not None else None
    except (TypeError, ValueError):
        total_num = None
    if total_num is None or (total_num == 0 and total_fb > 0):
        total_num = total_fb

    cg_raw = iden.get("codigoGeneracion")
    cg = (str(cg_raw).strip() if cg_raw is not None else "") or cg_fb or "—"
    nc_raw = iden.get("numeroControl")
    nc = (str(nc_raw).strip() if nc_raw is not None else "") or nc_fb or "—"

    total_fmt = f"{float(total_num or 0):,.2f}"

    etiqueta = _etiqueta_comprobante(tipo_comprobante)
    negocio = (nombre_comercial_corto or "AZ DIGITAL").strip()[:80]
    mensaje = (
        f"*{negocio}*\n"
        f"{etiqueta}\n"
        f"N.º interno: {venta_id}\n"
        f"Código generación MH: {cg}\n"
        f"N.º control: {nc}\n"
        f"Total: ${total_fmt}\n\n"
        f"Ver comprobante (PDF/imprimir):\n{url_c}\n\n"
        f"JSON formato MH:\n{url_j}"
    )

    twilio_ok = _intentar_twilio_texto(digits, mensaje)
    wa_me = "https://wa.me/" + digits + "?text=" + urllib.parse.quote(mensaje, safe="")

    out.update(
        {
            "ok": True,
            "motivo": "listo",
            "twilio_enviado": twilio_ok,
            "wa_me_url": wa_me,
            "url_comprobante": url_c,
            "url_json_mh": url_j,
        }
    )
    return out
