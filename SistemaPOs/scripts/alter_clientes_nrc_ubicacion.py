"""Agrega NRC, departamento y municipio a clientes (PostgreSQL PosAgil)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import ConexionDB

db = ConexionDB()
for sql in (
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS nrc VARCHAR(20)",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS departamento VARCHAR(2) DEFAULT '06'",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS municipio VARCHAR(2) DEFAULT '14'",
):
    db.ejecutar_sql(sql)
print("OK: clientes.nrc, departamento, municipio")
