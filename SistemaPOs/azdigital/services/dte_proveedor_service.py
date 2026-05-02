# Programador: Oscar Amaya Romero
"""Servicio para procesar DTE (JSON) de proveedores — Recepción de Compras."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class DTEProveedorData:
    """Datos extraídos del DTE del proveedor."""
    codigo_generacion: str
    sello_recepcion: str
    numero_control: str
    tipo_dte: str
    numero_documento: str
    fecha_emision: str
    emisor_nombre: str
    emisor_nit: str
    emisor_nrc: str
    receptor_nit: str
    receptor_nrc: str
    total_gravado: float
    total_iva: float
    total: float
    items: list[dict]  # [{descripcion, cantidad, precio_unitario, subtotal, codigo}, ...]
    valido: bool
    error: str = ""


def _get_nested(data: dict, *keys: str, default: Any = "") -> Any:
    """Obtiene valor anidado: _get_nested(d, 'a', 'b', 'c') -> d.get('a',{}).get('b',{}).get('c')"""
    v = data
    for k in keys:
        if isinstance(v, dict) and k in v:
            v = v[k]
        else:
            return default
    return v


def _to_float(val: Any) -> float:
    try:
        return float(val) if val not in (None, "") else 0.0
    except (ValueError, TypeError):
        return 0.0


def extraer_dte_proveedor(json_str: str) -> DTEProveedorData:
    """
    Extrae datos del DTE JSON del proveedor.
    Soporta estructuras según esquemas MH El Salvador.
    """
    vacio = DTEProveedorData(
        codigo_generacion="",
        sello_recepcion="",
        numero_control="",
        tipo_dte="",
        numero_documento="",
        fecha_emision="",
        emisor_nombre="",
        emisor_nit="",
        emisor_nrc="",
        receptor_nit="",
        receptor_nrc="",
        total_gravado=0.0,
        total_iva=0.0,
        total=0.0,
        items=[],
        valido=False,
        error="",
    )
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        vacio.error = f"JSON inválido: {e}"
        return vacio

    if not isinstance(data, dict):
        vacio.error = "El archivo no contiene un objeto JSON válido."
        return vacio

    # Identificación — varias estructuras posibles (MH El Salvador)
    ident = _get_nested(data, "identificacion") or _get_nested(data, "idDocumento") or data
    codigo = ""
    if isinstance(ident, dict):
        codigo = _get_nested(ident, "codigoGeneracion") or _get_nested(data, "codigoGeneracion") or ""
        numero_ctrl = _get_nested(ident, "numeroControl") or _get_nested(ident, "numeroControlDTE") or ""
        tipo = _get_nested(ident, "tipoDte") or _get_nested(ident, "tipoDocumento") or ""
        numero_doc = _get_nested(ident, "numeroDocumento") or _get_nested(ident, "numeroDTE") or ""
        fecha = _get_nested(ident, "fechaEmision") or _get_nested(ident, "fechaEmisionDTE") or ""
    else:
        codigo = _get_nested(data, "codigoGeneracion") or ""
        numero_ctrl = _get_nested(data, "numeroControl") or ""
        tipo = _get_nested(data, "tipoDte") or ""
        numero_doc = _get_nested(data, "numeroDocumento") or ""
        fecha = _get_nested(data, "fechaEmision") or ""

    # Sello de recepción
    sello = _get_nested(data, "selloRecibido") or _get_nested(data, "selloRecepcion") or _get_nested(data, "documentoRelacionado", "selloRecibido") or ""

    # Emisor
    emisor = _get_nested(data, "documento", "emisor") or _get_nested(data, "emisor") or {}
    if isinstance(emisor, dict):
        em_nombre = _get_nested(emisor, "nombre") or _get_nested(emisor, "nombreComercial") or _get_nested(emisor, "nombreEmisor") or ""
        em_nit = _get_nested(emisor, "nit") or _get_nested(emisor, "numeroDocumento") or ""
        em_nrc = _get_nested(emisor, "nrc") or _get_nested(emisor, "numeroRegistro") or ""
    else:
        em_nombre, em_nit, em_nrc = "", "", ""

    # Receptor
    receptor = _get_nested(data, "documento", "receptor") or _get_nested(data, "receptor") or {}
    if isinstance(receptor, dict):
        rec_nit = _get_nested(receptor, "nit") or _get_nested(receptor, "numeroDocumento") or ""
        rec_nrc = _get_nested(receptor, "nrc") or _get_nested(receptor, "numeroRegistro") or ""
    else:
        rec_nit, rec_nrc = "", ""

    # Resumen / totales
    resumen = _get_nested(data, "documento", "resumen") or _get_nested(data, "resumen") or {}
    if isinstance(resumen, dict):
        total_grav = _to_float(_get_nested(resumen, "totalGravada") or _get_nested(resumen, "totalSujetaGravamen") or _get_nested(resumen, "subTotalVentas"))
        total_iva = _to_float(_get_nested(resumen, "totalIva") or _get_nested(resumen, "ivaRete1") or 0)
        total_gen = _to_float(_get_nested(resumen, "totalPagar") or _get_nested(resumen, "totalComprobante") or _get_nested(resumen, "granTotal"))
    else:
        total_grav, total_iva, total_gen = 0.0, 0.0, 0.0

    if total_gen <= 0 and total_grav <= 0:
        cuerpo = _get_nested(data, "documento", "cuerpoDocumento") or _get_nested(data, "cuerpoDocumento") or []
        if isinstance(cuerpo, list) and cuerpo:
            total_gen = sum(_to_float(it.get("montoPagar") or it.get("subTotal") or 0) for it in cuerpo)

    # Items
    cuerpo = _get_nested(data, "documento", "cuerpoDocumento") or _get_nested(data, "cuerpoDocumento") or []
    items = []
    if isinstance(cuerpo, list):
        for it in cuerpo:
            if isinstance(it, dict):
                items.append({
                    "descripcion": str(it.get("descripcion") or it.get("item") or ""),
                    "cantidad": _to_float(it.get("cantidad") or 1),
                    "precio_unitario": _to_float(it.get("precioUnidad") or it.get("precioUnitario") or 0),
                    "subtotal": _to_float(it.get("montoDescu") or it.get("montoPagar") or it.get("subTotal") or 0),
                    "codigo": str(it.get("numeroDocumento") or it.get("codigo") or ""),
                })

    if not codigo:
        vacio.error = "No se encontró codigoGeneracion en el DTE."
        return vacio

    return DTEProveedorData(
        codigo_generacion=str(codigo).strip(),
        sello_recepcion=str(sello).strip() if sello else "",
        numero_control=str(numero_ctrl).strip(),
        tipo_dte=str(tipo).strip(),
        numero_documento=str(numero_doc).strip(),
        fecha_emision=str(fecha).strip()[:10] if fecha else "",
        emisor_nombre=str(em_nombre).strip(),
        emisor_nit=str(em_nit).strip(),
        emisor_nrc=str(em_nrc).strip(),
        receptor_nit=str(rec_nit).strip(),
        receptor_nrc=str(rec_nrc).strip(),
        total_gravado=total_grav,
        total_iva=total_iva,
        total=total_gen or (total_grav + total_iva),
        items=items,
        valido=True,
    )
