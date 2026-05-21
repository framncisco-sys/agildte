# Catálogo CAT-013 MH — departamentos y municipios (códigos 2 dígitos).
# Misma fuente que frontend-saas/src/data/departamentos-municipios.js

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
    ("12", "Morazán"),
    ("13", "San Miguel"),
    ("14", "La Unión"),
]

MUNICIPIOS_POR_DEPARTAMENTO: dict[str, list[tuple[str, str]]] = {
    "01": [("13", "Ahuachapán Norte"), ("14", "Ahuachapán Centro"), ("15", "Ahuachapán Sur")],
    "02": [("14", "Santa Ana Norte"), ("15", "Santa Ana Centro"), ("16", "Santa Ana Este"), ("17", "Santa Ana Oeste")],
    "03": [("17", "Sonsonate Norte"), ("18", "Sonsonate Centro"), ("19", "Sonsonate Este"), ("20", "Sonsonate Oeste")],
    "04": [("34", "Chalatenango Norte"), ("35", "Chalatenango Centro"), ("36", "Chalatenango Sur")],
    "05": [("23", "La Libertad Norte"), ("24", "La Libertad Centro"), ("25", "La Libertad Oeste"), ("26", "La Libertad Este"), ("27", "La Libertad Costa"), ("28", "La Libertad Sur")],
    "06": [("20", "San Salvador Norte"), ("21", "San Salvador Oeste"), ("22", "San Salvador Este"), ("23", "San Salvador Centro"), ("24", "San Salvador Sur")],
    "07": [("17", "Cuscatlán Norte"), ("18", "Cuscatlán Sur")],
    "08": [("23", "La Paz Oeste"), ("24", "La Paz Centro"), ("25", "La Paz Este")],
    "09": [("10", "Cabañas Oeste"), ("11", "Cabañas Este")],
    "10": [("14", "San Vicente Norte"), ("15", "San Vicente Sur")],
    "11": [("24", "Usulután Norte"), ("25", "Usulután Este"), ("26", "Usulután Oeste")],
    "12": [("27", "Morazán Norte"), ("28", "Morazán Sur")],
    "13": [("21", "San Miguel Norte"), ("22", "San Miguel Centro"), ("23", "San Miguel Oeste")],
    "14": [("19", "La Unión Norte"), ("20", "La Unión Sur")],
}

DEPTO_DEFAULT = "06"
MUNI_DEFAULT = "14"
