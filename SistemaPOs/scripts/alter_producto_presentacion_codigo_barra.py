# Programador: Oscar Amaya Romero
"""
Códigos de barras por presentación (six-pack, docena, etc.) ligados al mismo producto_id.

Ejecutar: python scripts/alter_producto_presentacion_codigo_barra.py
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import psycopg2

from database import ConexionDB  # noqa: E402


def _load_dotenv(path: str | None = None) -> None:
    p = path or os.path.join(_ROOT, ".env")
    lines: list[str] | None = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(p, "r", encoding=enc) as f:
                lines = f.readlines()
            break
        except FileNotFoundError:
            return
        except UnicodeDecodeError:
            continue
    if not lines:
        return
    for raw in lines:
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


def main() -> None:
    _load_dotenv()
    db = ConexionDB()
    try:
        conn = psycopg2.connect(**db.config)
    except UnicodeDecodeError as e:
        sql_path = os.path.join(_ROOT, "scripts", "sql", "add_producto_presentacion_codigo_barra.sql")
        print(
            "ERROR: Fallo de codificación al conectar (muy frecuente en Windows: PostgreSQL en español + psycopg2 + Python 3.11+).\n"
            "  El servidor envía un mensaje en Latin-1 y el cliente intenta decodificarlo como UTF-8 (p. ej. byte 0xF3 = «ó» en posición 79).\n\n"
            "  Soluciones (elija una):\n"
            "  A) En postgresql.conf del servidor: lc_messages = 'C'  (reiniciar PostgreSQL) y volver a ejecutar este script.\n"
            "  B) Ejecutar el SQL en pgAdmin o psql (sin este script Python):\n"
            f"      {os.path.abspath(sql_path)}\n\n"
            "  C) Además, guarde .env como UTF-8 y use contraseña codificada en la URL si tiene caracteres especiales.\n\n"
            f"  Detalle: {e}"
        )
        sys.exit(1)
    except psycopg2.OperationalError as e:
        print(f"ERROR: No se pudo conectar a PostgreSQL:\n{e}")
        sys.exit(1)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'producto_presentacion'
            """
        )
        if not cur.fetchone():
            print("AVISO: No existe tabla producto_presentacion. Ejecute antes alter_producto_presentaciones.py")
            sys.exit(1)
        cur.execute(
            """
            ALTER TABLE producto_presentacion
            ADD COLUMN IF NOT EXISTS codigo_barra VARCHAR(64) NULL
            """
        )
        cur.execute(
            """
            ALTER TABLE producto_presentacion
            ADD COLUMN IF NOT EXISTS cantidad_desde NUMERIC(18,6) NULL,
            ADD COLUMN IF NOT EXISTS cantidad_hasta NUMERIC(18,6) NULL,
            ADD COLUMN IF NOT EXISTS precio_regla NUMERIC(18,6) NULL
            """
        )
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_producto_presentacion_codigo_barra
            ON producto_presentacion (upper(trim(codigo_barra)))
            WHERE codigo_barra IS NOT NULL AND length(trim(codigo_barra)) > 0
            """
        )
        conn.commit()
        print("OK: producto_presentacion.codigo_barra + índice único (por código normalizado).")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
