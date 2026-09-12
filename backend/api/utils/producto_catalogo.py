"""Evita facturar ítems huérfanos: si no hay producto de catálogo, se crea o reutiliza."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from api.constants import DTE_LINEA_DESCRIPCION_MAX_LENGTH
from api.models import Producto


def asegurar_producto_desde_linea(
    empresa,
    *,
    descripcion: str | None,
    codigo: str | None = "",
    precio=None,
):
    """
    Devuelve un Producto de la empresa para la línea de factura.
    Busca por código o descripción; si no existe, lo crea (activo).
    """
    if empresa is None:
        return None
    desc = (descripcion or "").strip()[:DTE_LINEA_DESCRIPCION_MAX_LENGTH]
    if not desc:
        return None
    codigo_txt = (codigo or "").strip()[:50]
    qs = Producto.objects.filter(empresa=empresa)
    found = None
    if codigo_txt:
        found = qs.filter(codigo__iexact=codigo_txt).first()
    if found is None:
        found = qs.filter(descripcion__iexact=desc).first()
    if found is not None:
        if not found.activo:
            found.activo = True
            found.save(update_fields=["activo"])
        return found
    try:
        precio_dec = Decimal(str(precio if precio is not None else 0))
    except (InvalidOperation, TypeError, ValueError):
        precio_dec = Decimal("0")
    return Producto.objects.create(
        empresa=empresa,
        codigo=codigo_txt,
        descripcion=desc,
        precio_unitario=precio_dec,
        activo=True,
    )
