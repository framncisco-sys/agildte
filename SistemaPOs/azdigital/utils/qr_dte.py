# Programador: Oscar Amaya Romero
"""Genera código QR para consulta DTE en el portal del MH de El Salvador."""

from __future__ import annotations

import base64
import io
from urllib.parse import urlencode

try:
    import qrcode
    QR_DISPONIBLE = True
except ImportError:
    QR_DISPONIBLE = False


def _url_consulta_publica(codigo_generacion: str, fecha_emi: str | None = None) -> str:
    """Consulta pública oficial (admin.factura.gob.sv), ambiente 01 producción según MH."""
    p: dict[str, str] = {'ambiente': '01', 'codGen': str(codigo_generacion).strip()}
    if fecha_emi:
        p['fechaEmi'] = str(fecha_emi).strip()[:10]
    return f"https://admin.factura.gob.sv/consultaPublica?{urlencode(p)}"


def url_consulta_publica_dte(codigo_generacion: str, fecha_emi: str | None = None) -> str:
    """
    URL de consulta pública del DTE en el portal del MH (mismo destino que codifica el QR).
    Útil para mostrar el enlace en texto en el ticket si no hay librería qrcode.
    """
    return _url_consulta_publica(codigo_generacion, fecha_emi=fecha_emi)


def generar_qr_dte_base64(
    codigo_generacion: str,
    tamano: int = 4,
    borde: int = 1,
    *,
    fecha_emi: str | None = None,
) -> str | None:
    """
    Genera un QR que apunta a la consulta del DTE en el MH.
    Retorna la imagen en base64 data URI (listo para usar en <img src="...">)
    o None si qrcode no está instalado o codigo_generacion está vacío.
    """
    if not QR_DISPONIBLE or not codigo_generacion or not str(codigo_generacion).strip():
        return None
    cod = str(codigo_generacion).strip()
    url = _url_consulta_publica(cod, fecha_emi=fecha_emi)
    try:
        qr = qrcode.QRCode(version=1, box_size=tamano, border=borde)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None
