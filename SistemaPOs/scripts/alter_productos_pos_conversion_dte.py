# Programador: Oscar Amaya Romero
"""
Migración: conversión POS (caja/docena), venta por monto (fraccionable),
código unidad MH catálogo 003, texto de cantidad en ticket/factura.

Ejecutar: python scripts/alter_productos_pos_conversion_dte.py
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import psycopg2

from database import ConexionDB  # noqa: E402
from azdigital.utils.mh_cat003_unidades import todas_las_filas_cat003  # noqa: E402


def _load_dotenv(path: str | None = None) -> None:
    """Carga .env desde la raíz del proyecto (misma lógica que app.py)."""
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
        err = str(e).lower()
        print(f"ERROR: No se pudo conectar a PostgreSQL:\n{e}")
        if "password" in err or "fe_sendauth" in err:
            print()
            print("Suele faltar la clave en el entorno. Soluciones:")
            print(f"  • Edite {_ROOT}\\.env y defina AZ_DB_PASSWORD= (igual que para python app.py).")
            print("  • O en PowerShell:  $env:AZ_DB_PASSWORD='su_clave'")
            print("  • Ver .env.example como plantilla.")
        sys.exit(1)
    cur = conn.cursor()
    try:
        for sql in (
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS fraccionable BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS unidades_por_caja INTEGER NULL",
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS unidades_por_docena INTEGER NULL DEFAULT 12",
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS mh_codigo_unidad VARCHAR(4) NOT NULL DEFAULT '59'",
        ):
            cur.execute(sql)
        cur.execute(
            "ALTER TABLE venta_detalles ADD COLUMN IF NOT EXISTS texto_cantidad VARCHAR(80) NULL"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mh_unidad_medida (
                codigo VARCHAR(4) PRIMARY KEY,
                descripcion VARCHAR(240) NOT NULL
            )
            """
        )
        filas = todas_las_filas_cat003()
        for code, desc in filas:
            cur.execute(
                """
                INSERT INTO mh_unidad_medida (codigo, descripcion)
                VALUES (%s, %s)
                ON CONFLICT (codigo) DO UPDATE SET descripcion = EXCLUDED.descripcion
                """,
                (code, desc),
            )
        allowed = tuple(c for c, _ in filas)
        if allowed:
            cur.execute(
                "DELETE FROM mh_unidad_medida WHERE codigo NOT IN %s",
                (allowed,),
            )
        conn.commit()
        print(
            "OK: productos (fraccionable, unidades_por_caja/docena, mh_codigo_unidad), "
            "venta_detalles.texto_cantidad, mh_unidad_medida (cat. 003 listado oficial)."
        )
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
