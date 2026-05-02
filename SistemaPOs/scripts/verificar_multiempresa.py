#!/usr/bin/env python
"""
Auditoría multi-empresa (PosAgil + alineación con AgilDTE).

Ejecutar desde la raíz del proyecto:
  python scripts/verificar_multiempresa.py

Comprueba: conexión, tabla empresas, reparto de usuarios/productos por empresa_id,
y resume limitaciones conocidas frente a AgilDTE multi-tenant.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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

print("=== Auditoría multi-empresa — PosAgil ===\n")

try:
    import psycopg2
    from database import ConexionDB

    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
except Exception as e:
    print("[ERROR] No se pudo conectar a PostgreSQL:", e)
    sys.exit(1)

ok = True


def q(sql, params=None):
    cur.execute(sql, params or ())
    return cur.fetchall()


try:
    # 1) Empresas
    try:
        rows = q("SELECT id, COALESCE(nombre_comercial, nombre) FROM empresas ORDER BY id")
    except Exception:
        rows = q("SELECT id, COALESCE(nombre, '') FROM empresas ORDER BY id")
    print(f"[1] Empresas en BD: {len(rows)}")
    for r in rows[:20]:
        print(f"    - id={r[0]}  {r[1][:60] if r[1] else ''}")
    if len(rows) > 20:
        print(f"    ... y {len(rows) - 20} más")
    if not rows:
        print("    [AVISO] Sin empresas: el POS espera al menos una fila en `empresas`.")
        ok = False

    # 2) Usuarios por empresa (si existe columna)
    try:
        dist = q(
            """
            SELECT COALESCE(u.empresa_id, s.empresa_id, 0) AS eid, COUNT(*)
            FROM usuarios u
            LEFT JOIN sucursales s ON s.id = u.sucursal_id
            WHERE u.activo = TRUE
            GROUP BY 1 ORDER BY 1
            """
        )
        print("\n[2] Usuarios activos por empresa (empresa_id usuario o vía sucursal):")
        for eid, cnt in dist:
            print(f"    empresa {eid}: {cnt} usuario(s)")
    except Exception as ex:
        print("\n[2] No se pudo agrupar usuarios por empresa:", ex)

    # 3) Productos por empresa
    try:
        pdist = q(
            "SELECT COALESCE(empresa_id, 0), COUNT(*) FROM productos GROUP BY 1 ORDER BY 1"
        )
        print("\n[3] Productos por empresa_id:")
        for eid, cnt in pdist[:15]:
            print(f"    empresa {eid}: {cnt} producto(s)")
        if len(pdist) > 15:
            print(f"    ... ({len(pdist)} grupos)")
    except Exception as ex:
        print("\n[3] Tabla productos / empresa_id:", ex)

    # 4) Ventas recientes multi-empresa
    try:
        vdist = q(
            """
            SELECT COALESCE(empresa_id, 0), COUNT(*)
            FROM ventas
            WHERE fecha_registro >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY 1 ORDER BY 2 DESC
            """
        )
        print("\n[4] Ventas últimos 30 días por empresa_id:")
        for eid, cnt in vdist[:15]:
            print(f"    empresa {eid}: {cnt} venta(s)")
    except Exception as ex:
        print("\n[4] Resumen ventas por empresa:", ex)

finally:
    try:
        cur.close()
        conn.close()
    except Exception:
        pass

print(
    """

--- Conclusión (diseño actual) ---

• El modelo PosAgil ya contempla VARIAS empresas: tabla `empresas`, `empresa_id` en
  ventas/productos/usuarios (vía sucursal), y sesión Flask con `session['empresa_id']`.
• Los usuarios ADMIN/SUPERADMIN pueden cambiar de empresa con la ruta `/entrar_empresa/<id>`.
• El SSO desde AgilDTE usa el mismo `username` y toma la empresa del usuario en la BD local;
  los IDs de empresa en Django (AgilDTE) y en PosAgil deben estar alineados si comparten
  catálogo o sync (misma convención de empresa_id / mapeo explícito en integración).

• Carga y concurrencia: PostgreSQL en contenedor dedicado es adecuado para varias empresas
  y varios procesos; escalar = más CPU/RAM al servicio `db`, índices en consultas pesadas,
  y pool de conexiones si en el futuro se centraliza el acceso a datos.

"""
)

sys.exit(0 if ok else 1)
