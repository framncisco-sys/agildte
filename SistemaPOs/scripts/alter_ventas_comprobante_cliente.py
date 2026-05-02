# Programador: Oscar Amaya Romero
"""Tipo de comprobante (ticket/factura/CF) y cliente_id en ventas."""
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

conn = psycopg2.connect(**ConexionDB().config)
cur = conn.cursor()
try:
    cur.execute(
        "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS tipo_comprobante VARCHAR(32) NOT NULL DEFAULT 'TICKET'"
    )
    cur.execute(
        "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS cliente_id INTEGER REFERENCES clientes(id)"
    )
    conn.commit()
    print("OK: ventas.tipo_comprobante y ventas.cliente_id")
finally:
    cur.close()
    conn.close()
