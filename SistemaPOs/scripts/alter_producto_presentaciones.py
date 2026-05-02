# Programador: Oscar Amaya Romero
"""
Migración: capa de presentaciones (factores respecto a UMB) y opcional presentacion_id en venta_detalles.

Ejecutar: python scripts/alter_producto_presentaciones.py
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import psycopg2

from database import ConexionDB  # noqa: E402
from azdigital.repositories import presentaciones_repo  # noqa: E402


def _load_dotenv(path: str | None = None) -> None:
    p = path or os.path.join(_ROOT, ".env")
    try:
        with open(p, "r", encoding="utf-8") as f:
            for raw in f.readlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if not k:
                    continue
                if k not in os.environ or os.environ.get(k, "") == "":
                    os.environ[k] = v
    except FileNotFoundError:
        pass


def main() -> None:
    _load_dotenv()
    db = ConexionDB()
    try:
        conn = psycopg2.connect(**db.config)
    except psycopg2.OperationalError as e:
        print(f"ERROR: No se pudo conectar a PostgreSQL:\n{e}")
        sys.exit(1)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS producto_presentacion (
                id SERIAL PRIMARY KEY,
                producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                nombre VARCHAR(80) NOT NULL,
                factor_umb NUMERIC(18,6) NOT NULL CHECK (factor_umb > 0),
                es_umb BOOLEAN NOT NULL DEFAULT FALSE,
                orden SMALLINT DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            DROP INDEX IF EXISTS uq_producto_presentacion_umb
            """
        )
        cur.execute(
            """
            CREATE UNIQUE INDEX uq_producto_presentacion_umb
            ON producto_presentacion (producto_id)
            WHERE es_umb
            """
        )
        cur.execute(
            """
            ALTER TABLE venta_detalles
            ADD COLUMN IF NOT EXISTS presentacion_id INTEGER NULL
            """
        )
        cur.execute("SELECT id, COALESCE(unidades_por_docena, 12), unidades_por_caja FROM productos")
        productos = cur.fetchall() or []
        for pid, upd, upc in productos:
            cur.execute(
                "SELECT 1 FROM producto_presentacion WHERE producto_id = %s LIMIT 1",
                (pid,),
            )
            if cur.fetchone():
                continue
            filas = presentaciones_repo.construir_filas_desde_legacy(
                "Unidad base",
                int(upd or 12),
                int(upc) if upc is not None and int(upc) > 0 else None,
                extras=None,
            )
            presentaciones_repo.reemplazar_todas(cur, int(pid), filas)
        conn.commit()
        print("OK: producto_presentacion, venta_detalles.presentacion_id, datos iniciales por producto.")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
