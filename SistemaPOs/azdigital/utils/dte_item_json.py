# Programador: Oscar Amaya Romero
"""
Mapeo de ítems para JSON DTE (Ministerio de Hacienda, El Salvador).
Catálogo 003 — unidad de medida: mh_codigo_unidad del producto (listado en mh_cat003_unidades).
"""
from __future__ import annotations

from typing import Any

from azdigital.utils.conversion_venta import cantidad_para_dte
from azdigital.utils.mh_cat003_unidades import normalizar_codigo_mh


def item_dte_desde_linea(
    descripcion: str,
    cantidad_base: float,
    precio_unitario: float,
    mh_codigo_unidad: str,
    *,
    tributos: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Estructura orientativa para cuerpoDocumento / ítem (ajustar al esquema exacto del MH).
    cantidad: string numérica con hasta 6 decimales (precisión peso / venta por $).
    """
    cod = normalizar_codigo_mh(mh_codigo_unidad)
    cant = cantidad_para_dte(cantidad_base)
    precio = round(float(precio_unitario), 8)
    item: dict[str, Any] = {
        "descripcion": (descripcion or "")[:200],
        "cantidad": cant,
        "precioUnitario": precio,
        "uniMedida": int(cod) if cod.isdigit() else 59,
        "codigoUnidadMedida": cod,
    }
    if tributos:
        item["tributos"] = tributos
    return item
