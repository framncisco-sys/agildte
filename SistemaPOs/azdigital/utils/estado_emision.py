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


def fila_gestion_venta(row) -> dict:
    """Normaliza la fila de listar_ventas_recientes para la plantilla."""
    cg = row[7] if len(row) > 7 else ""
    ed = row[8] if len(row) > 8 else "RESPALDO"
    cajero = row[9] if len(row) > 9 else "—"
    st = clasificar_estado_emision(cg, ed)
    clave = st["clave"]
    return {
        "id": row[0],
        "fecha": row[1],
        "total": float(row[2] or 0),
        "cliente": row[3],
        "pago": row[4],
        "comprobante": row[5],
        "cliente_id": row[6],
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
