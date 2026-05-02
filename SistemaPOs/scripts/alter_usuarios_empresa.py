"""Agrega empresa_id a usuarios para multi-tenant."""
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

from database import ConexionDB

db = ConexionDB()
try:
    db.ejecutar_sql("ALTER TABLE usuarios ADD COLUMN empresa_id INTEGER REFERENCES empresas(id)")
except Exception as ex:
    if "already exists" not in str(ex).lower():
        raise
# Poblar empresa_id desde sucursal para usuarios existentes
db.ejecutar_sql("""
    UPDATE usuarios u SET empresa_id = s.empresa_id
    FROM sucursales s WHERE u.sucursal_id = s.id AND (u.empresa_id IS NULL OR u.empresa_id != s.empresa_id)
""")
db.ejecutar_sql("UPDATE usuarios SET empresa_id = 1 WHERE empresa_id IS NULL")
print("OK: empresa_id configurado en usuarios.")
