# Programador: Oscar Amaya Romero
"""Consulta information_schema para columnas de tablas: empresas, sucursales, usuarios, ventas, productos."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar .env
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

from database import ConexionDB

db = ConexionDB()
TABLAS = ["empresas", "sucursales", "usuarios", "ventas", "productos"]

for tabla in TABLAS:
    r = db.ejecutar_sql("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (tabla,), es_select=True)
    print(f"\n=== {tabla.upper()} ===")
    if r:
        for row in r:
            print(f"  {row[0]}: {row[1]} (nullable={row[2]}, default={row[3]})")
    else:
        print("  (tabla no encontrada)")
print()
