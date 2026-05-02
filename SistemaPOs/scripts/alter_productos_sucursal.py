# Programador: Oscar Amaya Romero
"""Agrega sucursal_id a productos (asignación por sucursal; NULL = todas las sucursales de la empresa)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v

from database import ConexionDB

db = ConexionDB()
try:
    db.ejecutar_sql(
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS sucursal_id INTEGER REFERENCES sucursales(id)"
    )
except Exception as ex:
    if "already exists" not in str(ex).lower():
        raise
print("OK: sucursal_id en productos (ejecutar una vez).")
