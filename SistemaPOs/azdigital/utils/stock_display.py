# Programador: Oscar Amaya Romero
"""Texto amigable de existencias en UMB + cajas/docenas residuales."""

# Cat. MH: medidas continuas (no agrupar stock en «docenas + sueltas» como si fueran unidades sueltas).
_MH_MEDIDA_CONTINUA: frozenset[str] = frozenset(
    {
        "10",
        "11",
        "12",
        "13",
        "14",  # peso/masa
        "31",
        "32",
        "39",
        "18",
        "20",
        "21",
        "22",
        "23",  # volumen
        "80",
        "81",
        "83",
        "84",
        "85",
        "87",
        "89",
        "90",  # longitud / superficie (no agrupar como docena)
    }
)


def _umb_o_mh_es_medida_continua(mh_codigo: str | None, etiqueta_umb_lower: str) -> bool:
    """True si el artículo es peso, volumen o longitud vendida por fracción — no empaques tipo docena."""
    mh = (mh_codigo or "").strip()
    if len(mh) >= 2 and mh[:2].isdigit() and mh[:2] in _MH_MEDIDA_CONTINUA:
        return True
    u = etiqueta_umb_lower
    for w in (
        "libra",
        "kilo",
        "kilogram",
        "gramo",
        "litro",
        "mililit",
        "galón",
        "galon",
        "onza",
        "quintal",
        "arroba",
        "tonelada",
        "metro cúb",
        "m³",
        "m3",
        "metro",
        "metros",
        "centímetro",
        "centimetro",
        "pulgada",
        "yarda",
        "varas",
        "vara ",
    ):
        if w in u:
            return True
    return u in ("lb", "lbs", "kg", "l", "ml", "g")


def _etiqueta_umb(etiqueta_umb: str | None) -> str:
    lab = (etiqueta_umb or "").strip()
    if not lab or lab.lower() in ("unidad base", "umb"):
        return "u."
    return lab


def texto_stock_grupos(
    unidades_base: float,
    unidades_por_caja: int | None = None,
    unidades_por_docena: int | None = None,
    etiqueta_umb: str | None = None,
    *,
    fraccionable: bool = False,
    mh_codigo_unidad: str | None = None,
) -> str:
    """
    Ej.: 47 sobres con caja de 60 → '47 Sobre (1 caja(s) + 23 Sobre)' si etiqueta_umb es «Sobre».
    Queso por libra (fraccionable, MH 11 o etiqueta «libra»): sin docenas — '15 Libra', no '1 docena + 3'.
    Sin etiqueta usa «u.» como antes.
    """
    uw = _etiqueta_umb(etiqueta_umb)
    try:
        u = float(unidades_base)
    except (TypeError, ValueError):
        return "—"
    umb_l = (etiqueta_umb or "").strip().lower()
    mh_s = (mh_codigo_unidad or "").strip()
    # Peso, volumen o fraccionable: no mostrar «X docenas + Y» (eso es para conteo por piezas).
    sin_agrupacion_empaque = bool(fraccionable) or _umb_o_mh_es_medida_continua(mh_s, umb_l)
    if sin_agrupacion_empaque:
        if u != int(u):
            base_txt = f"{u:.4f}".rstrip("0").rstrip(".")
            return f"{base_txt} {uw}"
        return f"{int(u)} {uw}"
    if u != int(u):
        base_txt = f"{u:.4f}".rstrip("0").rstrip(".")
        return f"{base_txt} {uw} (fraccionable)"
    n = int(u)
    partes = [f"{n} {uw}"]
    upc = int(unidades_por_caja) if unidades_por_caja and int(unidades_por_caja) > 0 else None
    if upc and upc > 1:
        cajas = n // upc
        resto = n % upc
        partes.append(f"({cajas} caja(s) + {resto} {uw})")
    elif (
        unidades_por_docena
        and int(unidades_por_docena) > 0
        and (not upc or int(unidades_por_docena) != upc)
    ):
        upd = int(unidades_por_docena)
        if upd > 1:
            doc = n // upd
            resto_d = n % upd
            if doc > 0:
                partes.append(f"({doc} docena(s) + {resto_d} {uw})")
    return " ".join(partes)
