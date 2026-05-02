"""Ejecuta ALTER TABLE para agregar direccion y telefono a clientes."""
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
for stmt in [
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS direccion TEXT",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telefono VARCHAR(50)",
]:
    db.ejecutar_sql(stmt)
    print("OK:", stmt[:60] + "...")
print("Columnas direccion y telefono agregadas correctamente.")
