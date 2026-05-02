#!/usr/bin/env python
"""
Script de diagnóstico: verifica que el sistema esté listo para usar.
Ejecutar: python scripts/verificar_sistema.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar .env igual que la app
def _load_dotenv(path=".env"):
    try:
        p = os.path.join(os.path.dirname(os.path.dirname(__file__)), path)
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
    except FileNotFoundError:
        pass
_load_dotenv()

print("=== Verificación del Sistema AZ DIGITAL ===\n")

# 1. Base de datos
try:
    from database import ConexionDB
    db = ConexionDB()
    r = db.ejecutar_sql("SELECT 1", (), es_select=True)
    if r is not None:
        print("[OK] Conexión a base de datos")
    else:
        print("[ERROR] No se pudo conectar. Verifique .env (AZ_DB_PASSWORD, etc.)")
        sys.exit(1)
except Exception as e:
    print("[ERROR] Base de datos:", e)
    sys.exit(1)

# 2. Usuario admin
try:
    import psycopg2
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    cur.execute("SELECT id, username, rol FROM usuarios WHERE activo = TRUE AND rol IN ('ADMIN','SUPERADMIN')")
    admins = cur.fetchall()
    cur.close()
    conn.close()
    if admins:
        print("[OK] Superusuario(es):", ", ".join(f"{a[1]} (rol={a[2]})" for a in admins))
    else:
        print("[AVISO] No hay usuario ADMIN/SUPERADMIN. Ejecute: python scripts/configurar_admin_unico.py")
except Exception as e:
    print("[ERROR] Usuarios:", e)

# 3. Empresas
try:
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    cur.execute("SELECT id, nombre_comercial FROM empresas LIMIT 5")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if rows:
        print("[OK] Empresas:", len(rows), "en BD")
    else:
        print("[AVISO] No hay empresas. Cree una en la base de datos.")
except Exception as e:
    try:
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        cur.execute("SELECT id, nombre FROM empresas LIMIT 5")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        print("[OK] Empresas (columna nombre):", len(rows) if rows else 0)
    except Exception as e2:
        print("[ERROR] Empresas:", e2)

# 4. App Flask
try:
    from app import app
    with app.test_client() as c:
        r = c.get("/login")
        if r.status_code == 200:
            print("[OK] Aplicación Flask responde en /login")
        else:
            print("[AVISO] /login devolvió:", r.status_code)
except Exception as e:
    print("[ERROR] App Flask:", e)

print("\n--- Pasos para usar el sistema ---")
print("1. Ejecute: python app.py")
_puerto = os.environ.get("AZ_PORT") or os.environ.get("PORT") or "5000"
print(f"2. Abra: http://127.0.0.1:{_puerto}")
print("3. Inicie sesión con el usuario admin")
print("4. Si es SUPERUSUARIO: primero elija una empresa (clic en 'Entrar')")
print("5. Luego use: Configuración, Clientes, Inventario, etc.")
print("\nSi algo falla, revise server.log")
print("\nMulti-empresa (empresas, usuarios, productos por tenant): python scripts/verificar_multiempresa.py")
