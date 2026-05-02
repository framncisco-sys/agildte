# Programador: Oscar Amaya Romero
"""Agrega descuento y total_bruto a ventas para cumplir con MH (Precio Unitario, Monto Descuento, Venta Gravada)."""
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
db.ejecutar_sql("ALTER TABLE ventas ADD COLUMN IF NOT EXISTS descuento NUMERIC(10, 2) DEFAULT 0")
db.ejecutar_sql("ALTER TABLE ventas ADD COLUMN IF NOT EXISTS total_bruto NUMERIC(10, 2)")
db.ejecutar_sql("UPDATE ventas SET total_bruto = total_pagar, descuento = 0 WHERE total_bruto IS NULL")
print("OK: Columnas descuento y total_bruto agregadas a ventas (compatibilidad MH).")
