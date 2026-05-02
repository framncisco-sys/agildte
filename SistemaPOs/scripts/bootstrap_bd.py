#!/usr/bin/env python
"""
Aplica el esquema PosAgil: mínimo (empresas, usuarios) + tablas POS + compras/proveedores
si faltan.

Uso: python scripts/bootstrap_bd.py
Requiere variables AZ_DB_* o DATABASE_URL en .env

Si la BD ya existía solo con el esquema mínimo, ejecutar este script una vez (o recrear el
volumen de Postgres para que docker-entrypoint vuelva a correr los .sql).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_dotenv():
    p = os.path.join(ROOT, ".env")
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
    except FileNotFoundError:
        pass


_load_dotenv()


def _run_sql_script(conn, sql_text: str) -> None:
    """Ejecuta sentencias separadas por ';' (sin punto y coma dentro de funciones)."""
    lines = []
    for line in sql_text.splitlines():
        if line.strip().startswith("--"):
            continue
        lines.append(line)
    buf = "\n".join(lines)
    cur = conn.cursor()
    for part in buf.split(";"):
        st = part.strip()
        if not st:
            continue
        cur.execute(st)
    cur.close()


SQL_SCRIPTS = (
    "schema_bootstrap_min.sql",
    "schema_bootstrap_pos_extensions.sql",
    "schema_bootstrap_compras_proveedores.sql",
    "schema_bootstrap_kardex_promos_contingencia.sql",
)


def main() -> None:
    import psycopg2
    from database import ConexionDB

    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    try:
        for name in SQL_SCRIPTS:
            sql_path = os.path.join(ROOT, "scripts", name)
            with open(sql_path, "r", encoding="utf-8") as f:
                sql = f.read()
            _run_sql_script(conn, sql)
        conn.commit()
        print("OK: esquema aplicado (POS, compras, kardex, promociones, contingencia).")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e)
        sys.exit(1)
