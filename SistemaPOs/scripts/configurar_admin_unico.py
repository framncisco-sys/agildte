"""Configura 'admin' como ÚNICO superusuario. Quita superuser a OAMAYA, ADMIN y demás."""
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

# 1. Quitar superuser a TODOS (luego pondremos solo admin)
cur.execute("""
    UPDATE usuarios SET rol = 'GERENTE'
    WHERE UPPER(TRIM(rol)) IN ('ADMIN', 'SUPERADMIN')
    RETURNING id, username
""")
cambiados = cur.fetchall()
for r in cambiados:
    print(f"  {r[1]} (id={r[0]}): rol cambiado a GERENTE")

# 2. Buscar usuario admin (preferir 'admin' exacto sobre 'ADMIN')
cur.execute("""
    SELECT id, username FROM usuarios
    WHERE LOWER(TRIM(username)) = 'admin'
    ORDER BY CASE WHEN TRIM(username) = 'admin' THEN 0 ELSE 1 END
""")
rows = cur.fetchall()

pw_hash = generate_password_hash(PASSWORD_ADMIN)
admin_id = None

if rows:
    # Usar el primero que coincida (admin o ADMIN)
    admin_id = rows[0][0]
    cur.execute(
        "UPDATE usuarios SET username = 'admin', rol = 'ADMIN', password_hash = %s, activo = TRUE WHERE id = %s",
        (pw_hash, admin_id),
    )
    # Si hay más de uno (ej: admin y ADMIN), desactivar o cambiar el duplicado
    for r in rows[1:]:
        cur.execute(
            "UPDATE usuarios SET rol = 'GERENTE', activo = FALSE WHERE id = %s",
            (r[0],),
        )
        print(f"  Usuario duplicado '{r[1]}' (id={r[0]}): desactivado")
    print(f"\nOK: Usuario 'admin' (id={admin_id}) configurado como único Superusuario.")
else:
    cur.execute(
        """
        INSERT INTO usuarios (username, password_hash, rol, sucursal_id, empresa_id, activo)
        VALUES ('admin', %s, 'ADMIN', NULL, 1, TRUE)
        RETURNING id
        """,
        (pw_hash,),
    )
    admin_id = cur.fetchone()[0]
    print(f"\nOK: Usuario 'admin' (id={admin_id}) creado como único Superusuario.")

conn.commit()
cur.close()
conn.close()

print(f"\n--- ÚNICO SUPERUSUARIO ---")
print(f"  Usuario: admin")
print(f"  Contraseña: {PASSWORD_ADMIN}")
print("\nCierre sesión y entre como 'admin' para gestionar todo el sistema.")
