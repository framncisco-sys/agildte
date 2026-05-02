"""Recrea el usuario 'admin' como SUPERADMIN para pruebas. Contraseña: admin"""
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

from werkzeug.security import generate_password_hash
import psycopg2
from database import ConexionDB

db = ConexionDB()
conn = psycopg2.connect(**db.config)
cur = conn.cursor()

cur.execute("SELECT id FROM usuarios WHERE TRIM(username) = 'admin'")
if cur.fetchone():
    print("El usuario 'admin' ya existe. Para eliminarlo: python scripts/eliminar_admin_definitivo.py")
    conn.close()
    sys.exit(1)

pw_hash = generate_password_hash("admin")
cur.execute(
    """
    INSERT INTO usuarios (username, password_hash, rol, sucursal_id, empresa_id, activo)
    VALUES ('admin', %s, 'SUPERADMIN', NULL, 1, TRUE)
    """,
    (pw_hash,),
)
conn.commit()
cur.execute("SELECT id FROM usuarios WHERE TRIM(username) = 'admin'")
r = cur.fetchone()
cur.close()
conn.close()

print("OK: Usuario 'admin' creado como SUPERADMIN.")
print("  Contraseña: admin")
print("Cierre sesión, inicie con 'admin' y verifique si ve el selector de empresas.")
