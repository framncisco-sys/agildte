#!/usr/bin/env python3
# Programador: Oscar Amaya Romero
"""
Remite a AgilDTE las ventas POS que quedaron solo en local (sin código de generación).

Uso (dentro del contenedor posagil):
  python scripts/remitir_tickets_sin_codigo.py
  python scripts/remitir_tickets_sin_codigo.py --desde 2026-09-11
  python scripts/remitir_tickets_sin_codigo.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.chdir(ROOT)


def _listar_pendientes(cur, desde: str | None):
    sql = """
        SELECT v.id, v.empresa_id, v.fecha_registro, v.total_pagar,
               COALESCE(v.tipo_comprobante, 'TICKET'),
               COALESCE(v.cliente_nombre, '')
        FROM ventas v
        WHERE COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
          AND TRIM(COALESCE(v.codigo_generacion, '')) = ''
          AND UPPER(COALESCE(v.tipo_comprobante, 'TICKET')) IN ('TICKET', 'FACTURA', 'CREDITO_FISCAL')
    """
    params: list = []
    if desde:
        sql += " AND v.fecha_registro::date >= %s"
        params.append(desde)
    sql += " ORDER BY v.id ASC"
    cur.execute(sql, tuple(params))
    return cur.fetchall() or []


def _contar_sin_codigo(cur) -> int:
    cur.execute(
        """
        SELECT COUNT(*) FROM ventas v
        WHERE COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
          AND TRIM(COALESCE(v.codigo_generacion, '')) = ''
          AND UPPER(COALESCE(v.tipo_comprobante, 'TICKET')) IN ('TICKET', 'FACTURA', 'CREDITO_FISCAL')
        """
    )
    return int((cur.fetchone() or [0])[0] or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Remite tickets POS sin código de generación.")
    parser.add_argument("--desde", default=None, help="Fecha YYYY-MM-DD (inclusive)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pausa", type=float, default=0.4, help="Segundos entre envíos")
    args = parser.parse_args()

    from app import create_app

    create_app()

    import psycopg2
    from database import ConexionDB
    from azdigital.integration.agildte_sync import remitir_venta_existente
    from azdigital.utils.alerta_operativa import alertar_modo_local

    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        filas = _listar_pendientes(cur, args.desde)
        print(f"Pendientes sin código: {len(filas)}")
        if not filas:
            print("OK: no hay tickets locales sin código de generación.")
            return 0
        for vid, emp, fecha, total, tipo, cliente in filas:
            print(f"  #{vid} emp={emp} {fecha} {tipo} ${float(total or 0):.2f} {cliente}")
        if args.dry_run:
            print("Dry-run: no se remitió nada.")
            return 0

        ok_n = 0
        fail_n = 0
        errores: list[str] = []
        for vid, emp, fecha, total, tipo, cliente in filas:
            emp_id = int(emp) if emp is not None else 0
            if emp_id <= 0:
                fallback = (os.environ.get("AGILDTE_EMPRESA_ID") or "").strip()
                emp_id = int(fallback) if fallback.isdigit() else 0
            if emp_id <= 0:
                fail_n += 1
                errores.append(f"#{vid}: sin empresa_id")
                print(f"FALLO #{vid}: sin empresa_id")
                continue
            try:
                result = remitir_venta_existente(
                    cur=cur,
                    empresa_id_local=emp_id,
                    venta_id_local=int(vid),
                )
                conn.commit()
                if result.get("ok") and result.get("dte_persistido"):
                    ok_n += 1
                    print(f"OK #{vid} codigo persistido")
                elif result.get("ok"):
                    ok_n += 1
                    print(f"OK #{vid} (AgilDTE respondió; dte_persistido={result.get('dte_persistido')})")
                else:
                    fail_n += 1
                    msg = result.get("mensaje_usuario") or result.get("error") or str(result)
                    errores.append(f"#{vid}: {msg}")
                    print(f"FALLO #{vid}: {msg}")
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                fail_n += 1
                errores.append(f"#{vid}: {e}")
                print(f"FALLO #{vid}: {e}")
            time.sleep(max(0.0, args.pausa))

        quedan = _contar_sin_codigo(cur)
        print(f"Resumen: ok={ok_n} fallo={fail_n} quedan_sin_codigo={quedan}")
        if quedan > 0:
            det = "\n".join(errores[:20])
            alertar_modo_local(
                f"{quedan} ticket(s) siguen solo en POS sin código de generación.",
                detalle=det or "Remisión parcial o fallida.",
                forzar=True,
            )
            return 2
        print("OK: no queda ticket local sin código de generación.")
        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
