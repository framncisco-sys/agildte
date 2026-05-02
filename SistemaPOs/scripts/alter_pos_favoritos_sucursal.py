# Programador: Oscar Amaya Romero
"""Tabla de favoritos del POS compartidos por sucursal (JSON en servidor)."""
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
sqls = [
    """
    CREATE TABLE IF NOT EXISTS pos_favoritos_sucursal (
        id SERIAL PRIMARY KEY,
        empresa_id INTEGER NOT NULL,
        sucursal_key INTEGER NOT NULL DEFAULT 0,
        payload_json TEXT NOT NULL DEFAULT '[]',
        actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actualizado_por INTEGER
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_pos_favoritos_empresa_sucursal
    ON pos_favoritos_sucursal (empresa_id, sucursal_key)
    """,
]
for sql in sqls:
    try:
        db.ejecutar_sql(sql)
    except Exception as ex:
        if "already exists" not in str(ex).lower() and "duplicate" not in str(ex).lower():
            raise
print("OK: pos_favoritos_sucursal (ejecutar una vez).")
