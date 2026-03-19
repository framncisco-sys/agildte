from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterable, Dict, Any

from api.models import Empresa, Venta


TZ_SV = timezone(timedelta(hours=-6))


def _nit_limpio(empresa: Empresa) -> str:
    nit_raw = (empresa.nit or empresa.nrc or "").strip()
    nit_raw = re.sub(r"[^0-9]", "", nit_raw)
    if len(nit_raw) >= 14:
        return nit_raw[:14]
    if len(nit_raw) >= 9:
        return nit_raw[:9]
    return nit_raw.zfill(9)


def _tipo_doc_responsable(descriptor: str | None) -> str:
    """
    CAT-22: 36-NIT, 13-DUI, 02-Carnet, 03-Pasaporte, 37-Otro.
    """
    if not descriptor:
        return "36"
    t = descriptor.upper()
    if t == "NIT":
        return "36"
    if t == "DUI":
        return "13"
    if t in ("PASAPORTE", "PASSPORT"):
        return "03"
    if "CARNET" in t:
        return "02"
    return "37"


def generar_reporte_contingencia(
    empresa: Empresa,
    ventas: Iterable[Venta],
    *,
    ambiente_mh: str,
    f_inicio: datetime,
    f_fin: datetime,
    tipo_contingencia: int,
    motivo: str | None = None,
    nombre_responsable: str | None = None,
    tipo_doc_responsable: str | None = None,
    numero_doc_responsable: str | None = None,
) -> Dict[str, Any]:
    """
    Genera el JSON del reporte de contingencia que cumple contingencia-schema-v3.json.
    - ambiente_mh: '00' Pruebas, '01' Producción (según schema de contingencia).
    - f_inicio / f_fin: datetimes en TZ SV.
    """
    if ambiente_mh not in ("00", "01"):
        ambiente_mh = "00"

    ahora_sv = datetime.now(TZ_SV)
    f_tx = ahora_sv.strftime("%Y-%m-%d")
    h_tx = ahora_sv.strftime("%H:%M:%S")

    if f_inicio.tzinfo:
        f_inicio = f_inicio.astimezone(TZ_SV)
    if f_fin.tzinfo:
        f_fin = f_fin.astimezone(TZ_SV)

    f_inicio_str = f_inicio.strftime("%Y-%m-%d")
    h_inicio_str = f_inicio.strftime("%H:%M:%S")
    f_fin_str = f_fin.strftime("%Y-%m-%d")
    h_fin_str = f_fin.strftime("%H:%M:%S")

    codigo_generacion = str(uuid.uuid4()).upper()

    nit = _nit_limpio(empresa)
    nombre_emisor = (empresa.nombre or "Empresa").strip()
    if len(nombre_emisor) < 5:
        nombre_emisor = (nombre_emisor + " " * 5)[:5]

    nombre_resp = (nombre_responsable or empresa.nombre or "Responsable").strip()
    if len(nombre_resp) < 5:
        nombre_resp = "Responsable"

    tipo_doc_resp_cat22 = _tipo_doc_responsable(tipo_doc_responsable or "NIT")

    num_doc_resp = (numero_doc_responsable or empresa.nit or empresa.nrc or "0").replace("-", "").replace(" ", "")
    if len(num_doc_resp) < 5:
        num_doc_resp = num_doc_resp.zfill(9)

    cod_est_mh = (empresa.cod_establecimiento or "M001").strip()[:4] or "M001"
    cod_pv = (empresa.cod_punto_venta or "P001").strip()[:15] or "P001"

    telefono = (empresa.telefono or "00000000").strip()
    if len(telefono) < 8:
        telefono = "00000000"
    correo = (empresa.correo or "contacto@empresa.sv").strip()[:100] or "contacto@empresa.sv"

    detalle_items = []
    tipo_map = {"CF": "01", "CCF": "03", "NC": "05", "ND": "06", "FSE": "14"}
    for idx, v in enumerate(ventas, start=1):
        if not v.codigo_generacion:
            continue
        tipo_doc = tipo_map.get(v.tipo_venta, "03")
        detalle_items.append(
            {
                "noItem": idx,
                "codigoGeneracion": str(v.codigo_generacion).upper(),
                "tipoDoc": tipo_doc,
            }
        )

    if not detalle_items:
        raise ValueError("No hay DTE con codigoGeneracion para incluir en el reporte de contingencia.")

    reporte = {
        "identificacion": {
            "version": 3,
            "ambiente": ambiente_mh,
            "codigoGeneracion": codigo_generacion,
            "fTransmision": f_tx,
            "hTransmision": h_tx,
        },
        "emisor": {
            "nit": nit,
            "nombre": nombre_emisor[:250],
            "nombreResponsable": nombre_resp[:100],
            "tipoDocResponsable": tipo_doc_resp_cat22,
            "numeroDocResponsable": num_doc_resp[:25],
            "tipoEstablecimiento": "01",
            "codEstableMH": cod_est_mh[:4],
            "codPuntoVenta": cod_pv[:15],
            "telefono": telefono[:30],
            "correo": correo,
        },
        "detalleDTE": detalle_items,
        "motivo": {
            "fInicio": f_inicio_str,
            "fFin": f_fin_str,
            "hInicio": h_inicio_str,
            "hFin": h_fin_str,
            "tipoContingencia": int(tipo_contingencia),
            "motivoContingencia": (motivo or None)[:500] if motivo else None,
        },
    }
    return reporte

