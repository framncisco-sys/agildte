#!/usr/bin/env python
"""Prueba rápida: guardar presentación extra con desde/hasta/precio."""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import psycopg2
from database import ConexionDB
from azdigital.repositories import presentaciones_repo

db = ConexionDB()
conn = psycopg2.connect(**db.config)
cur = conn.cursor()
try:
    presentaciones_repo.asegurar_columnas_regla_precio(cur)
    cur.execute("SELECT id FROM productos ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if not row:
        print("Sin productos en BD")
        sys.exit(1)
    pid = int(row[0])
    filas = presentaciones_repo.construir_filas_desde_legacy(
        "Unidad base",
        12,
        None,
        extras=[("Tira test", 6.0, "BAR-TIRA-1", 3.0, 10.0, 1.25)],
    )
    presentaciones_repo.reemplazar_todas(cur, pid, filas)
    conn.commit()
    rows = presentaciones_repo.listar_por_producto(cur, pid)
    extras = [r for r in rows if not r[3]]
    print("OK guardado. Filas no-UMB:", len(extras))
    for r in extras:
        print(" ", r)
finally:
    cur.close()
    conn.close()
