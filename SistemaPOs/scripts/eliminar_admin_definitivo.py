"""Elimina el usuario 'admin' por completo de la base de datos."""
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

db = ConexionDB()
conn = psycopg2.connect(**db.config)
cur = conn.cursor()

# Obtener id de admin y OAMAYA
cur.execute("SELECT id FROM usuarios WHERE TRIM(username) = 'admin'")
admin_row = cur.fetchone()
cur.execute("SELECT id FROM usuarios WHERE TRIM(username) = 'OAMAYA'")
oamaya_row = cur.fetchone()

if not admin_row:
    print("Usuario 'admin' no encontrado. Ya fue eliminado.")
    conn.close()
    sys.exit(0)

admin_id = admin_row[0]
oamaya_id = oamaya_row[0] if oamaya_row else None

# 1. Reasignar ventas de admin a OAMAYA (para no perder historial)
try:
    if oamaya_id:
        cur.execute("UPDATE ventas SET usuario_id = %s WHERE usuario_id = %s", (oamaya_id, admin_id))
        n = cur.rowcount
        if n > 0:
            print(f"  Reasignadas {n} ventas de admin a OAMAYA")
except Exception as e:
    print(f"  Aviso al reasignar ventas: {e}")

# 2. Eliminar usuario admin (DELETE físico)
cur.execute("DELETE FROM usuarios WHERE id = %s", (admin_id,))
deleted = cur.rowcount
conn.commit()
cur.close()
conn.close()

if deleted:
    print("OK: Usuario 'admin' eliminado permanentemente de la base de datos.")
else:
    print("No se pudo eliminar 'admin'.")
