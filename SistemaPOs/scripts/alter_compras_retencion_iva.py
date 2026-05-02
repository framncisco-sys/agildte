# Programador: Oscar Amaya Romero
"""Agrega retencion_iva a compras para Libro IVA Compras (retención 1% según Gran Contribuyente)."""
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
        "ALTER TABLE compras ADD COLUMN IF NOT EXISTS retencion_iva DECIMAL(12,2) DEFAULT 0"
    )
    conn.commit()
    print("OK: retencion_iva agregado a compras.")
finally:
    cur.close()
    conn.close()
