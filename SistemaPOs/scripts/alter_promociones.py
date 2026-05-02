# Programador: Oscar Amaya Romero
"""Crea tablas promociones y promocion_productos para ofertas con vigencia por fechas."""
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS promociones (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
            nombre VARCHAR(120) NOT NULL,
            tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('2X1', 'PORCENTAJE')),
            valor NUMERIC(10, 2) NOT NULL,
            fecha_inicio DATE,
            fecha_fin DATE,
            activa BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS promocion_productos (
            promocion_id INTEGER NOT NULL REFERENCES promociones(id) ON DELETE CASCADE,
            producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
            PRIMARY KEY (promocion_id, producto_id)
        )
    """)
    conn.commit()
    print("OK: tablas promociones y promocion_productos creadas.")
finally:
    cur.close()
    conn.close()
