# Programador: Oscar Amaya Romero
"""Crea tabla actividades_economicas e importa desde ACTIVIDADES-ECONÓMICAS-1.xlsx"""
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

EXCEL_PATH = os.path.join(
    os.path.expanduser("~"),
    "Downloads",
    "ACTIVIDADES-ECONÓMICAS-1.xlsx",
)

def main():
    if not os.path.exists(EXCEL_PATH):
        print(f"No se encontró el archivo: {EXCEL_PATH}")
        print("Coloque ACTIVIDADES-ECONÓMICAS-1.xlsx en la carpeta Descargas.")
        sys.exit(1)

    try:
        import openpyxl
    except ImportError:
        print("Instale openpyxl: pip install openpyxl")
        sys.exit(1)

    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb.active

    filas = []
    for row in ws.iter_rows(min_row=1, values_only=True):
        if not row or len(row) < 2:
            continue
        cod = row[0]
        desc = row[1]
        if not cod or not desc:
            continue
        cod_str = str(cod).strip()
        if not cod_str or not cod_str[0].isdigit():
            continue
        desc_str = (desc or "").strip()[:500]
        if desc_str:
            filas.append((cod_str, desc_str))

    wb.close()
    print(f"Leídas {len(filas)} actividades del Excel.")

    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS actividades_economicas (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(20) NOT NULL UNIQUE,
                descripcion VARCHAR(500) NOT NULL
            )
        """)
        cur.execute("DELETE FROM actividades_economicas")
        cur.executemany(
            "INSERT INTO actividades_economicas (codigo, descripcion) VALUES (%s, %s)",
            filas,
        )
        conn.commit()
        print(f"OK: {len(filas)} actividades económicas importadas.")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
