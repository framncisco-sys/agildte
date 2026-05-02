# Programador: Oscar Amaya Romero
"""Agrega costo_unitario, unidad_medida y metodo_valuacion para reportes tributarios (Art. 142, F-983, NIC 2)."""
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

import psycopg2

from database import ConexionDB

cfg = ConexionDB().config
conn = psycopg2.connect(**cfg)
cur = conn.cursor()
try:
    cur.execute(
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS costo_unitario NUMERIC(16, 4) DEFAULT 0"
    )
    cur.execute(
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS unidad_medida VARCHAR(25) DEFAULT 'UNI'"
    )
    cur.execute(
        "ALTER TABLE productos ADD COLUMN IF NOT EXISTS metodo_valuacion VARCHAR(20) DEFAULT 'PROMEDIO'"
    )
    cur.execute(
        "ALTER TABLE inventario_kardex ADD COLUMN IF NOT EXISTS costo_unitario NUMERIC(16, 4)"
    )
    conn.commit()
    print("OK: costo_unitario, unidad_medida, metodo_valuacion en productos; costo_unitario en inventario_kardex.")
finally:
    cur.close()
    conn.close()
