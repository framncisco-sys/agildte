"""Estado de emisión POS → AgilDTE (columna consultable en Gestión de ventas)."""
from __future__ import annotations

CLAVES_EMITIBLES = frozenset({"pendiente", "rechazado"})


def es_estado_aceptado_mh(estado_dte: str | None) -> bool:
    edu = (estado_dte or "").strip().upper()
    return any(x in edu for x in ("ACEPT", "ENVIADO", "PROCESADO", "CORREG"))


def clasificar_estado_emision(
    codigo_generacion: str | None,
    estado_dte: str | None,
) -> dict[str, str]:
    """
    Pendiente: ticket solo en POS (primera emisión).
    Rechazado: DTE remoto rechazado; se corrige y se emite con correlativo nuevo.
    Corregido: el nuevo DTE fue aceptado por Hacienda.
    Procesado / En AgilDTE: ya aceptado o enviado (sin ser corrección).
    """
    cg = (codigo_generacion or "").strip()
    ed = (estado_dte or "").strip()
    edu = ed.upper()
    if len(cg) > 8:
        if "CORREG" in edu:
            return {"clave": "corregido", "etiqueta": "Corregido"}
        if "RECHAZ" in edu:
            return {"clave": "rechazado", "etiqueta": "Rechazado"}
        if any(x in edu for x in ("ACEPT", "ENVIADO", "PROCESADO")):
            return {"clave": "procesado", "etiqueta": "Procesado"}
        return {"clave": "agildte", "etiqueta": "En AgilDTE"}
    return {"clave": "pendiente", "etiqueta": "Pendiente"}


def _celda(row, idx: int, clave: str, default=None):
    if row is None:
        return default
    if isinstance(row, dict):
        if clave in row:
            return row[clave]
        return row.get(idx, default)
    try:
        if len(row) > idx:
            return row[idx]
    except TypeError:
        pass
    return default


def _total_fila(val) -> float:
    try:
        if val is None or val == "":
            return 0.0
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def fila_gestion_venta(row) -> dict:
    """Normaliza la fila de listar_ventas_recientes para la plantilla."""
    cg = _celda(row, 7, "codigo_generacion", "")
    ed = _celda(row, 8, "estado_dte", "RESPALDO")
    cajero = _celda(row, 9, "cajero", "—")
    st = clasificar_estado_emision(cg, ed)
    clave = st["clave"]
    return {
        "id": _celda(row, 0, "id"),
        "fecha": _celda(row, 1, "fecha") or "",
        "total": _total_fila(_celda(row, 2, "total", 0)),
        "cliente": _celda(row, 3, "cliente") or "",
        "pago": _celda(row, 4, "pago") or "",
        "comprobante": _celda(row, 5, "comprobante") or "TICKET",
        "cliente_id": _celda(row, 6, "cliente_id"),
        "codigo_generacion": cg or "",
        "estado_dte": ed or "",
        "cajero": cajero or "—",
        "clave": clave,
        "etiqueta": st["etiqueta"],
        "puede_remitir": clave == "pendiente",
        "puede_reemitir": clave == "rechazado",
        "puede_emitir": clave in CLAVES_EMITIBLES,
        "en_agildte": clave in ("procesado", "agildte", "rechazado", "corregido"),
    }
