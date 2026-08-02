# Catálogo CAT-012 / CAT-013 MH V2 — misma fuente que frontend-saas/src/data/departamentos-municipios.js
# Códigos de los 44 municipios nuevos (ej. San Salvador Centro = 23). No usar CGEOES 01..N.

DEPARTAMENTOS = [
    ("01", "Ahuachapán"),
    ("02", "Santa Ana"),
    ("03", "Sonsonate"),
    ("04", "Chalatenango"),
    ("05", "La Libertad"),
    ("06", "San Salvador"),
    ("07", "Cuscatlán"),
    ("08", "La Paz"),
    ("09", "Cabañas"),
    ("10", "San Vicente"),
    ("11", "Usulután"),
    ("12", "San Miguel"),
    ("13", "Morazán"),
    ("14", "La Unión"),
]

MUNICIPIOS_POR_DEPARTAMENTO: dict[str, list[tuple[str, str]]] = {
    "01": [("13", "Ahuachapán Norte"), ("14", "Ahuachapán Centro"), ("15", "Ahuachapán Sur")],
    "02": [("14", "Santa Ana Norte"), ("15", "Santa Ana Centro"), ("16", "Santa Ana Este"), ("17", "Santa Ana Oeste")],
    "03": [("17", "Sonsonate Norte"), ("18", "Sonsonate Centro"), ("19", "Sonsonate Este"), ("20", "Sonsonate Oeste")],
    "04": [("34", "Chalatenango Norte"), ("35", "Chalatenango Centro"), ("36", "Chalatenango Sur")],
    "05": [
        ("23", "La Libertad Norte"), ("24", "La Libertad Centro"), ("25", "La Libertad Oeste"),
        ("26", "La Libertad Este"), ("27", "La Libertad Costa"), ("28", "La Libertad Sur"),
    ],
    "06": [
        ("20", "San Salvador Norte"), ("21", "San Salvador Oeste"), ("22", "San Salvador Este"),
        ("23", "San Salvador Centro"), ("24", "San Salvador Sur"),
    ],
    "07": [("17", "Cuscatlán Norte"), ("18", "Cuscatlán Sur")],
    "08": [("23", "La Paz Oeste"), ("24", "La Paz Centro"), ("25", "La Paz Este")],
    "09": [("10", "Cabañas Oeste"), ("11", "Cabañas Este")],
    "10": [("14", "San Vicente Norte"), ("15", "San Vicente Sur")],
    "11": [("24", "Usulután Norte"), ("25", "Usulután Este"), ("26", "Usulután Oeste")],
    "12": [("21", "San Miguel Norte"), ("22", "San Miguel Centro"), ("23", "San Miguel Oeste")],
    "13": [("27", "Morazán Norte"), ("28", "Morazán Sur")],
    "14": [("19", "La Unión Norte"), ("20", "La Unión Sur")],
}

# Si alguien guardó códigos CGEOES (01..N), mapear a CAT-013 MH DTE.
MUNI_CGEOES_A_MH: dict[str, dict[str, str]] = {
    "01": {"01": "14", "02": "13", "03": "15"},
    "02": {"01": "15", "02": "16", "03": "14", "04": "17"},
    "03": {"01": "18", "02": "19", "03": "17", "04": "20"},
    "04": {"01": "35", "02": "34", "03": "36"},
    "05": {"01": "24", "02": "27", "03": "26", "04": "23", "05": "25", "06": "28"},
    "06": {"01": "23", "02": "22", "03": "20", "04": "21", "05": "24"},
    "07": {"01": "17", "02": "18"},
    "08": {"01": "24", "02": "25", "03": "23"},
    "09": {"01": "11", "02": "10"},
    "10": {"01": "14", "02": "15"},
    "11": {"01": "25", "02": "24", "03": "26"},
    "12": {"01": "22", "02": "21", "03": "23"},
    "13": {"01": "27", "02": "28"},
    "14": {"01": "19", "02": "20"},
}

DEPTO_DEFAULT = "06"
MUNI_DEFAULT = "23"  # San Salvador Centro (CAT-013)
DISTRITO_DEFAULT = "14"


def _pad2(valor: str | None, default: str = "") -> str:
    digitos = "".join(c for c in str(valor or "") if c.isdigit())
    if not digitos:
        return default
    return digitos.zfill(2)[-2:]


def municipio_mh(departamento: str | None, municipio: str | None) -> str:
    d = _pad2(departamento, DEPTO_DEFAULT)
    m = _pad2(municipio, "")
    return MUNI_CGEOES_A_MH.get(d, {}).get(m) or m


def normalizar_ubicacion_mh(
    departamento: str | None,
    municipio: str | None,
    distrito: str | None = None,
) -> tuple[str, str, str]:
    """Normaliza depto/muni/distrito a CAT-012/013/008 para DTE."""
    from azdigital.data.distritos_cat008 import distrito_default

    d = _pad2(departamento, DEPTO_DEFAULT)
    m_raw = _pad2(municipio, "")
    codigos_depto = {c for c, _ in MUNICIPIOS_POR_DEPARTAMENTO.get(d, [])}

    if m_raw and m_raw in codigos_depto:
        m = m_raw
    else:
        m = MUNI_CGEOES_A_MH.get(d, {}).get(m_raw) or m_raw
        # Histórico: San Miguel guardado como depto 13 + CGEOES 01..03
        if d == "13" and m_raw in ("01", "02", "03") and m not in ("27", "28"):
            d = "12"
            m = MUNI_CGEOES_A_MH.get("12", {}).get(m_raw) or m
        elif d == "12" and m_raw in ("01", "02") and m not in ("21", "22", "23"):
            d = "13"
            m = MUNI_CGEOES_A_MH.get("13", {}).get(m_raw) or m

    codigos_ok = {c for c, _ in MUNICIPIOS_POR_DEPARTAMENTO.get(d, [])}
    if not m or m not in codigos_ok:
        m = MUNICIPIOS_POR_DEPARTAMENTO.get(d, [(MUNI_DEFAULT, "")])[0][0]

    di = _pad2(distrito, "")
    if not di:
        di = distrito_default(d, m) or DISTRITO_DEFAULT
    return d, m, di
