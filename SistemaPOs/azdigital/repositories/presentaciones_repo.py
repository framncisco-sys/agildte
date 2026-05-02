# Programador: Oscar Amaya Romero
"""Presentaciones de venta: factores respecto a la UMB (unidad de medida base) del producto."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


def _inferir_caja_desde_nombre(nombre_producto: str | None) -> int | None:
    """Ej. 'CAJA ... 60 SOBRES' → 60 para completar presentación Caja en POS."""
    if not nombre_producto:
        return None
    m = re.search(r"(\d+)\s*SOBRES?\b", nombre_producto.upper())
    if m:
        n = int(m.group(1))
        return n if n > 0 else None
    return None


def _inferir_etiqueta_umb_desde_nombre(nombre_producto: str | None, umb_desde_bd: str) -> str:
    """Si en BD sigue 'Unidad base' pero el nombre del artículo dice SOBRES/LIBRA, sugerir etiqueta UMB en POS."""
    u = (umb_desde_bd or "").strip()
    if u and u.lower() not in ("unidad base", "umb"):
        return u[:80]
    if not nombre_producto:
        return u or "Unidad base"
    nu = nombre_producto.upper()
    if "SOBRE" in nu:
        return "Sobre"
    if "LIBRA" in nu:
        return "Libra"
    return u or "Unidad base"


def tabla_existe(cur) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s",
        ("producto_presentacion",),
    )
    return cur.fetchone() is not None


def listar_por_producto(cur, producto_id: int) -> list[tuple[Any, ...]]:
    """Filas: id, nombre, factor_umb, es_umb, orden."""
    if not tabla_existe(cur):
        return []
    cur.execute(
        """
        SELECT id, nombre, factor_umb, es_umb, orden
        FROM producto_presentacion
        WHERE producto_id = %s
        ORDER BY orden NULLS LAST, id
        """,
        (producto_id,),
    )
    return list(cur.fetchall() or [])


def nombres_umb_por_productos(cur, producto_ids: list[int]) -> dict[int, str]:
    """Nombre de la presentación UMB (es_umb o primera por factor 1) por producto_id."""
    if not producto_ids or not tabla_existe(cur):
        return {}
    try:
        cur.execute(
            """
            SELECT DISTINCT ON (producto_id) producto_id, nombre
            FROM producto_presentacion
            WHERE producto_id = ANY(%s)
            ORDER BY producto_id, CASE WHEN es_umb THEN 0 ELSE 1 END, id
            """,
            (list(producto_ids),),
        )
        return {
            int(r[0]): str(r[1] or "").strip()
            for r in (cur.fetchall() or [])
            if r and r[1] and str(r[1]).strip()
        }
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return {}


def nombre_umb_producto(cur, producto_id: int) -> str:
    """Etiqueta corta para formularios (Kardex, reportes)."""
    m = nombres_umb_por_productos(cur, [int(producto_id)])
    return m.get(int(producto_id)) or "Unidad base"


def factor_por_id(cur, presentacion_id: int, producto_id: int) -> Decimal | None:
    r = fila_por_id(cur, presentacion_id, producto_id)
    return r[0] if r else None


def fila_por_id(cur, presentacion_id: int, producto_id: int) -> tuple[Decimal, str] | None:
    if not tabla_existe(cur):
        return None
    cur.execute(
        """
        SELECT factor_umb, nombre FROM producto_presentacion
        WHERE id = %s AND producto_id = %s
        """,
        (presentacion_id, producto_id),
    )
    r = cur.fetchone()
    if not r or r[0] is None:
        return None
    try:
        return Decimal(str(r[0])), str(r[1] or "").strip() or "Presentación"
    except (InvalidOperation, ValueError):
        return None


def buscar_por_factor(cur, producto_id: int, fac: Decimal) -> tuple[int, str] | None:
    """Primera presentación con ese factor (validación de factor enviado desde POS offline)."""
    if not tabla_existe(cur):
        return None
    cur.execute(
        """
        SELECT id, nombre FROM producto_presentacion
        WHERE producto_id = %s AND factor_umb = %s
        ORDER BY id
        LIMIT 1
        """,
        (producto_id, fac),
    )
    r = cur.fetchone()
    if not r:
        return None
    return int(r[0]), str(r[1] or "").strip() or "Presentación"


def factores_permitidos(cur, producto_id: int) -> set[Decimal]:
    rows = listar_por_producto(cur, producto_id)
    out: set[Decimal] = set()
    for r in rows:
        try:
            out.add(Decimal(str(r[2])))
        except (InvalidOperation, ValueError, IndexError):
            continue
    return out


def _validar_filas(filas: list[tuple[str, Decimal, bool]]) -> None:
    if not filas:
        raise ValueError("Debe existir al menos una presentación (UMB).")
    umb = [f for f in filas if f[2]]
    if len(umb) != 1:
        raise ValueError("Debe haber exactamente una presentación marcada como UMB (factor base).")
    for nombre, fac, _ in filas:
        if not (nombre or "").strip():
            raise ValueError("Cada presentación debe tener nombre.")
        if fac <= 0:
            raise ValueError("Los factores deben ser mayores a cero.")


def reemplazar_todas(
    cur,
    producto_id: int,
    filas: list[tuple[str, Decimal, bool]],
) -> None:
    """
    filas: (nombre, factor_umb, es_umb). Una sola fila con es_umb=True (típicamente factor 1).
    """
    if not tabla_existe(cur):
        return
    _validar_filas(filas)
    cur.execute("DELETE FROM producto_presentacion WHERE producto_id = %s", (producto_id,))
    for i, (nombre, fac, es_u) in enumerate(filas):
        cur.execute(
            """
            INSERT INTO producto_presentacion (producto_id, nombre, factor_umb, es_umb, orden)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (producto_id, nombre.strip()[:80], fac, es_u, i),
        )


