"""Crea el superusuario inicial del sistema (SUPERADMIN). Usa .env para la conexión."""
import os
import sys
import getpass

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

print("=== Crear Superusuario del Sistema ===\n")
if len(sys.argv) >= 3:
    username = sys.argv[1].strip()
    password = sys.argv[2]
    print(f"Usuario: {username}")
else:
    username = input("Usuario [admin]: ").strip() or "admin"
    password = getpass.getpass("Contraseña (no se muestra): ").strip()
if not password:
    print("ERROR: la contraseña no puede estar vacía.")
    sys.exit(1)

pw_hash = generate_password_hash(password)

db = ConexionDB()
conn = psycopg2.connect(**db.config)
cur = conn.cursor()

cur.execute(
    """
    INSERT INTO usuarios (username, password_hash, rol, sucursal_id, empresa_id, activo)
    VALUES (%s, %s, 'ADMIN', NULL, 1, TRUE)
    RETURNING id
    """,
    (username, pw_hash),
)
row = cur.fetchone()
conn.commit()
cur.close()
conn.close()

if row:
    print(f"\nOK: Superusuario '{username}' (id={row[0]}) creado correctamente.")
    print("Puede iniciar sesión, cambiar empresa y gestionar todo el sistema.")
else:
    print("ERROR: no se pudo crear el usuario.")
    sys.exit(1)
