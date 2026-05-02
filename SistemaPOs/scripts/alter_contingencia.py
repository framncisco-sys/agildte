# Programador: Oscar Amaya Romero
"""Plan de Contingencia MH: tabla evento_contingencia y columna causa_contingencia en ventas."""
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

# Causa contingencia en ventas (1=MH, 2=Internet, 3=Energía, 4=Sistema)
db.ejecutar_sql(
    "ALTER TABLE ventas ADD COLUMN IF NOT EXISTS causa_contingencia SMALLINT"
)

# Tabla evento_contingencia: para enviar Evento tipo 1 al MH
db.ejecutar_sql("""
    CREATE TABLE IF NOT EXISTS evento_contingencia (
        id SERIAL PRIMARY KEY,
        empresa_id INTEGER NOT NULL,
        fecha_inicio TIMESTAMP NOT NULL,
        fecha_fin TIMESTAMP NOT NULL,
        causa SMALLINT NOT NULL,
        descripcion_causa VARCHAR(100),
        estado VARCHAR(32) DEFAULT 'PENDIENTE',
        json_enviado TEXT,
        respuesta_mh TEXT,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Índice para listar por empresa
db.ejecutar_sql("""
    CREATE INDEX IF NOT EXISTS idx_evento_contingencia_empresa
    ON evento_contingencia(empresa_id)
""")

print("OK: Plan de Contingencia — evento_contingencia y causa_contingencia.")
