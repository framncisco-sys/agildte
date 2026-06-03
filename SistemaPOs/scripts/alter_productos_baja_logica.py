# Programador: Oscar Amaya Romero
"""Columnas para baja lógica de productos (activo, motivo, fecha, usuario)."""
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
sql_path = os.path.join(os.path.dirname(__file__), "sql", "schema_productos_baja_logica.sql")
with open(sql_path, "r", encoding="utf-8") as f:
    for part in f.read().split(";"):
        st = part.strip()
        if st:
            db.ejecutar_sql(st)
print("OK: columnas de baja lógica en productos.")
