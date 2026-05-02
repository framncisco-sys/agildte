"""Agrega sucursal_id a clientes para asignar cliente a sucursal (superusuario)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import ConexionDB

db = ConexionDB()
db.ejecutar_sql(
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS sucursal_id INTEGER REFERENCES sucursales(id)"
)
print("OK: sucursal_id agregado a clientes.")
