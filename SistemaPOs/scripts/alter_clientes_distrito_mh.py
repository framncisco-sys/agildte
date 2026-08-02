"""Agrega distrito, nombre_comercial y desc_actividad a clientes; backfill municipio CGEOES→MH."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import ConexionDB
from azdigital.data.departamentos_municipios import MUNI_CGEOES_A_MH

db = ConexionDB()
for sql in (
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS distrito VARCHAR(2) DEFAULT '14'",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS nombre_comercial VARCHAR(255)",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS desc_actividad VARCHAR(255)",
):
    db.ejecutar_sql(sql)

# Backfill: códigos municipio CGEOES (01..N) → CAT-013 MH
n_upd = 0
for depto, mapa in MUNI_CGEOES_A_MH.items():
    for cgeoes, mh in mapa.items():
        db.ejecutar_sql(
            "UPDATE clientes SET municipio = %s WHERE departamento = %s AND municipio = %s",
            (mh, depto, cgeoes),
        )
        n_upd += 1

print("OK: clientes.distrito, nombre_comercial, desc_actividad")
print(f"OK: backfill municipio CGEOES→MH ({n_upd} mapeos aplicados)")
