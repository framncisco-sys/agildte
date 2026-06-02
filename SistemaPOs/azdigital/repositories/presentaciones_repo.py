# Programador: Oscar Amaya Romero
"""Presentaciones de venta: factores respecto a la UMB (unidad de medida base) del producto."""

from __future__ import annotations

import re
import uuid
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


def asegurar_tabla_presentacion(cur) -> bool:
    """
    Crea producto_presentacion (y columnas de regla/código) si faltan en BD antigua.
    Sin esta tabla, guardar_producto guarda el ítem pero omite «Otras formas de vender».
    """
    if tabla_existe(cur):
        asegurar_columnas_regla_precio(cur)
        _asegurar_columna_codigo_barra(cur)
        return True
    sp = "spppt" + uuid.uuid4().hex[:10]
    cur.execute(f"SAVEPOINT {sp}")
    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS producto_presentacion (
                id SERIAL PRIMARY KEY,
                producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                nombre VARCHAR(80) NOT NULL,
                factor_umb NUMERIC(18,6) NOT NULL CHECK (factor_umb > 0),
                es_umb BOOLEAN NOT NULL DEFAULT FALSE,
                orden SMALLINT DEFAULT 0,
                codigo_barra VARCHAR(64) NULL,
                cantidad_desde NUMERIC(18,6) NULL,
                cantidad_hasta NUMERIC(18,6) NULL,
                precio_regla NUMERIC(18,6) NULL
            )
            """
        )
        cur.execute("DROP INDEX IF EXISTS uq_producto_presentacion_umb")
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_producto_presentacion_umb
            ON producto_presentacion (producto_id)
            WHERE es_umb
            """
        )
        asegurar_columnas_regla_precio(cur)
        _asegurar_columna_codigo_barra(cur)
        cur.execute(f"RELEASE SAVEPOINT {sp}")
        return tabla_existe(cur)
    except Exception:
        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        return False


def _asegurar_columna_codigo_barra(cur) -> None:
    if not tabla_existe(cur) or tiene_columna_codigo_barra(cur):
        return
    cur.execute(
        """
        ALTER TABLE producto_presentacion
        ADD COLUMN IF NOT EXISTS codigo_barra VARCHAR(64) NULL
        """
    )


def tiene_columna_codigo_barra(cur) -> bool:
    """True si existe ``producto_presentacion.codigo_barra`` (migración códigos por presentación)."""
    if not tabla_existe(cur):
        return False
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'producto_presentacion'
          AND column_name = 'codigo_barra'
        LIMIT 1
        """,
    )
    return cur.fetchone() is not None


def _tiene_columna(cur, nombre_columna: str) -> bool:
    if not tabla_existe(cur):
        return False
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'producto_presentacion'
          AND column_name = %s
        LIMIT 1
        """,
        (nombre_columna,),
    )
    return cur.fetchone() is not None


def tiene_columnas_regla_precio(cur) -> bool:
    """True cuando existen columnas de rango/precio por presentación."""
    return (
        _tiene_columna(cur, "cantidad_desde")
        and _tiene_columna(cur, "cantidad_hasta")
        and _tiene_columna(cur, "precio_regla")
    )


def asegurar_columnas_regla_precio(cur) -> None:
    """Agrega columnas de regla de precio por rango si faltan."""
    if not tabla_existe(cur):
        return
    cur.execute(
        """
        ALTER TABLE producto_presentacion
        ADD COLUMN IF NOT EXISTS cantidad_desde NUMERIC(18,6) NULL,
        ADD COLUMN IF NOT EXISTS cantidad_hasta NUMERIC(18,6) NULL,
        ADD COLUMN IF NOT EXISTS precio_regla NUMERIC(18,6) NULL
        """
    )


