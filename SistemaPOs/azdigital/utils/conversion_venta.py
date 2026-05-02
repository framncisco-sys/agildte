# Programador: Oscar Amaya Romero
"""
Conversión de presentación en POS → cantidad en UMB (unidad mínima de bodega).

Invariantes (inventario + Kardex + cobro):
- Toda venta guarda en `venta_detalles` y descuenta stock la **cantidad en UMB** (decimal si aplica).
- Kardex `SALIDA_VENTA` usa la misma cantidad UMB; el ticket muestra presentación con `texto_presentacion_cantidad`.
- UNIDAD / presentación factor 1: cantidad_ui = UMB (sobres, piezas).
- DOCENA: UMB = cantidad_ui × unidades_por_docena (típ. 12).
- CAJA: UMB = cantidad_ui × unidades_por_caja (o factor de `producto_presentacion`).
- MONTO ($) con fraccionable: UMB = monto / precio_unitario (precio siempre por 1 UMB).
- Producto no fraccionable: cantidad UMB debe ser entera (piezas discretas).
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from azdigital.utils.mh_cat003_unidades import sufijo_ticket_cat003


def cantidad_para_dte(cantidad_base: float, decimales: int = 6) -> str:
    """
    Cantidad formateada para JSON DTE (Hacienda): por defecto hasta 6 decimales.
    Para ticket impreso use decimales menores (p. ej. 2–4) vía el mismo helper.
    """
    d = max(0, min(8, int(decimales)))
    step = Decimal(1).scaleb(-d) if d > 0 else Decimal("1")
    q = Decimal(str(cantidad_base)).quantize(step, rounding=ROUND_HALF_UP)
    s = format(q, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def factor_unidad_venta(
    unidad_venta: str,
    unidades_por_caja: int | None,
    unidades_por_docena: int | None,
) -> int:
    u = (unidad_venta or "UNIDAD").strip().upper()
    if u == "UNIDAD":
        return 1
    if u == "DOCENA":
        d = int(unidades_por_docena) if unidades_por_docena and int(unidades_por_docena) > 0 else 12
        return d
    if u == "CAJA":
        if not unidades_por_caja or int(unidades_por_caja) <= 0:
            raise ValueError("Este producto no tiene definidas unidades por caja en Inventario.")
        return int(unidades_por_caja)
    raise ValueError("Unidad de venta inválida (use UNIDAD, DOCENA o CAJA).")


def cantidad_base_desde_ui(
    cantidad_ui: float,
    unidad_venta: str,
    unidades_por_caja: int | None,
    unidades_por_docena: int | None,
) -> float:
    f = factor_unidad_venta(unidad_venta, unidades_por_caja, unidades_por_docena)
    return float(Decimal(str(cantidad_ui)) * Decimal(f))


def cantidad_base_desde_factor(cantidad_ui: float, factor: float) -> float:
    """Cantidad en UMB = cantidad en presentación × factor (respecto a la unidad base)."""
    return float(Decimal(str(cantidad_ui)) * Decimal(str(factor)))


def cantidad_base_venta_por_monto(monto: float, precio_por_unidad_base: float) -> float:
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    if precio_por_unidad_base <= 0:
        raise ValueError("El producto no tiene precio válido por unidad base.")
    return float(
        (Decimal(str(monto)) / Decimal(str(precio_por_unidad_base))).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )
    )


def texto_presentacion_cantidad(
    cantidad_ui: float,
    unidad_venta: str,
    *,
    venta_por_monto: bool = False,
    monto: float | None = None,
    cantidad_base: float | None = None,
    etiqueta_unidad_mh: str = "59",
    nombre_presentacion: str | None = None,
) -> str:
    """Texto para columna CANT en ticket (ej. '1 Caja', '2 Tira', '$1.00 → 0.25 Lb')."""
    if venta_por_monto and monto is not None and cantidad_base is not None:
        suf = sufijo_ticket_cat003(etiqueta_unidad_mh)
        cb = cantidad_para_dte(cantidad_base, decimales=2)
        return f"${float(monto):.2f} ({cb}{suf})"
    nom = (nombre_presentacion or "").strip()
    if nom:
        nf = float(cantidad_ui)
        if nf == 1.0:
            return f"1 {nom}"
        n = int(nf) if nf == int(nf) else nf
        return f"{n} {nom}"
    u = (unidad_venta or "UNIDAD").strip().upper()
    if u == "CAJA":
        nf = float(cantidad_ui)
        if nf == 1.0:
            return "1 Caja"
        n = int(nf) if nf == int(nf) else nf
        return f"{n} Cajas"
    if u == "DOCENA":
        nf = float(cantidad_ui)
        if nf == 1.0:
            return "1 Docena"
        n = int(nf) if nf == int(nf) else nf
        return f"{n} Docenas"
    n = cantidad_ui
    if n == int(n):
        return str(int(n))
    return str(Decimal(str(n)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))

