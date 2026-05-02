"""Borra TODOS los usuarios excepto 'admin'. Solo queda admin como superusuario."""
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

PASSWORD_ADMIN = "123456789"

db = ConexionDB()
conn = psycopg2.connect(**db.config)
cur = conn.cursor()

# 1. Obtener id de admin (el que tiene username = 'admin', preferir lowercase)
cur.execute("""
    SELECT id FROM usuarios WHERE LOWER(TRIM(username)) = 'admin'
    ORDER BY CASE WHEN TRIM(username) = 'admin' THEN 0 ELSE 1 END
    LIMIT 1
""")
admin_row = cur.fetchone()

if not admin_row:
    print("ERROR: No existe usuario 'admin'. Cree uno primero con configurar_admin_unico.py")
    conn.close()
    sys.exit(1)

admin_id = admin_row[0]

# 2. Reasignar ventas de usuarios eliminados a admin
cur.execute("UPDATE ventas SET usuario_id = %s WHERE usuario_id != %s", (admin_id, admin_id))
reasignadas = cur.rowcount
if reasignadas > 0:
    print(f"  Reasignadas {reasignadas} ventas a admin")

# 3. Borrar TODOS los usuarios excepto admin
cur.execute("DELETE FROM usuarios WHERE id != %s", (admin_id,))
borrados = cur.rowcount

# 4. Asegurar que admin sea ADMIN con la contraseña correcta
pw_hash = generate_password_hash(PASSWORD_ADMIN)
cur.execute(
    "UPDATE usuarios SET username = 'admin', rol = 'ADMIN', password_hash = %s, activo = TRUE WHERE id = %s",
    (pw_hash, admin_id),
)

conn.commit()
cur.close()
conn.close()

print(f"\nOK: {borrados} usuario(s) eliminados. Solo queda 'admin'.")
print(f"  Usuario: admin")
print(f"  Contraseña: {PASSWORD_ADMIN}")
print("\nCierre sesión y entre como 'admin'.")
