from __future__ import annotations

import getpass
import os
import sys

from werkzeug.security import generate_password_hash

def main() -> None:
    print("=== Crear superusuario AZ DIGITAL ===")

    # Importante: libpq/psycopg2 leen PGCLIENTENCODING al cargar/conectar.
    # Esto evita UnicodeDecodeError cuando el servidor devuelve mensajes en WIN1252/LATIN1.
    az_enc = (os.environ.get("AZ_DB_CLIENT_ENCODING") or "").strip() or "WIN1252"
    os.environ["PGCLIENTENCODING"] = az_enc

    # Pedir credenciales de PostgreSQL aquí (para evitar confusiones con PowerShell)
    print("\n--- Conexión a PostgreSQL ---")
    db_host = input(f"Host [127.0.0.1]: ").strip() or "127.0.0.1"
    db_port = input(f"Puerto [5432]: ").strip() or "5432"
    db_name = input(f"Base de datos [saas_facturacion]: ").strip() or "saas_facturacion"
    db_user = input(f"Usuario DB [postgres]: ").strip() or "postgres"
    db_password = getpass.getpass("Password DB (PostgreSQL): ").strip()
    if not db_password:
        print("ERROR: password DB vacío.")
        return

    os.environ["AZ_DB_HOST"] = db_host
    os.environ["AZ_DB_PORT"] = db_port
    os.environ["AZ_DB_NAME"] = db_name
    os.environ["AZ_DB_USER"] = db_user
    os.environ["AZ_DB_PASSWORD"] = db_password
    os.environ["AZ_DB_CLIENT_ENCODING"] = az_enc

    username = input("Usuario [OAMAYA]: ").strip() or "OAMAYA"
    password = getpass.getpass("Contraseña (no se muestra al escribir): ").strip()
    if not password:
        print("ERROR: contraseña vacía.")
        return

    rol = "ADMIN"
    sucursal_id = None

    # Import después de setear env vars/encoding
    from database import ConexionDB

    db = ConexionDB()
    pw_hash = generate_password_hash(password)

    ok = db.ejecutar_sql(
        "INSERT INTO usuarios (username, password_hash, rol, sucursal_id, activo) VALUES (%s, %s, %s, %s, TRUE)",
        (username, pw_hash, rol, sucursal_id),
        es_select=False,
    )
    print("OK: usuario creado." if ok else "ERROR: no se pudo crear (revisa conexión DB / esquema).")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR inesperado:", type(e).__name__, repr(e))
        sys.exit(1)

