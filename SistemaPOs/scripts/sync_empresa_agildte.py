#!/usr/bin/env python3
"""Sincroniza una o todas las empresas del POS desde GET /api/empresas/{id}/ de AgilDTE."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import psycopg2

from azdigital.integration.agildte_client import obtener_empresa_agildte
from azdigital.repositories import empresas_repo
from database import ConexionDB


def main() -> int:
    p = argparse.ArgumentParser(description="Sync empresas POS ← AgilDTE API")
    p.add_argument("--empresa-id", type=int, default=0, help="ID (0 = todas las filas en empresas)")
    args = p.parse_args()

    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        if args.empresa_id:
            ids = [args.empresa_id]
        else:
            cur.execute("SELECT id FROM empresas ORDER BY id")
            ids = [r[0] for r in cur.fetchall()]
        ok = 0
        for eid in ids:
            data, err = obtener_empresa_agildte(eid)
            if err or not data:
                print(f"Empresa {eid}: ERROR — {err or 'sin datos'}")
                continue
            empresas_repo.aplicar_empresa_agildte_en_bd(cur, eid, data)
            print(f"Empresa {eid}: OK — {data.get('nombre', data.get('nombre_comercial', ''))}")
            ok += 1
        conn.commit()
        print(f"Sincronizadas: {ok}/{len(ids)}")
        return 0 if ok else 1
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