def listar_por_producto(cur, producto_id: int) -> list[tuple[Any, ...]]:
    """
    Filas base: id, nombre, factor_umb, es_umb, orden.
    Opcionales en orden: codigo_barra, cantidad_desde, cantidad_hasta, precio_regla.
    """
    if not tabla_existe(cur):
        return []
    cols = "id, nombre, factor_umb, es_umb, orden"
    if tiene_columna_codigo_barra(cur):
        cols += ", codigo_barra"
    if tiene_columnas_regla_precio(cur):
        cols += ", cantidad_desde, cantidad_hasta, precio_regla"
    cur.execute(
        f"""
        SELECT {cols}
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


def _validar_filas(filas: list[tuple[Any, ...]]) -> None:
    if not filas:
        raise ValueError("Debe existir al menos una presentación (UMB).")
    umb = [f for f in filas if f[2]]
    if len(umb) != 1:
        raise ValueError("Debe haber exactamente una presentación marcada como UMB (factor base).")
    for f in filas:
        nombre, fac = f[0], f[1]
        if not (nombre or "").strip():
            raise ValueError("Cada presentación debe tener nombre.")
        if fac <= 0:
            raise ValueError("Los factores deben ser mayores a cero.")


def _fila_con_codigo_opcional(
    nombre: str,
    fac: Decimal,
    es_umb: bool,
    codigo_barra: str | None = None,
    cantidad_desde: Decimal | None = None,
    cantidad_hasta: Decimal | None = None,
    precio_regla: Decimal | None = None,
) -> tuple[Any, ...]:
    """Tupla: nombre, factor, es_umb, codigo, cantidad_desde, cantidad_hasta, precio_regla."""
    n = (nombre or "").strip()[:80]
    c = (codigo_barra or "").strip()[:64] if codigo_barra else ""
    return (n, fac, es_umb, (c or None), cantidad_desde, cantidad_hasta, precio_regla)


def _codigo_desde_fila(fila: tuple[Any, ...]) -> str | None:
    if len(fila) <= 3 or fila[3] is None:
        return None
    s = str(fila[3]).strip()[:64]
    return s or None


def _decimal_desde_fila(fila: tuple[Any, ...], idx: int) -> Decimal | None:
    if len(fila) <= idx or fila[idx] is None or str(fila[idx]).strip() == "":
        return None
    try:
        return Decimal(str(fila[idx]))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _hasta_para_json(val: Decimal | float | None) -> float | None:
    """Vacío o ≤ 0 en BD = sin tope superior (no se envía al POS)."""
    if val is None:
        return None
    try:
        n = float(val)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _pos_dict_desde_fila_interna(fila: tuple[Any, ...], id_val: int | None = None) -> dict[str, Any]:
    """Convierte tupla interna (nombre, factor, es_umb, …) al JSON del POS."""
    d: dict[str, Any] = {
        "id": id_val,
        "nombre": str(fila[0] or "").strip(),
        "factor": float(fila[1]),
        "es_umb": bool(fila[2]),
    }
    cb = _codigo_desde_fila(fila)
    if cb:
        d["codigo_barra"] = cb
    cdes = _decimal_desde_fila(fila, 4)
    chas = _decimal_desde_fila(fila, 5)
    preg = _decimal_desde_fila(fila, 6)
    if cdes is not None:
        d["cantidad_desde"] = float(cdes)
    chas_j = _hasta_para_json(chas)
    if chas_j is not None:
        d["cantidad_hasta"] = chas_j
    if preg is not None:
        d["precio_regla"] = float(preg)
    return d


def _pos_dict_desde_fila_bd(r: tuple[Any, ...]) -> dict[str, Any]:
    """Convierte fila de ``listar_por_producto`` al JSON del POS."""
    d: dict[str, Any] = {
        "id": int(r[0]),
        "nombre": str(r[1] or "").strip(),
        "factor": float(r[2]),
        "es_umb": bool(r[3]),
    }
    rem = list(r[5:]) if len(r) > 5 else []
    if len(rem) == 1:
        cb = rem[0]
        if cb is not None and str(cb).strip():
            d["codigo_barra"] = str(cb).strip()
    elif len(rem) == 3:
        d["cantidad_desde"] = float(rem[0]) if rem[0] is not None else None
        chas_j = _hasta_para_json(rem[1])
        if chas_j is not None:
            d["cantidad_hasta"] = chas_j
        d["precio_regla"] = float(rem[2]) if rem[2] is not None else None
    elif len(rem) >= 4:
        cb = rem[0]
        if cb is not None and str(cb).strip():
            d["codigo_barra"] = str(cb).strip()
        d["cantidad_desde"] = float(rem[1]) if rem[1] is not None else None
        chas_j = _hasta_para_json(rem[2])
        if chas_j is not None:
            d["cantidad_hasta"] = chas_j
        d["precio_regla"] = float(rem[3]) if rem[3] is not None else None
    return d


def _snapshot_codigos_presentacion(cur, producto_id: int) -> dict[tuple[Decimal, str], str]:
    """Antes de reemplazar filas: mapa (factor normalizado, nombre lower) -> código."""
    if not tabla_existe(cur) or not tiene_columna_codigo_barra(cur):
        return {}
    cur.execute(
        """
        SELECT nombre, factor_umb, codigo_barra
        FROM producto_presentacion
        WHERE producto_id = %s
        """,
        (producto_id,),
    )
    out: dict[tuple[Decimal, str], str] = {}
    for r in cur.fetchall() or []:
        if not r or len(r) < 3:
            continue
        cb = r[2] if len(r) > 2 else None
        if not cb or not str(cb).strip():
            continue
        try:
            fac = _factor_normalizado(r[1])
        except Exception:
            continue
        key = (fac, str(r[0] or "").strip().lower())
        out[key] = str(cb).strip()[:64]
    return out


def reemplazar_todas(
    cur,
    producto_id: int,
    filas: list[tuple[Any, ...]],
) -> None:
    """
    filas: (nombre, factor_umb, es_umb) o (nombre, factor_umb, es_umb, codigo_barra).
    Si existe columna codigo_barra, conserva códigos de la BD por (factor, nombre) al
    reordenar o guardar desde inventario.
    """
    if not tabla_existe(cur):
        return
    preservar = _snapshot_codigos_presentacion(cur, producto_id)
    _validar_filas(filas)
    cur.execute("DELETE FROM producto_presentacion WHERE producto_id = %s", (producto_id,))
    use_cb = tiene_columna_codigo_barra(cur)
    use_regla = tiene_columnas_regla_precio(cur)
    for i, fila in enumerate(filas):
        nombre, fac, es_u = fila[0], fila[1], fila[2]
        cb = _codigo_desde_fila(fila)
        cant_desde = _decimal_desde_fila(fila, 4)
        cant_hasta = _decimal_desde_fila(fila, 5)
        precio_regla = _decimal_desde_fila(fila, 6)
        if cb is None and preservar:
            k = (_factor_normalizado(fac), str(nombre or "").strip().lower())
            cb = preservar.get(k)
        if use_cb and use_regla:
            cur.execute(
                """
                INSERT INTO producto_presentacion (
                    producto_id, nombre, factor_umb, es_umb, orden, codigo_barra,
                    cantidad_desde, cantidad_hasta, precio_regla
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (producto_id, str(nombre).strip()[:80], fac, es_u, i, cb, cant_desde, cant_hasta, precio_regla),
            )
        elif use_cb:
            cur.execute(
                """
                INSERT INTO producto_presentacion (producto_id, nombre, factor_umb, es_umb, orden, codigo_barra)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (producto_id, str(nombre).strip()[:80], fac, es_u, i, cb),
            )
        elif use_regla:
            cur.execute(
                """
                INSERT INTO producto_presentacion (
                    producto_id, nombre, factor_umb, es_umb, orden, cantidad_desde, cantidad_hasta, precio_regla
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (producto_id, str(nombre).strip()[:80], fac, es_u, i, cant_desde, cant_hasta, precio_regla),
            )
        else:
            cur.execute(
                """
                INSERT INTO producto_presentacion (producto_id, nombre, factor_umb, es_umb, orden)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (producto_id, str(nombre).strip()[:80], fac, es_u, i),
            )


def _factor_normalizado(val) -> Decimal:
    try:
        return Decimal(str(val)).normalize()
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def listar_por_productos(cur, producto_ids: list[int]) -> dict[int, list[tuple[Any, ...]]]:
    """Presentaciones agrupadas por producto_id (consulta única)."""
    if not producto_ids or not tabla_existe(cur):
        return {}
    cols = "id, nombre, factor_umb, es_umb, orden"
    if tiene_columna_codigo_barra(cur):
        cols += ", codigo_barra"
    if tiene_columnas_regla_precio(cur):
        cols += ", cantidad_desde, cantidad_hasta, precio_regla"
    try:
        cur.execute(
            f"""
            SELECT producto_id, {cols}
            FROM producto_presentacion
            WHERE producto_id = ANY(%s)
            ORDER BY producto_id, orden NULLS LAST, id
            """,
            (producto_ids,),
        )
        out: dict[int, list[tuple[Any, ...]]] = {}
        for row in cur.fetchall() or []:
            pid = int(row[0])
            out.setdefault(pid, []).append(tuple(row[1:]))
        return out
    except Exception:
        cur.connection.rollback()
        return {}


def _lista_para_pos_json_desde_filas(
    rows: list[tuple[Any, ...]],
    unidades_por_docena: int,
    unidades_por_caja: int | None,
    nombre_producto: str | None = None,
) -> list[dict[str, Any]]:
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
        return [_pos_dict_desde_fila_interna(fila, id_val=None) for fila in filas_legacy]

    out: list[dict[str, Any]] = [_pos_dict_desde_fila_bd(r) for r in rows]
    factores_db = {_factor_normalizado(r[2]) for r in rows}
    for fila in filas_legacy:
        k = _factor_normalizado(fila[1])
        if k <= 0 or k in factores_db:
            continue
        factores_db.add(k)
        out.append(_pos_dict_desde_fila_interna(fila, id_val=None))

    for d in out:
        if d.get("es_umb") and (d.get("nombre") or "").strip().lower() in ("unidad base", "umb", ""):
            d["nombre"] = _inferir_etiqueta_umb_desde_nombre(nombre_producto, str(d.get("nombre") or ""))
    return out


def map_listas_para_pos_json(
    cur,
    items: list[tuple[int, int, int | None, str | None]],
) -> dict[int, list[dict[str, Any]]]:
    """Presentaciones POS para muchos productos (2 consultas máx.: tabla + filas)."""
    if not items:
        return {}
    ids = [int(x[0]) for x in items]
    rows_map = listar_por_productos(cur, ids)
    return {
        int(pid): _lista_para_pos_json_desde_filas(
            rows_map.get(int(pid), []),
            int(uxdoc or 12),
            uxcaja,
            nom,
        )
        for pid, uxdoc, uxcaja, nom in items
    }


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
    return _lista_para_pos_json_desde_filas(rows, unidades_por_docena, unidades_por_caja, nombre_producto)


def construir_filas_desde_legacy(
    nombre_umb: str,
    unidades_por_docena: int,
    unidades_por_caja: int | None,
    extras: list[
        tuple[str, float]
        | tuple[str, float, str | None]
        | tuple[str, float, str | None, float | None, float | None, float | None]
    ] | None = None,
    *,
    codigo_barra_umb: str | None = None,
    codigo_barra_docena: str | None = None,
    codigo_barra_caja: str | None = None,
) -> list[tuple[Any, ...]]:
    """UMB + Docena + Caja (si aplica) + filas extra (nombre, factor [, codigo_barra])."""
    umb = (nombre_umb or "Unidad base").strip()[:80] or "Unidad base"
    rows: list[tuple[Any, ...]] = [_fila_con_codigo_opcional(umb, Decimal("1"), True, codigo_barra_umb)]
    upd = int(unidades_por_docena or 12)
    if upd < 2:
        upd = 12
    if upd > 1:
        rows.append(_fila_con_codigo_opcional("Docena", Decimal(upd), False, codigo_barra_docena))
    if unidades_por_caja is not None and int(unidades_por_caja) > 0:
        rows.append(
            _fila_con_codigo_opcional("Caja", Decimal(int(unidades_por_caja)), False, codigo_barra_caja)
        )
    if extras:
        for x in extras:
            if len(x) >= 6:
                nom, fac, cb, cdes, chas, preg = x[0], x[1], x[2], x[3], x[4], x[5]
            elif len(x) >= 3:
                nom, fac, cb, cdes, chas, preg = x[0], x[1], x[2], None, None, None
            else:
                nom, fac, cb, cdes, chas, preg = x[0], x[1], None, None, None, None
            n = (str(nom) or "").strip()[:80]
            if not n:
                continue
            try:
                f = Decimal(str(fac))
            except (InvalidOperation, ValueError):
                continue
            if f <= 0:
                continue
            cdes_d: Decimal | None = None
            chas_d: Decimal | None = None
            preg_d: Decimal | None = None
            try:
                if cdes is not None and str(cdes).strip() != "":
                    cdes_d = Decimal(str(cdes))
                if chas is not None and str(chas).strip() != "":
                    chas_d = Decimal(str(chas))
                if preg is not None and str(preg).strip() != "":
                    preg_d = Decimal(str(preg))
            except (InvalidOperation, ValueError):
                cdes_d = None
                chas_d = None
                preg_d = None
            if cdes_d is not None and cdes_d < 0:
                cdes_d = None
            if chas_d is not None and chas_d <= 0:
                chas_d = None
            if cdes_d is not None and chas_d is not None and chas_d < cdes_d:
                chas_d = None
            if preg_d is not None and preg_d < 0:
                preg_d = None
            rows.append(
                _fila_con_codigo_opcional(
                    n,
                    f,
                    False,
                    str(cb) if cb is not None else None,
                    cdes_d,
                    chas_d,
                    preg_d,
                )
            )
    return rows
