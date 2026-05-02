# Programador: Oscar Amaya Romero
"""Agrega codigo_generacion y sello_recepcion a compras para trazabilidad DTE MH."""
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
    cur.execute("ALTER TABLE compras ADD COLUMN IF NOT EXISTS codigo_generacion VARCHAR(100)")
    cur.execute("ALTER TABLE compras ADD COLUMN IF NOT EXISTS sello_recepcion TEXT")
    conn.commit()
    print("OK: codigo_generacion, sello_recepcion en compras.")
finally:
    cur.close()
    conn.close()
