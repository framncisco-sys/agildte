# Programador: Oscar Amaya Romero
"""Validación de documentos fiscales (NIT, NRC) para El Salvador."""


def extraer_digitos(texto: str) -> str:
    """Extrae solo dígitos del texto."""
    return "".join(c for c in (texto or "") if c.isdigit())


def validar_nit(nit: str) -> tuple[bool, str]:
    """
    NIT El Salvador: 14 dígitos. Formato típico 0614-161386-001-4.
    Retorna (es_valido, mensaje).
    """
    if not nit or not str(nit).strip():
        return True, ""  # Vacío permitido
    digitos = extraer_digitos(nit)
    if len(digitos) != 14:
        return False, "NIT debe tener 14 dígitos (ej: 0614-161386-001-4)."
    if not digitos.isdigit():
        return False, "NIT debe contener solo números."
    return True, ""


def validar_nrc(nrc: str) -> tuple[bool, str]:
    """
    NRC según DTE MH: puede ser corto (ej. 27 Vidri) o largo (2984414).
    Aplica a clientes y proveedores. Acepta 1-8 dígitos; vacío permitido.
    """
    if not nrc or not str(nrc).strip():
        return True, ""
    digitos = extraer_digitos(nrc)
    if not digitos or not digitos.isdigit():
        return False, "NRC debe contener solo números."
    if len(digitos) < 1 or len(digitos) > 8:
        return False, "NRC debe tener entre 1 y 8 dígitos (según registro en Hacienda)."
    return True, ""


def validar_nrc_proveedor(nrc: str) -> tuple[bool, str]:
    """Alias de validar_nrc (misma regla MH para emisor/receptor)."""
    return validar_nrc(nrc)


def validar_dui(dui: str) -> tuple[bool, str]:
    """
    DUI El Salvador: 9 dígitos. Formato típico 00000000-0.
    Retorna (es_valido, mensaje). Validado sin guiones.
    """
    if not dui or not str(dui).strip():
        return True, ""
    digitos = extraer_digitos(dui)
    if len(digitos) != 9:
        return False, "DUI debe tener 9 dígitos (ej: 00000000-0)."
    if not digitos.isdigit():
        return False, "DUI debe contener solo números."
    return True, ""


def validar_nit_dui(tipo: str, numero: str) -> tuple[bool, str]:
    """
    Valida NIT (14 dígitos) o DUI (9 dígitos) según tipo. Sin guiones.
    """
    if not numero or not str(numero).strip():
        return True, ""
    digitos = extraer_digitos(numero)
    t = (tipo or "").strip().upper()
    if t == "NIT":
        return validar_nit(numero)
    if t == "DUI":
        return validar_dui(numero)
    if len(digitos) == 14:
        return validar_nit(numero)
    if len(digitos) == 9:
        return validar_dui(numero)
    return False, "NIT debe tener 14 dígitos; DUI debe tener 9 dígitos."
