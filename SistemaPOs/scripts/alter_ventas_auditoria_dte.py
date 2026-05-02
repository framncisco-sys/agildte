# Programador: Oscar Amaya Romero
"""Trazabilidad en anulaciones y campos DTE para auditoría e integración MH."""
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
db.ejecutar_sql(
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS motivo_anulacion TEXT"
)
db.ejecutar_sql(
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS usuario_anulo_id INTEGER REFERENCES usuarios(id)"
)
db.ejecutar_sql(
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS fecha_anulacion TIMESTAMP"
)
db.ejecutar_sql(
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS estado_dte VARCHAR(32) DEFAULT 'RESPALDO'"
)
db.ejecutar_sql(
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS codigo_generacion VARCHAR(64)"
)
db.ejecutar_sql(
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS numero_control VARCHAR(64)"
)
db.ejecutar_sql(
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS sello_recepcion TEXT"
)
print("OK: Trazabilidad anulaciones y campos DTE en ventas.")
