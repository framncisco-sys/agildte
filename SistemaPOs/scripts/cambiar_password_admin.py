"""Cambia la contraseña del usuario admin. Uso: python cambiar_password_admin.py <nueva_password>"""
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

password = sys.argv[1] if len(sys.argv) > 1 else "123456789"
pw_hash = generate_password_hash(password)

db = ConexionDB()
conn = psycopg2.connect(**db.config)
cur = conn.cursor()
cur.execute(
    "UPDATE usuarios SET password_hash = %s WHERE TRIM(username) = 'admin' RETURNING id",
    (pw_hash,),
)
r = cur.fetchone()
conn.commit()
cur.close()
conn.close()

if r:
    print(f"OK: Contraseña de 'admin' actualizada.")
else:
    print("Error: Usuario 'admin' no encontrado.")
