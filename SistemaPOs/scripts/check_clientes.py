"""Verifica si existe la tabla clientes y su estructura."""
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
r = db.ejecutar_sql("""
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'clientes' 
ORDER BY ordinal_position
""", es_select=True)

if r:
    print("Tabla clientes YA EXISTE. Columnas:")
    for row in r:
        print("  -", row[0], ":", row[1])
else:
    print("No existe tabla 'clientes' en la base de datos.")
    # Listar tablas existentes
    tablas = db.ejecutar_sql("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' ORDER BY table_name
    """, es_select=True)
    if tablas:
        print("\nTablas existentes:", [t[0] for t in tablas])
