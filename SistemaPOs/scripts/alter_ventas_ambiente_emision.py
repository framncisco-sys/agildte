# Programador: Oscar Amaya Romero
"""
Columna ambiente_emision en ventas (misma convención AgilDTE):
  '00' = producción (api MH)
  '01' = pruebas (apitest)

Ejecutar en SistemaPOs: docker compose exec posagil python scripts/alter_ventas_ambiente_emision.py
"""
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

cfg = ConexionDB().config
conn = psycopg2.connect(**cfg)
cur = conn.cursor()
try:
    cur.execute(
        """
        ALTER TABLE ventas
        ADD COLUMN IF NOT EXISTS ambiente_emision VARCHAR(2) DEFAULT NULL
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ventas_ambiente_emision
        ON ventas (empresa_id, ambiente_emision)
        """
    )
    # Histórico sin marcar: asumir pruebas (01) para no mezclar en vista producción
    cur.execute(
        """
        UPDATE ventas
        SET ambiente_emision = '01'
        WHERE ambiente_emision IS NULL
        """
    )
    # Opcional: marcar producción reciente (fecha corte en .env AGILDTE_AMBIENTE_CORTE_FECHA=YYYY-MM-DD)
    corte = (os.environ.get("AGILDTE_AMBIENTE_CORTE_FECHA") or "").strip()
    if corte:
        cur.execute(
            """
            UPDATE ventas
            SET ambiente_emision = '00'
            WHERE ambiente_emision = '01'
              AND sello_recepcion IS NOT NULL
              AND TRIM(sello_recepcion) <> ''
              AND fecha_registro::date >= %s::date
            """,
            (corte,),
        )
    conn.commit()
    print("OK: ventas.ambiente_emision agregado (histórico en '01'; use AGILDTE_AMBIENTE_CORTE_FECHA para marcar producción).")
finally:
    cur.close()
    conn.close()
