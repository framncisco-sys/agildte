# Programador: Oscar Amaya Romero
"""Crea tabla historial_usuarios para registro de accesos y acciones de usuarios."""
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
db.ejecutar_sql("""
    CREATE TABLE IF NOT EXISTS historial_usuarios (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER REFERENCES usuarios(id),
        username VARCHAR(100),
        evento VARCHAR(50) NOT NULL,
        detalle TEXT,
        ip_address VARCHAR(45),
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
db.ejecutar_sql("""
    CREATE INDEX IF NOT EXISTS idx_historial_usuarios_usuario_id
    ON historial_usuarios(usuario_id)
""")
db.ejecutar_sql("""
    CREATE INDEX IF NOT EXISTS idx_historial_usuarios_created_at
    ON historial_usuarios(created_at DESC)
""")
db.ejecutar_sql("""
    CREATE INDEX IF NOT EXISTS idx_historial_usuarios_evento
    ON historial_usuarios(evento)
""")
print("OK: Tabla historial_usuarios creada.")
