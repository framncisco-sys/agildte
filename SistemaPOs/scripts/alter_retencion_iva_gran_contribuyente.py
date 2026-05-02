# Programador: Oscar Amaya Romero
"""Retención IVA 1%: es_gran_contribuyente en clientes y empresas, retencion_iva en ventas."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar .env para conexión a BD (igual que app.py)
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
db.ejecutar_sql(
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS es_gran_contribuyente BOOLEAN DEFAULT FALSE"
)
db.ejecutar_sql(
    "ALTER TABLE empresas ADD COLUMN IF NOT EXISTS es_gran_contribuyente BOOLEAN DEFAULT FALSE"
)
db.ejecutar_sql(
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS retencion_iva DECIMAL(10,2) DEFAULT 0"
)
print("OK: es_gran_contribuyente en clientes y empresas, retencion_iva en ventas.")
