# Programador: Oscar Amaya Romero
"""Kardex de inventario y stock por sucursal (entradas, salidas, traslados). Ejecutar una vez."""
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
        CREATE TABLE IF NOT EXISTS producto_stock_sucursal (
            id SERIAL PRIMARY KEY,
            producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
            sucursal_id INTEGER NOT NULL REFERENCES sucursales(id) ON DELETE CASCADE,
            cantidad NUMERIC(16, 4) NOT NULL DEFAULT 0,
            UNIQUE (producto_id, sucursal_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventario_kardex (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id),
            producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
            tipo VARCHAR(24) NOT NULL,
            cantidad NUMERIC(16, 4) NOT NULL,
            sucursal_id INTEGER REFERENCES sucursales(id),
            sucursal_destino_id INTEGER REFERENCES sucursales(id),
            referencia VARCHAR(160),
            notas TEXT,
            usuario_id INTEGER REFERENCES usuarios(id),
            creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute(
        """
        INSERT INTO producto_stock_sucursal (producto_id, sucursal_id, cantidad)
        SELECT p.id,
               COALESCE(
                   p.sucursal_id,
                   (SELECT MIN(s.id) FROM sucursales s WHERE s.empresa_id = p.empresa_id)
               ),
               COALESCE(p.stock_actual, 0)
        FROM productos p
        WHERE COALESCE(
                  p.sucursal_id,
                  (SELECT MIN(s.id) FROM sucursales s WHERE s.empresa_id = p.empresa_id)
              ) IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM producto_stock_sucursal x WHERE x.producto_id = p.id
          )
        """
    )
    conn.commit()
    print("OK: tablas producto_stock_sucursal e inventario_kardex (ejecutar una vez).")
finally:
    cur.close()
    conn.close()
