# Programador: Oscar Amaya Romero
"""Agrega estado (ACTIVO/ANULADO) y estado_cobro (COBRADO/PENDIENTE) a ventas para reportes tributarios."""
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
        "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS estado VARCHAR(16) DEFAULT 'ACTIVO'"
    )
    cur.execute(
        "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS estado_cobro VARCHAR(16) DEFAULT 'COBRADO'"
    )
    cur.execute(
        "UPDATE ventas SET estado = 'ACTIVO' WHERE estado IS NULL"
    )
    cur.execute(
        "UPDATE ventas SET estado_cobro = 'COBRADO' WHERE estado_cobro IS NULL"
    )
    conn.commit()
    print("OK: ventas.estado y ventas.estado_cobro agregados.")
finally:
    cur.close()
    conn.close()
