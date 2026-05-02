# Programador: Oscar Amaya Romero
"""Campos fiscales para proveedores: tipo doc, giro, clasificación contribuyente (retención IVA 1%)."""
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
        "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS tipo_documento VARCHAR(10) DEFAULT 'NIT'"
    )
    cur.execute(
        "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS giro_actividad VARCHAR(255)"
    )
    cur.execute(
        "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS clasificacion_contribuyente VARCHAR(20) DEFAULT 'PEQUEÑO'"
    )
    cur.execute(
        "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS es_gran_contribuyente BOOLEAN DEFAULT FALSE"
    )
    conn.commit()
    print("OK: tipo_documento, giro_actividad, clasificacion_contribuyente, es_gran_contribuyente en proveedores.")
finally:
    cur.close()
    conn.close()