def _factor_normalizado(val) -> Decimal:
    try:
        return Decimal(str(val)).normalize()
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def lista_para_pos_json(
    cur,
    producto_id: int,
    unidades_por_docena: int,
    unidades_por_caja: int | None,
    nombre_producto: str | None = None,
) -> list[dict[str, Any]]:
    """
    Lista para el POS: id (o null si sintético), nombre, factor, es_umb.

    Si hay filas en BD pero solo la UMB (p. ej. migración parcial), se completan
    Docena y Caja desde unidades_por_docena / unidades_por_caja como cuando no hay tabla.
    El nombre UMB para docena/caja sale del nombre guardado en la fila es_umb (ej. Sobre, Libra).

    Si faltan unidades por caja en BD pero el nombre del producto incluye «60 SOBRES», se infiere
    el factor de caja para el desplegable del POS (no modifica la base de datos).
    """
    rows = listar_por_producto(cur, producto_id)
    umb_nombre = "Unidad base"
    if rows:
        for r in rows:
            if len(r) > 3 and r[3]:
                umb_nombre = str(r[1] or "").strip() or umb_nombre
                break
        if umb_nombre == "Unidad base":
            for r in rows:
                try:
                    if _factor_normalizado(r[2]) == Decimal("1"):
                        umb_nombre = str(r[1] or "").strip() or umb_nombre
                        break
                except (IndexError, TypeError):
                    pass

    umb_nombre = _inferir_etiqueta_umb_desde_nombre(nombre_producto, umb_nombre)

    uxcaja_eff: int | None
    if unidades_por_caja is not None and int(unidades_por_caja) > 0:
        uxcaja_eff = int(unidades_por_caja)
    else:
        uxcaja_eff = _inferir_caja_desde_nombre(nombre_producto)

    uxdoc_eff = int(unidades_por_docena or 12)
    if uxdoc_eff < 2:
        uxdoc_eff = 12

    filas_legacy = construir_filas_desde_legacy(
        umb_nombre,
        uxdoc_eff,
        uxcaja_eff,
        extras=None,
    )

    if not rows:
        return [
            {"id": None, "nombre": n, "factor": float(f), "es_umb": es}
            for n, f, es in filas_legacy
        ]

    out: list[dict[str, Any]] = [
        {"id": int(r[0]), "nombre": str(r[1] or "").strip(), "factor": float(r[2]), "es_umb": bool(r[3])}
        for r in rows
    ]
    factores_db = {_factor_normalizado(r[2]) for r in rows}
    for n, f, es in filas_legacy:
        k = _factor_normalizado(f)
        if k <= 0 or k in factores_db:
            continue
        factores_db.add(k)
        out.append({"id": None, "nombre": n, "factor": float(f), "es_umb": es})

    for d in out:
        if d.get("es_umb") and (d.get("nombre") or "").strip().lower() in ("unidad base", "umb", ""):
            d["nombre"] = _inferir_etiqueta_umb_desde_nombre(nombre_producto, str(d.get("nombre") or ""))
    return out


def construir_filas_desde_legacy(
    nombre_umb: str,
    unidades_por_docena: int,
    unidades_por_caja: int | None,
    extras: list[tuple[str, float]] | None = None,
) -> list[tuple[str, Decimal, bool]]:
    """UMB + Docena + Caja (si aplica) + filas extra (nombre, factor)."""
    umb = (nombre_umb or "Unidad base").strip()[:80] or "Unidad base"
    rows: list[tuple[str, Decimal, bool]] = [(umb, Decimal("1"), True)]
    upd = int(unidades_por_docena or 12)
    if upd < 2:
        upd = 12
    if upd > 1:
        rows.append(("Docena", Decimal(upd), False))
    if unidades_por_caja is not None and int(unidades_por_caja) > 0:
        rows.append(("Caja", Decimal(int(unidades_por_caja)), False))
    if extras:
        for nom, fac in extras:
            n = (nom or "").strip()[:80]
            if not n:
                continue
            try:
                f = Decimal(str(fac))
            except (InvalidOperation, ValueError):
                continue
            if f <= 0:
                continue
            rows.append((n, f, False))
    return rows
