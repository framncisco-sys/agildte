# Programador: Oscar Amaya Romero
"""Conversión de números a letras en español para facturas (El Salvador)."""

UNIDADES = ("", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve")
ESPECIALES = (
    "diez", "once", "doce", "trece", "catorce", "quince",
    "dieciséis", "diecisiete", "dieciocho", "diecinueve",
)
DECENAS = ("", "", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa")
CIENTOS = ("", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos",
           "seiscientos", "setecientos", "ochocientos", "novecientos")


def _menor_1000(n: int) -> str:
    if n == 0:
        return ""
    if n < 10:
        return UNIDADES[n]
    if n < 20:
        return ESPECIALES[n - 10]
    if n < 100:
        d, u = divmod(n, 10)
        base = DECENAS[d]
        return f"{base} y {UNIDADES[u]}" if u else base
    c, resto = divmod(n, 100)
    if n == 100:
        return "cien"
    base = CIENTOS[c]
    return f"{base} {_menor_1000(resto)}".strip() if resto else base


def numero_a_letras_dolares(monto: float) -> str:
    """
    Convierte un monto a letras para facturas en USD.
    Ej: 262.05 -> "Doscientos sesenta y dos 05/100 dólares"
    """
    try:
        monto = float(monto)
    except (TypeError, ValueError):
        return "Cero 00/100 dólares"
    if monto < 0:
        return "Menos " + numero_a_letras_dolares(-monto)
    entero = int(monto)
    centavos = int(round((monto - entero) * 100)) % 100
    if entero == 0 and centavos == 0:
        return "Cero 00/100 dólares"
    if entero == 0:
        return f"Cero {centavos:02d}/100 dólares"

    partes = []
    if entero >= 1_000_000:
        millones = entero // 1_000_000
        if millones == 1:
            partes.append("un millón")
        else:
            partes.append(_menor_1000(millones) + " millones")
        entero %= 1_000_000
    if entero >= 1_000:
        miles = entero // 1_000
        if miles == 1:
            partes.append("mil")
        else:
            partes.append(_menor_1000(miles) + " mil")
        entero %= 1_000
    if entero > 0:
        partes.append(_menor_1000(entero))
    texto = " ".join(partes).strip()
    texto = texto[0].upper() + texto[1:] if texto else "Cero"
    return f"{texto} {centavos:02d}/100 dólares"
