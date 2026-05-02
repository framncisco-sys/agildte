# Programador: Oscar Amaya Romero
"""
Catálogo 003 — Unidades de medida (Ministerio de Hacienda, El Salvador).
Listado oficial reducido usado en inventario, POS, ventas y DTE.
"""

from __future__ import annotations

# Categorías y códigos en el orden del listado MH acordado para el negocio.
CATEGORIAS_CAT003: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Pesos y Masa",
        [
            ("10", "Quintal"),
            ("11", "Libra"),
            ("12", "Arroba"),
            ("13", "Tonelada"),
            ("14", "Onza"),
            ("31", "Miligramo"),
            ("32", "Gramo"),
            ("39", "Kilogramo"),
        ],
    ),
    (
        "Volumen y Líquidos",
        [
            ("03", "Millares de pies cúbicos"),
            ("05", "Barriles"),
            ("17", "Yarda cúbica"),
            ("18", "Galón"),
            ("19", "Botella"),
            ("20", "Centímetro cúbico"),
            ("21", "Mililitro"),
            ("22", "Litro"),
            ("23", "Metro cúbico"),
        ],
    ),
    (
        "Longitud y Superficie",
        [
            ("80", "Milímetro"),
            ("81", "Centímetro"),
            ("83", "Pulgada"),
            ("84", "Pie"),
            ("85", "Yarda"),
            ("87", "Metro"),
            ("89", "Metro cuadrado"),
            ("90", "Vara"),
        ],
    ),
    (
        "Conteo y Agrupación",
        [
            ("26", "Docena"),
            ("27", "Pares"),
            ("57", "Caja"),
            ("58", "Paquete"),
            ("59", "Unidad"),
            ("60", "Ciento"),
            ("67", "Millar"),
        ],
    ),
    (
        "Energía y Servicios",
        [
            ("01", "Servicio por hora día etc"),
            ("02", "Kilovatios-hora"),
            ("99", "Otros Especificar"),
        ],
    ),
]

_ORDEN_CAT003: list[tuple[str, str]] = [pair for _, pairs in CATEGORIAS_CAT003 for pair in pairs]

NOMBRES_OFICIALES_CAT_003: dict[str, str] = dict(_ORDEN_CAT003)

CODIGOS_CAT003: frozenset[str] = frozenset(NOMBRES_OFICIALES_CAT_003.keys())

CODIGO_MH_DEFAULT: str = "59"

# Sufijo corto tras la cantidad en ticket (venta por monto / texto amigable).
_SUFIJOS_TICKET: dict[str, str] = {
    "01": " serv.",
    "02": " kWh",
    "03": " mpc",
    "05": " bbl",
    "10": " qq",
    "11": " Lb",
    "12": " @",
    "13": " t",
    "14": " oz",
    "17": " yd³",
    "18": " gal",
    "19": " bot.",
    "20": " cm³",
    "21": " ml",
    "22": " L",
    "23": " m³",
    "26": " doc.",
    "27": " pr.",
    "31": " mg",
    "32": " g",
    "39": " Kg",
    "57": " caja(s)",
    "58": " paq.",
    "59": " u.",
    "60": " cto.",
    "67": " mill.",
    "80": " mm",
    "81": " cm",
    "83": " plg",
    "84": " ft",
    "85": " yd",
    "87": " m",
    "89": " m²",
    "90": " vara",
    "99": " u.",
}


def _codigo_dos_digitos_raw(codigo: str | None) -> str | None:
    c = (codigo or "").strip()
    if len(c) == 1 and c.isdigit():
        return f"0{c}"
    if len(c) >= 2:
        c2 = c[:2]
        if c2.isdigit():
            return c2
    return None


def normalizar_codigo_mh(codigo: str | None) -> str:
    """Código de dos dígitos permitido en cat. 003; si no aplica, retorna 59 (Unidad)."""
    c2 = _codigo_dos_digitos_raw(codigo)
    if c2 and c2 in CODIGOS_CAT003:
        return c2
    return CODIGO_MH_DEFAULT


def sufijo_ticket_cat003(codigo: str | None) -> str:
    """Abreviatura para texto de cantidad en ticket (p. ej. venta por monto)."""
    return _SUFIJOS_TICKET.get(normalizar_codigo_mh(codigo), " u.")


def descripcion_cat003(codigo: str) -> str:
    """Devuelve la descripción para un código de dos dígitos (nombre oficial o genérico)."""
    c2 = _codigo_dos_digitos_raw(codigo)
    if c2 is None:
        return "59 — Unidad"
    if c2 in NOMBRES_OFICIALES_CAT_003:
        return NOMBRES_OFICIALES_CAT_003[c2]
    return f"Código {c2}"


def todas_las_filas_cat003() -> list[tuple[str, str]]:
    """Filas (codigo, descripcion) para BD y selects: solo el listado oficial configurado."""
    return list(_ORDEN_CAT003)


def catalogo_para_select_optgroups(desc_por_codigo: dict[str, str] | None = None) -> list[tuple[str, list[tuple[str, str]]]]:
    """Para <select> con <optgroup>: textos desde BD (mapa opcional) o los de este módulo."""
    m = desc_por_codigo or {}
    return [(titulo, [(c, m.get(c, d)) for c, d in pairs]) for titulo, pairs in CATEGORIAS_CAT003]
