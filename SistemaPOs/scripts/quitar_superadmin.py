"""Quita SUPERADMIN a un usuario. Uso: python quitar_superadmin.py <username>"""
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

if len(sys.argv) < 2:
    print("Uso: python quitar_superadmin.py <username>")
    sys.exit(1)

username = sys.argv[1].strip()
db = ConexionDB()
conn = psycopg2.connect(**db.config)
cur = conn.cursor()
cur.execute(
    "UPDATE usuarios SET rol = 'ADMIN' WHERE TRIM(username) = %s RETURNING id, username",
    (username,),
)
r = cur.fetchall()
conn.commit()
cur.close()
conn.close()
if r:
    print(f"OK: '{r[0][1]}' (id={r[0][0]}) ahora es ADMIN. Ya no es superusuario.")
else:
    print(f"No se encontró usuario '{username}'.")
