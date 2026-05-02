"""Verifica qué usuarios son Superusuario (ADMIN). El único debe ser: admin"""
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
r = db.ejecutar_sql(
    "SELECT id, username, rol FROM usuarios WHERE activo = TRUE ORDER BY id",
    es_select=True,
)
if not r:
    print("No hay usuarios activos.")
    sys.exit(1)

print("Usuarios y sus roles:")
print("-" * 40)
for row in r:
    rl = str(row[2] or "").strip().upper()
    mark = " <- SUPERUSUARIO" if rl in ("ADMIN", "SUPERADMIN") else ""
    print(f"  {row[1]} (id={row[0]}): rol={row[2]}{mark}")

superadmins = [x for x in r if str(x[2] or "").strip().upper() in ("ADMIN", "SUPERADMIN")]
if not superadmins:
    print("\nNo hay Superusuario. Para crear uno ejecute:")
    print("  python scripts/crear_superusuario_sistema.py OAMAYA 123456789")
else:
    print(f"\nSuperusuario(s): {', '.join(s[1] for s in superadmins)}")
    print("Cierre sesión y vuelva a entrar para que carguen las opciones.")
