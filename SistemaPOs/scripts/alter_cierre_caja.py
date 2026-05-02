# Programador: Oscar Amaya Romero
"""Crea tabla cierre_caja para Corte de Caja bajo esquema DTE El Salvador."""
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
CREATE TABLE IF NOT EXISTS cierre_caja (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    sucursal_id INTEGER,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha_apertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TIMESTAMP,
    monto_apertura NUMERIC(12,2) DEFAULT 0,
    ventas_efectivo NUMERIC(12,2) DEFAULT 0,
    ventas_tarjeta NUMERIC(12,2) DEFAULT 0,
    ventas_credito NUMERIC(12,2) DEFAULT 0,
    ventas_otro NUMERIC(12,2) DEFAULT 0,
    salidas_efectivo NUMERIC(12,2) DEFAULT 0,
    monto_esperado NUMERIC(12,2),
    monto_real NUMERIC(12,2),
    diferencia NUMERIC(12,2),
    estado VARCHAR(16) DEFAULT 'ABIERTO'
)
""")

db.ejecutar_sql("""
CREATE INDEX IF NOT EXISTS idx_cierre_caja_empresa ON cierre_caja(empresa_id)
""")
db.ejecutar_sql("""
CREATE INDEX IF NOT EXISTS idx_cierre_caja_usuario ON cierre_caja(usuario_id)
""")
db.ejecutar_sql("""
CREATE INDEX IF NOT EXISTS idx_cierre_caja_fecha ON cierre_caja(fecha_apertura)
""")

print("OK: Tabla cierre_caja creada.")
