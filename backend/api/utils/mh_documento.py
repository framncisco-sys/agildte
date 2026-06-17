"""
Normalización de NIT/DUI para esquemas JSON del Ministerio de Hacienda (El Salvador).

fe-fc-v1 / DTE-01 receptor:
  - tipoDocumento "13" (DUI)  → numDocumento: exactamente 9 dígitos (solo números)
  - tipoDocumento "36" (NIT)  → numDocumento: 14 dígitos (o 9 en casos homologados)

Formato visual DUI «04727688-8» → 9 dígitos «047276888» (sin guión).
"""
from __future__ import annotations


def solo_digitos(texto: str | None) -> str:
    return "".join(c for c in str(texto or "") if c.isdigit())


def normalizar_nrc_mh(valor: str | None) -> str | None:
    """
    NRC para JSON MH (fe-ccf-v3 receptor.nrc): solo dígitos, 1–8 caracteres.
    """
    from api.dte_generator import formatear_nrc_emisor

    return formatear_nrc_emisor(valor)


# Valores de prueba / relleno que MH rechaza en producción (cód. 008).
_NRC_PLACEHOLDERS = frozenset(
    {"0000000", "00000000", "000000", "1234567", "123456", "1111111", "9999999"}
)


def es_nrc_placeholder_mh(nrc: str | None) -> bool:
    n = normalizar_nrc_mh(nrc) or solo_digitos(nrc)
    return bool(n) and n in _NRC_PLACEHOLDERS


def mensaje_ayuda_receptor_nrc_mh(codigo_msg: str | None, descripcion: str | None) -> str | None:
    """Texto orientado al usuario cuando MH rechaza el NRC del receptor."""
    desc = (descripcion or "").upper()
    cod = str(codigo_msg or "").strip()
    if cod != "008" and "RECEPTOR.NRC" not in desc and "NO CORRESPONDE A CONTRIBUYENTE" not in desc:
        return None
    return (
        "El NRC del cliente no coincide con el DUI/NIT registrado en Hacienda. "
        "En PosAgil edite el cliente: use el NRC oficial del MH (no el DUI ni datos de prueba) "
        "y el mismo DUI/NIT que figura en el registro del contribuyente."
    )


def normalizar_telefono_mh(
    telefono_raw: str | None,
    *,
    min_len: int = 8,
    max_len: int = 30,
    default: str = "22222222",
) -> str:
    """
    MH fe-fc-v1 receptor.telefono: solo dígitos, longitud 8–30 (sin guiones ni letras).
    """
    digitos = solo_digitos(telefono_raw)
    if len(digitos) == 8 and not digitos.startswith("503"):
        digitos = f"503{digitos}"
    if len(digitos) < min_len:
        digitos = solo_digitos(default) or default
    if len(digitos) < min_len:
        return default
    return digitos[:max_len]


def normalizar_tipo_y_numero_mh(
    tipo_usuario: str | None,
    documento_raw: str | None,
) -> tuple[str | None, str | None]:
    """
    Devuelve (tipoDocumento MH, numDocumento) o (None, None) si no hay documento.

    tipo_usuario: 'DUI', 'NIT', '13', '36', etc.
    """
    if not documento_raw or not str(documento_raw).strip():
        return None, None

    doc_limpio = solo_digitos(documento_raw)
    if not doc_limpio:
        return None, None

    t = (tipo_usuario or "").strip().upper()
    if t in ("13",):
        t = "DUI"
    elif t in ("36",):
        t = "NIT"

    if t not in ("DUI", "NIT"):
        if len(doc_limpio) == 14:
            t = "NIT"
        elif len(doc_limpio) in (8, 9, 10):
            t = "DUI"
        elif len(doc_limpio) > 10:
            t = "NIT"
        else:
            t = "DUI"

    if t == "DUI":
        if len(doc_limpio) == 10:
            doc_limpio = doc_limpio[:9]
        elif len(doc_limpio) == 8:
            doc_limpio = "0" + doc_limpio
        elif len(doc_limpio) > 9:
            doc_limpio = doc_limpio[:9]
        if len(doc_limpio) != 9:
            raise ValueError(
                f"DUI inválido para MH: '{documento_raw}'. "
                f"Debe tener 9 dígitos (ej. 04727688-8 → 047276888). "
                f"Dígitos encontrados: {len(doc_limpio)}."
            )
        return "13", doc_limpio

    # NIT
    if len(doc_limpio) == 13:
        doc_limpio = "0" + doc_limpio
    elif len(doc_limpio) == 8:
        doc_limpio = "0" + doc_limpio
    if len(doc_limpio) not in (9, 14):
        raise ValueError(
            f"NIT inválido para MH: '{documento_raw}'. "
            f"Debe tener 14 dígitos (o 9 en formato homologado). "
            f"Dígitos encontrados: {len(doc_limpio)}."
        )
    if len(doc_limpio) == 9:
        # MH: tipo 36 con 9 dígitos solo en homologación; DUI mal tipificado como NIT → 13
        if t != "NIT":
            return "13", doc_limpio
        return "36", doc_limpio
    return "36", doc_limpio.zfill(14)


def documento_receptor_desde_payload(
    tipo_usuario: str | None,
    documento_raw: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Normaliza documento del POS (documento_receptor / nit_receptor) para guardar en Cliente.

    Retorna (tipo_documento BD, nit, dui, documento_identidad) o (None,...) si vacío.
    """
    doc_raw = (documento_raw or "").strip()
    if not doc_raw:
        return None, None, None, None
    try:
        tipo_mh, doc_norm = normalizar_tipo_y_numero_mh(tipo_usuario, doc_raw)
    except ValueError:
        return None, None, None, None
    tipo_bd = "DUI" if tipo_mh == "13" else "NIT"
    if tipo_mh == "13":
        return tipo_bd, None, doc_norm, doc_norm
    nit_val = doc_norm if len(doc_norm) == 14 else doc_raw
    return tipo_bd, nit_val, None, doc_norm


def documento_cliente_para_mh(cliente) -> tuple[str | None, str | None]:
    """Elige DUI/NIT del cliente y normaliza para el JSON DTE."""
    if not cliente:
        return None, None
    tipo = (getattr(cliente, "tipo_documento", None) or "").strip().upper()
    dui = (getattr(cliente, "dui", None) or "").strip()
    nit = (getattr(cliente, "nit", None) or "").strip()
    doc_id = (getattr(cliente, "documento_identidad", None) or "").strip()

    def _es_dui_por_digitos(raw: str) -> bool:
        n = len(solo_digitos(raw))
        return n in (8, 9, 10)

    if tipo == "DUI" and (dui or doc_id):
        return normalizar_tipo_y_numero_mh("DUI", dui or doc_id)
    if dui:
        return normalizar_tipo_y_numero_mh("DUI", dui)
    # DUI guardado por error en campo nit (común en migraciones / POS antiguo)
    if nit and _es_dui_por_digitos(nit) and len(solo_digitos(nit)) != 14:
        return normalizar_tipo_y_numero_mh("DUI", nit)
    if tipo == "NIT" and (nit or doc_id):
        return normalizar_tipo_y_numero_mh("NIT", nit or doc_id)
    if nit:
        return normalizar_tipo_y_numero_mh("NIT", nit)
    if doc_id:
        return normalizar_tipo_y_numero_mh(tipo or None, doc_id)
    return None, None
