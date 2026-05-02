# Programador: Oscar Amaya Romero
"""Agrega motivo_ajuste al Kardex para clasificar mermas, averías y faltantes. Ejecutar una vez."""
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
        """
        ALTER TABLE inventario_kardex
        ADD COLUMN IF NOT EXISTS motivo_ajuste VARCHAR(32) NULL
        """
    )
    conn.commit()
    print("OK: inventario_kardex.motivo_ajuste (ejecutar una vez).")
finally:
    cur.close()
    conn.close()
