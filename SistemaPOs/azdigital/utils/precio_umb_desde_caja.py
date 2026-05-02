# Programador: Oscar Amaya Romero
"""Deriva precio y costo por UMB desde precio/costo por presentación comercial y factor UMB."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def presentacion_tiene_monto_derivable(s: str | None) -> bool:
    """True si el campo trae un monto distinto de cero (0.00 no cuenta: evita pisar el UMB al editar productos sin precio)."""
    t = (s or "").strip().replace(",", ".")
    if not t:
        return False
    try:
        return Decimal(t) != 0
    except Exception:
        return True


def aplicar_derivacion_desde_presentacion(
    precio_presentacion_str: str | None,
    costo_presentacion_str: str | None,
    factor_umb: float | int | None,
    precio_umb_fallback: float,
    costo_umb_fallback: float,
) -> tuple[float, float]:
    """
    Si hay texto en precio/costo por presentación y factor_umb > 0,
    precio_umb = precio_presentación / factor, costo_umb = costo_presentación / factor.
    Si un campo de presentación viene vacío, se conserva el fallback correspondiente.
    """
    out_p = float(precio_umb_fallback or 0)
    out_c = float(costo_umb_fallback or 0)
    if factor_umb is None:
        return out_p, out_c
    try:
        n = Decimal(str(float(factor_umb)))
    except (TypeError, ValueError):
        return out_p, out_c
    if n <= 0:
        return out_p, out_c
    ps = (precio_presentacion_str or "").strip().replace(",", ".")
    if ps:
        try:
            pc = Decimal(ps)
            if pc != 0:
                out_p = float((pc / n).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
        except Exception:
            pass
    cs = (costo_presentacion_str or "").strip().replace(",", ".")
    if cs:
        try:
            cc = Decimal(cs)
            if cc != 0:
                out_c = float((cc / n).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
        except Exception:
            pass
    return out_p, out_c


def aplicar_derivacion_desde_caja(
    precio_caja_str: str | None,
    costo_caja_str: str | None,
    unidades_por_caja: int | None,
    precio_umb_fallback: float,
    costo_umb_fallback: float,
) -> tuple[float, float]:
    """Compatibilidad: factor = unidades por caja."""
    factor = float(int(unidades_por_caja)) if unidades_por_caja and int(unidades_por_caja) > 0 else None
    return aplicar_derivacion_desde_presentacion(
        precio_caja_str,
        costo_caja_str,
        factor,
        precio_umb_fallback,
        costo_umb_fallback,
    )
