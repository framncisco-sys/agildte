# Programador: Oscar Amaya Romero
"""Tabla para historial de costos de productos (último precio compra, promedio para fijación justa)."""
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
        CREATE TABLE IF NOT EXISTS producto_costos (
            id SERIAL PRIMARY KEY,
            producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
            costo NUMERIC(16, 4) NOT NULL,
            cantidad NUMERIC(16, 4) DEFAULT 1,
            tipo VARCHAR(24) DEFAULT 'COMPRA',
            referencia VARCHAR(160),
            creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            usuario_id INTEGER REFERENCES usuarios(id)
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_producto_costos_producto ON producto_costos(producto_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_producto_costos_creado ON producto_costos(creado_en DESC)"
    )
    conn.commit()
    print("OK: tabla producto_costos creada.")
finally:
    cur.close()
    conn.close()
