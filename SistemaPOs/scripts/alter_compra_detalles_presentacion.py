# Programador: Oscar Amaya Romero
"""Añade a compra_detalles el factor y cantidad en presentación (factura proveedor) para conversión a UMB."""

from __future__ import annotations

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


def main() -> None:
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            ALTER TABLE compra_detalles
            ADD COLUMN IF NOT EXISTS cantidad_recibida_presentacion NUMERIC(16, 4) NULL
            """
        )
        cur.execute(
            """
            ALTER TABLE compra_detalles
            ADD COLUMN IF NOT EXISTS factor_conversion NUMERIC(18, 6) NULL
            """
        )
        cur.execute(
            """
            ALTER TABLE compra_detalles
            ADD COLUMN IF NOT EXISTS presentacion_nombre VARCHAR(80) NULL
            """
        )
        conn.commit()
        print("OK: compra_detalles (cantidad_recibida_presentacion, factor_conversion, presentacion_nombre).")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
