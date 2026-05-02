# Programador: Oscar Amaya Romero
"""Extiende promociones para: DESCUENTO_MONTO, VOLUMEN (2x1, 3x2), REGALO."""
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
    cur.execute("ALTER TABLE promociones ADD COLUMN IF NOT EXISTS valor_comprar NUMERIC(10, 2)")
    cur.execute("ALTER TABLE promociones ADD COLUMN IF NOT EXISTS valor_pagar NUMERIC(10, 2)")
    cur.execute("ALTER TABLE promociones ADD COLUMN IF NOT EXISTS descuento_monto NUMERIC(10, 2)")
    cur.execute("ALTER TABLE promociones ADD COLUMN IF NOT EXISTS producto_regalo_id INTEGER REFERENCES productos(id) ON DELETE SET NULL")
    cur.execute("ALTER TABLE promociones ADD COLUMN IF NOT EXISTS cantidad_min_compra NUMERIC(10, 2) DEFAULT 1")
    cur.execute("ALTER TABLE promociones ADD COLUMN IF NOT EXISTS cantidad_regalo NUMERIC(10, 2) DEFAULT 1")
    try:
        cur.execute("ALTER TABLE promociones DROP CONSTRAINT IF EXISTS promociones_tipo_check")
        cur.execute("ALTER TABLE promociones ADD CONSTRAINT promociones_tipo_check CHECK (tipo IN ('2X1', '3X2', 'PORCENTAJE', 'DESCUENTO_MONTO', 'VOLUMEN', 'REGALO', 'PRECIO_FIJO', 'DESCUENTO_CANTIDAD'))")
    except Exception as e:
        try:
            cur.execute("SELECT conname FROM pg_constraint WHERE conrelid = 'promociones'::regclass AND contype = 'c'")
            for row in cur.fetchall() or []:
                cur.execute(f"ALTER TABLE promociones DROP CONSTRAINT IF EXISTS {row[0]}")
            cur.execute("ALTER TABLE promociones ADD CONSTRAINT promociones_tipo_check CHECK (tipo IN ('2X1', '3X2', 'PORCENTAJE', 'DESCUENTO_MONTO', 'VOLUMEN', 'REGALO', 'PRECIO_FIJO', 'DESCUENTO_CANTIDAD'))")
        except Exception:
            pass
    conn.commit()
    print("OK: columnas de promociones extendidas (valor_comprar, valor_pagar, descuento_monto, producto_regalo_id, cantidad_min_compra, cantidad_regalo).")
finally:
    cur.close()
    conn.close()
