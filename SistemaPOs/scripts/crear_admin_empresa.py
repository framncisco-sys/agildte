"""Crea un usuario GERENTE (admin de empresa). Uso: python crear_admin_empresa.py USUARIO PASSWORD"""
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

username = sys.argv[1].strip() if len(sys.argv) > 1 else "admin"
password = sys.argv[2] if len(sys.argv) > 2 else "123456"

db = ConexionDB()
conn = psycopg2.connect(**db.config)
cur = conn.cursor()
cur.execute("SELECT id FROM usuarios WHERE TRIM(username) = %s", (username,))
if cur.fetchone():
    print(f"El usuario '{username}' ya existe.")
    conn.close()
    sys.exit(1)

pw_hash = generate_password_hash(password)
cur.execute(
    """
    INSERT INTO usuarios (username, password_hash, rol, sucursal_id, empresa_id, activo)
    VALUES (%s, %s, 'GERENTE', NULL, 1, TRUE)
    RETURNING id
    """,
    (username, pw_hash),
)
row = cur.fetchone()
conn.commit()
cur.close()
conn.close()
print(f"OK: Usuario '{username}' creado como GERENTE (admin de empresa) (id={row[0]}). Contraseña: {password}")
