# Programador: Oscar Amaya Romero
from __future__ import annotations

from typing import Any


def _mh_codigo_producto(codigo: str | None) -> str:
    from azdigital.utils.mh_cat003_unidades import normalizar_codigo_mh

    return normalizar_codigo_mh(codigo)


def _productos_tiene_columna(cur, nombre_columna: str) -> bool:
    """True si la tabla productos tiene la columna (BD sin migración POS/MH)."""
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'productos'
        AND column_name = %s
        LIMIT 1
        """,
        (nombre_columna.lower(),),
    )
    return cur.fetchone() is not None


def asegurar_columnas_baja(cur) -> bool:
    """Crea columnas activo/motivo_baja si faltan (migración en caliente)."""
    if _productos_tiene_columna(cur, "activo"):
        return True
    try:
        cur.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE")
        cur.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS motivo_baja TEXT")
        cur.execute("ALTER TABLE productos ADD COLUMN IF NOT EXISTS fecha_baja TIMESTAMP")
        cur.execute(
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS usuario_baja_id "
            "INTEGER REFERENCES usuarios(id) ON DELETE SET NULL"
        )
        cur.execute(
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS usuario_baja_username VARCHAR(100)"
        )
        cur.connection.commit()
        return _productos_tiene_columna(cur, "activo")
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return False


def _filtro_activos_sql(cur, alias: str | None = "p", *, solo_activos: bool = True) -> str:
    """Fragmento AND para inventario/POS (activos) o reporte de bajas (inactivos)."""
    if not _productos_tiene_columna(cur, "activo"):
        return ""
    col = f"{alias}.activo" if alias else "activo"
    if solo_activos:
        return f" AND COALESCE({col}, TRUE) = TRUE"
    return f" AND COALESCE({col}, TRUE) = FALSE"


def _sql_existencia_pos(alias: str = "p", sucursal_id_usuario: int | None = None) -> tuple[str, list[Any]]:
    """
    Stock vendible en POS. Si hay ``producto_stock_sucursal`` pero ninguna fila para la sucursal
    de sesión, usa ``stock_actual`` (misma cifra que muestra Inventario).
    """
    a = alias
    suc = sucursal_id_usuario
    if suc is not None:
        frag = (
            f"CASE "
            f"WHEN EXISTS (SELECT 1 FROM producto_stock_sucursal x WHERE x.producto_id = {a}.id) "
            f"THEN ("
            f"  CASE "
            f"  WHEN EXISTS ("
            f"    SELECT 1 FROM producto_stock_sucursal z "
            f"    WHERE z.producto_id = {a}.id AND z.sucursal_id = %s"
            f"  ) "
            f"  THEN ("
            f"    SELECT COALESCE(SUM(y.cantidad), 0) FROM producto_stock_sucursal y "
            f"    WHERE y.producto_id = {a}.id AND y.sucursal_id = %s"
            f"  ) "
            f"  ELSE COALESCE({a}.stock_actual, 0) "
            f"  END"
            f") "
            f"ELSE COALESCE({a}.stock_actual, 0) END"
        )
        return frag, [suc, suc]
    frag = (
        f"CASE "
        f"WHEN EXISTS (SELECT 1 FROM producto_stock_sucursal x WHERE x.producto_id = {a}.id) "
        f"THEN ("
        f"  SELECT COALESCE(SUM(y.cantidad), 0) FROM producto_stock_sucursal y "
        f"  WHERE y.producto_id = {a}.id"
        f") "
        f"ELSE COALESCE({a}.stock_actual, 0) END"
    )
    return frag, []


def _buscar_via_presentacion_codigo_barra(
    cur, codigo: str, empresa_id: int | None, sucursal_id_usuario: int | None
) -> tuple[Any, ...] | None:
    """
    Mismo SELECT que ``buscar_por_codigo`` en producto, pero resolviendo el código en
    ``producto_presentacion.codigo_barra`` (six-pack, docena, etc.).
    Añade al final ``presentacion_match_id`` (índice 11) para el POS.
    """
    from azdigital.repositories import presentaciones_repo

    if not presentaciones_repo.tabla_existe(cur) or not presentaciones_repo.tiene_columna_codigo_barra(cur):
        return None
    c = (codigo or "").strip()
    if not c:
        return None
    suc = sucursal_id_usuario
    ex_sql, ex_params = _sql_existencia_pos("p", suc)
    q = (
        "SELECT p.id, p.nombre, p.precio_unitario, p.codigo_barra, COALESCE(p.promocion_tipo, ''), COALESCE(p.promocion_valor, 0), "
        "COALESCE(p.fraccionable, FALSE), p.unidades_por_caja, COALESCE(p.unidades_por_docena, 12), "
        "COALESCE(NULLIF(TRIM(p.mh_codigo_unidad), ''), '59'), "
        f"{ex_sql} AS existencia, "
        "pp.id AS presentacion_match_id "
        "FROM productos p "
        "INNER JOIN producto_presentacion pp ON pp.producto_id = p.id "
        "AND pp.codigo_barra IS NOT NULL AND length(trim(pp.codigo_barra)) > 0 "
        "AND TRIM(pp.codigo_barra) = %s"
    )
    params: list[Any] = list(ex_params) + [c]
    if empresa_id:
        fe, pe = _alcance_empresa_inventario(empresa_id)
        q += fe
        params.extend(pe)
    if sucursal_id_usuario is not None:
        q += " AND (p.sucursal_id IS NULL OR p.sucursal_id = %s)"
        params.append(sucursal_id_usuario)
    q += _filtro_activos_sql(cur, "p", solo_activos=True)
    q += " LIMIT 1"
    cur.execute(q, tuple(params))
    return cur.fetchone()


def buscar_por_codigo(cur, codigo: str, empresa_id: int = None, sucursal_id_usuario: int | None = None):
    suc = sucursal_id_usuario
    ex_sql, ex_params = _sql_existencia_pos("p", suc)
    q = (
        "SELECT p.id, p.nombre, p.precio_unitario, p.codigo_barra, COALESCE(p.promocion_tipo, ''), COALESCE(p.promocion_valor, 0), "
        "COALESCE(p.fraccionable, FALSE), p.unidades_por_caja, COALESCE(p.unidades_por_docena, 12), "
        "COALESCE(NULLIF(TRIM(p.mh_codigo_unidad), ''), '59'), "
        f"{ex_sql} AS existencia "
        "FROM productos p WHERE TRIM(p.codigo_barra) = %s"
    )
    params: list[Any] = list(ex_params) + [codigo.strip()]
    if empresa_id:
        fe, pe = _alcance_empresa_inventario(empresa_id)
        q += fe
        params.extend(pe)
    if sucursal_id_usuario is not None:
        q += " AND (p.sucursal_id IS NULL OR p.sucursal_id = %s)"
        params.append(sucursal_id_usuario)
    q += _filtro_activos_sql(cur, "p", solo_activos=True)
    try:
        cur.execute(q, tuple(params))
        r = cur.fetchone()
        if r is not None:
            return r
        r2 = _buscar_via_presentacion_codigo_barra(cur, codigo.strip(), empresa_id, sucursal_id_usuario)
        if r2 is not None:
            return r2
    except Exception:
        cur.connection.rollback()
        q0 = (
            "SELECT id, nombre, precio_unitario, codigo_barra, COALESCE(promocion_tipo, ''), COALESCE(promocion_valor, 0), "
            "COALESCE(stock_actual, 0) FROM productos WHERE TRIM(codigo_barra) = %s"
        )
        params0: list[Any] = [codigo.strip()]
        if empresa_id:
            q0 += " AND (empresa_id IS NULL OR empresa_id = %s)"
            params0.append(empresa_id)
        if sucursal_id_usuario is not None:
            q0 += " AND (sucursal_id IS NULL OR sucursal_id = %s)"
            params0.append(sucursal_id_usuario)
        cur.execute(q0, tuple(params0))
        r = cur.fetchone()
        if not r:
            return None
        return (
            r[0],
            r[1],
            r[2],
            r[3],
            r[4],
            r[5],
            False,
            None,
            12,
            "59",
            float(r[6]) if len(r) > 6 and r[6] is not None else 0.0,
        )


def buscar_por_nombre(cur, q: str, limit: int = 10, empresa_id: int = None, sucursal_id_usuario: int | None = None):
    suc = sucursal_id_usuario
    ex_sql, ex_params = _sql_existencia_pos("p", suc)
    sql = (
        "SELECT p.id, p.nombre, p.precio_unitario, p.codigo_barra, COALESCE(p.promocion_tipo, ''), COALESCE(p.promocion_valor, 0), "
        "COALESCE(p.fraccionable, FALSE), p.unidades_por_caja, COALESCE(p.unidades_por_docena, 12), "
        "COALESCE(NULLIF(TRIM(p.mh_codigo_unidad), ''), '59'), "
        f"{ex_sql} AS existencia "
        "FROM productos p WHERE UPPER(p.nombre) LIKE %s"
    )
    params: list[Any] = list(ex_params) + [f"%{q.upper()}%"]
    if empresa_id:
        fe, pe = _alcance_empresa_inventario(empresa_id)
        sql += fe
        params.extend(pe)
    if sucursal_id_usuario is not None:
        sql += " AND (p.sucursal_id IS NULL OR p.sucursal_id = %s)"
        params.append(sucursal_id_usuario)
    sql += _filtro_activos_sql(cur, "p", solo_activos=True)
    sql += " LIMIT %s"
    params.append(limit)
    try:
        cur.execute(sql, tuple(params))
        return cur.fetchall()
    except Exception:
        cur.connection.rollback()
        sql0 = (
            "SELECT id, nombre, precio_unitario, codigo_barra, COALESCE(promocion_tipo, ''), COALESCE(promocion_valor, 0), "
            "COALESCE(stock_actual, 0) FROM productos WHERE UPPER(nombre) LIKE %s"
        )
        p0: list[Any] = [f"%{q.upper()}%"]
        if empresa_id:
            sql0 += " AND (empresa_id IS NULL OR empresa_id = %s)"
            p0.append(empresa_id)
        if sucursal_id_usuario is not None:
            sql0 += " AND (sucursal_id IS NULL OR sucursal_id = %s)"
            p0.append(sucursal_id_usuario)
        sql0 += " LIMIT %s"
        p0.append(limit)
        cur.execute(sql0, tuple(p0))
        rows = cur.fetchall() or []
        out = []
        for r in rows:
            ex = float(r[6]) if len(r) > 6 and r[6] is not None else 0.0
            base = list(r[:6])
            out.append(tuple(base + [False, None, 12, "59", ex]))
        return out


def listar_catalogo_pos_modal(
    cur,
    empresa_id: int,
    sucursal_id_usuario: int | None = None,
    limit: int = 50000,
) -> list[tuple]:
    """
    Lista para modal POS: mismas columnas base que buscar_por_nombre + existencia (UMB / stock).
    Tupla: id, nombre, precio, codigo, promo_t, promo_v, fracc, uxcaja, uxdoc, mh, existencia.
    """
    params: list[Any] = []
    filtro_suc_prod = ""
    if sucursal_id_usuario is not None:
        filtro_suc_prod = " AND (p.sucursal_id IS NULL OR p.sucursal_id = %s)"
        params.append(sucursal_id_usuario)
    ex_sql, ex_params = _sql_existencia_pos("p", sucursal_id_usuario)
    sql_exist = f"""
        SELECT p.id, p.nombre, p.precio_unitario, p.codigo_barra,
            COALESCE(p.promocion_tipo, ''), COALESCE(p.promocion_valor, 0),
            COALESCE(p.fraccionable, FALSE), p.unidades_por_caja, COALESCE(p.unidades_por_docena, 12),
            COALESCE(NULLIF(TRIM(p.mh_codigo_unidad), ''), '59'),
            {ex_sql} AS existencia
        FROM productos p
        WHERE (p.empresa_id IS NULL OR p.empresa_id = %s)
    """ + filtro_suc_prod + _filtro_activos_sql(cur, "p", solo_activos=True) + """
        ORDER BY UPPER(p.nombre)
        LIMIT %s
    """
    params_exist = list(ex_params) + [empresa_id] + params + [limit]
    try:
        cur.execute(sql_exist, tuple(params_exist))
        return list(cur.fetchall() or [])
    except Exception:
        cur.connection.rollback()
    fa = _filtro_activos_sql(cur, "p", solo_activos=True)
    sql_simple = (
        "SELECT p.id, p.nombre, p.precio_unitario, p.codigo_barra, "
        "COALESCE(p.promocion_tipo, ''), COALESCE(p.promocion_valor, 0), "
        "COALESCE(p.fraccionable, FALSE), p.unidades_por_caja, COALESCE(p.unidades_por_docena, 12), "
        "COALESCE(NULLIF(TRIM(p.mh_codigo_unidad), ''), '59'), COALESCE(p.stock_actual, 0) "
        "FROM productos p WHERE (p.empresa_id IS NULL OR p.empresa_id = %s)" + filtro_suc_prod + fa + " ORDER BY UPPER(p.nombre) LIMIT %s"
    )
    try:
        cur.execute(sql_simple, tuple([empresa_id] + params + [limit]))
        return list(cur.fetchall() or [])
    except Exception:
        cur.connection.rollback()
        sql0 = (
            "SELECT p.id, p.nombre, p.precio_unitario, p.codigo_barra, "
            "COALESCE(p.promocion_tipo, ''), COALESCE(p.promocion_valor, 0) "
            "FROM productos p WHERE (p.empresa_id IS NULL OR p.empresa_id = %s)" + filtro_suc_prod + " ORDER BY UPPER(p.nombre) LIMIT %s"
        )
        cur.execute(sql0, tuple([empresa_id] + params + [limit]))
        rows = cur.fetchall() or []
        return [tuple(list(r) + [False, None, 12, "59", 0.0]) for r in rows]


def listar_catalogo_pos_modal_global(
    cur,
    sucursal_id_usuario: int | None = None,
    limit: int = 50000,
) -> list[tuple]:
    """Superusuario POS: catálogo de todas las empresas (como inventario global)."""
    params: list[Any] = []
    filtro_suc_prod = ""
    if sucursal_id_usuario is not None:
        filtro_suc_prod = " AND (p.sucursal_id IS NULL OR p.sucursal_id = %s)"
        params.append(sucursal_id_usuario)
    ex_sql, ex_params = _sql_existencia_pos("p", sucursal_id_usuario)
    sql_exist = f"""
        SELECT p.id, p.nombre, p.precio_unitario, p.codigo_barra,
            COALESCE(p.promocion_tipo, ''), COALESCE(p.promocion_valor, 0),
            COALESCE(p.fraccionable, FALSE), p.unidades_por_caja, COALESCE(p.unidades_por_docena, 12),
            COALESCE(NULLIF(TRIM(p.mh_codigo_unidad), ''), '59'),
            {ex_sql} AS existencia
        FROM productos p
        WHERE 1=1
    """ + filtro_suc_prod + _filtro_activos_sql(cur, "p", solo_activos=True) + """
        ORDER BY UPPER(p.nombre)
        LIMIT %s
    """
    params_exist = list(ex_params) + params + [limit]
    try:
        cur.execute(sql_exist, tuple(params_exist))
        return list(cur.fetchall() or [])
    except Exception:
        cur.connection.rollback()
    fa = _filtro_activos_sql(cur, "p", solo_activos=True)
    sql_simple = (
        "SELECT p.id, p.nombre, p.precio_unitario, p.codigo_barra, "
        "COALESCE(p.promocion_tipo, ''), COALESCE(p.promocion_valor, 0), "
        "COALESCE(p.fraccionable, FALSE), p.unidades_por_caja, COALESCE(p.unidades_por_docena, 12), "
        "COALESCE(NULLIF(TRIM(p.mh_codigo_unidad), ''), '59'), COALESCE(p.stock_actual, 0) "
        "FROM productos p WHERE 1=1" + filtro_suc_prod + fa + " ORDER BY UPPER(p.nombre) LIMIT %s"
    )
    try:
        cur.execute(sql_simple, tuple(params + [limit]))
        return list(cur.fetchall() or [])
    except Exception:
        cur.connection.rollback()
        return []


def _empresa_id_de_producto(cur, producto_id: int, default: int = 1) -> int:
    try:
        cur.execute("SELECT empresa_id FROM productos WHERE id = %s", (int(producto_id),))
        row = cur.fetchone()
        if row and row[0] is not None:
            return int(row[0])
    except Exception:
        pass
    return int(default)


def get_nombre_producto(cur, producto_id: int) -> str | None:
    """Nombre comercial del producto en inventario POS (para descripción en DTE AgilDTE)."""
    try:
        cur.execute(
            "SELECT COALESCE(NULLIF(TRIM(nombre), ''), NULL) FROM productos WHERE id = %s",
            (producto_id,),
        )
        row = cur.fetchone()
        return (row[0] or "").strip() if row and row[0] else None
    except Exception:
        return None


def get_precio_y_stock_for_update(cur, producto_id: int):
    try:
        cur.execute(
            """SELECT precio_unitario, stock_actual,
               COALESCE(NULLIF(TRIM(promocion_tipo), ''), NULL),
               COALESCE(promocion_valor, 0),
               COALESCE(fraccionable, FALSE),
               unidades_por_caja,
               COALESCE(unidades_por_docena, 12),
               COALESCE(NULLIF(TRIM(mh_codigo_unidad), ''), '59')
               FROM productos WHERE id = %s FOR UPDATE""",
            (producto_id,),
        )
        return cur.fetchone()
    except Exception:
        cur.connection.rollback()
        cur.execute(
            """SELECT precio_unitario, stock_actual,
               COALESCE(NULLIF(TRIM(promocion_tipo), ''), NULL),
               COALESCE(promocion_valor, 0)
               FROM productos WHERE id = %s FOR UPDATE""",
            (producto_id,),
        )
        r = cur.fetchone()
        if not r:
            return None
        return (r[0], r[1], r[2], r[3], False, None, 12, "59")


def descontar_stock(cur, producto_id: int, cantidad: float, sucursal_id: int | None = None) -> None:
    from azdigital.repositories import kardex_repo

    if kardex_repo.producto_usa_tabla_sucursal(cur, producto_id):
        if not kardex_repo.descontar_stock_sucursal(cur, producto_id, cantidad, sucursal_id):
            raise ValueError("Stock insuficiente")
        return
    cur.execute(
        "UPDATE productos SET stock_actual = stock_actual - %s WHERE id = %s",
        (cantidad, producto_id),
    )


def incrementar_stock(cur, producto_id: int, cantidad: float) -> None:
    """Devuelve unidades al inventario (p. ej. anular venta). Respeta stock por sucursal si aplica."""
    from azdigital.repositories import kardex_repo

    if kardex_repo.producto_usa_tabla_sucursal(cur, producto_id):
        cur.execute(
            """
            SELECT sucursal_id FROM producto_stock_sucursal
            WHERE producto_id = %s
            ORDER BY sucursal_id
            LIMIT 1 FOR UPDATE
            """,
            (producto_id,),
        )
        r = cur.fetchone()
        if r:
            cur.execute(
                """
                UPDATE producto_stock_sucursal SET cantidad = cantidad + %s
                WHERE producto_id = %s AND sucursal_id = %s
                """,
                (cantidad, producto_id, r[0]),
            )
            kardex_repo.sincronizar_stock_total_producto(cur, producto_id)
            return
    cur.execute(
        "UPDATE productos SET stock_actual = stock_actual + %s WHERE id = %s",
        (cantidad, producto_id),
    )


_ACENTOS_INV = str.maketrans("ÁÉÍÓÚÜÑáéíóúüñ", "AEIOUUNAEIOUUN")


def _sql_orden_inventario(q: str | None) -> str:
    if (q or "").strip():
        return " ORDER BY UPPER(p.nombre), p.id DESC"
    return " ORDER BY p.id DESC"


def _alcance_empresa_inventario(empresa_id: int | None) -> tuple[str, list[Any]]:
    """Mismo criterio que ventas: la empresa de sesión o producto sin empresa asignada."""
    if empresa_id is None:
        return "", []
    return " AND (p.empresa_id IS NULL OR p.empresa_id = %s)", [int(empresa_id)]


def asignar_empresa_si_vacia(cur, producto_id: int, empresa_id: int) -> None:
    """Si el producto se vendió sin empresa, lo ancla a la empresa de la venta (queda en inventario)."""
    if not producto_id or not empresa_id:
        return
    try:
        cur.execute(
            "UPDATE productos SET empresa_id = %s WHERE id = %s AND empresa_id IS NULL",
            (int(empresa_id), int(producto_id)),
        )
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass


def _variantes_termino_inventario(term: str) -> list[str]:
    t = (term or "").strip()
    if not t:
        return []
    out = [t]
    folded = t.translate(_ACENTOS_INV)
    if folded.casefold() != t.casefold():
        out.append(folded)
    return out


def _codigo_compacto_inventario(term: str) -> str:
    return "".join(ch for ch in (term or "") if ch.isalnum())


def _ids_por_presentacion_busqueda(cur, term: str) -> list[int]:
    """IDs de producto cuyo código/nombre de presentación coincide (consulta aparte, no tumba el listado)."""
    t = (term or "").strip()
    if not t:
        return []
    try:
        from azdigital.repositories import presentaciones_repo

        if not presentaciones_repo.tabla_existe(cur):
            return []
        likes = [f"%{v}%" for v in _variantes_termino_inventario(t)]
        compact = _codigo_compacto_inventario(t)
        clauses = ["UPPER(COALESCE(pp.nombre, '')) LIKE UPPER(%s)" for _ in likes]
        params: list[Any] = list(likes)
        if presentaciones_repo.tiene_columna_codigo_barra(cur):
            clauses += ["UPPER(TRIM(COALESCE(pp.codigo_barra, ''))) LIKE UPPER(%s)" for _ in likes]
            params += likes
            if compact:
                clauses.append(
                    "REPLACE(REPLACE(UPPER(TRIM(COALESCE(pp.codigo_barra, ''))), ' ', ''), '-', '') "
                    "LIKE UPPER(%s)"
                )
                params.append(f"%{compact}%")
        cur.execute(
            "SELECT DISTINCT pp.producto_id FROM producto_presentacion pp WHERE " + " OR ".join(clauses),
            tuple(params),
        )
        return [int(r[0]) for r in (cur.fetchall() or []) if r and r[0] is not None]
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return []


def _sql_filtro_busqueda_inventario(cur, q: str | None) -> tuple[str, list[Any]]:
    """Nombre, código (con/sin espacios o guiones) y presentaciones. Sin EXISTS que pueda vaciar el listado."""
    term = (q or "").strip()
    if not term:
        return "", []
    clauses: list[str] = []
    params: list[Any] = []
    for v in _variantes_termino_inventario(term):
        like = f"%{v}%"
        clauses.append("UPPER(COALESCE(p.nombre, '')) LIKE UPPER(%s)")
        params.append(like)
        clauses.append("UPPER(TRIM(COALESCE(p.codigo_barra, ''))) LIKE UPPER(%s)")
        params.append(like)
    compact = _codigo_compacto_inventario(term)
    if compact:
        clauses.append(
            "REPLACE(REPLACE(UPPER(TRIM(COALESCE(p.codigo_barra, ''))), ' ', ''), '-', '') LIKE UPPER(%s)"
        )
        params.append(f"%{compact}%")
    ids = _ids_por_presentacion_busqueda(cur, term)
    if ids:
        placeholders = ",".join(["%s"] * len(ids))
        clauses.append(f"p.id IN ({placeholders})")
        params.extend(ids)
    return " AND (" + " OR ".join(clauses) + ")", params


def contar_inventario(
    cur,
    empresa_id: int | None = None,
    q: str | None = None,
    solo_activos: bool = True,
) -> int:
    """Total del mismo universo que el listado (empresa NULL incluida)."""
    fa = _filtro_activos_sql(cur, "p", solo_activos=True) if solo_activos else ""
    fe, pe = _alcance_empresa_inventario(empresa_id)
    fq, pq = _sql_filtro_busqueda_inventario(cur, q)
    try:
        cur.execute(f"SELECT COUNT(*) FROM productos p WHERE 1=1{fe}{fa}{fq}", tuple([*pe, *pq]))
        return int((cur.fetchone() or [0])[0] or 0)
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        try:
            term = (q or "").strip()
            simple = ""
            extra: list[Any] = []
            if term:
                simple = (
                    " AND (UPPER(COALESCE(p.nombre, '')) LIKE UPPER(%s) "
                    "OR UPPER(TRIM(COALESCE(p.codigo_barra, ''))) LIKE UPPER(%s))"
                )
                extra = [f"%{term}%", f"%{term}%"]
            cur.execute(
                f"SELECT COUNT(*) FROM productos p WHERE 1=1{fe}{simple}",
                tuple([*pe, *extra]),
            )
            return int((cur.fetchone() or [0])[0] or 0)
        except Exception:
            try:
                cur.connection.rollback()
            except Exception:
                pass
            return 0


def listar_inventario(
    cur,
    limit: int = 500,
    empresa_id: int = None,
    q: str | None = None,
    offset: int = 0,
    solo_activos: bool = True,
):
    fa = _filtro_activos_sql(cur, "p", solo_activos=True) if solo_activos else ""
    fe, pe = _alcance_empresa_inventario(empresa_id)
    fq, pq = _sql_filtro_busqueda_inventario(cur, q)
    off = max(0, int(offset or 0))
    lim = max(1, int(limit or 500))
    orden = _sql_orden_inventario(q)
    bind = (*pe, *pq, lim, off)
    rows = []
    try:
        if empresa_id:
            try:
                cur.execute(
                    f"""
                    SELECT p.id, p.codigo_barra, p.nombre, COALESCE(p.precio_unitario, 0), COALESCE(p.stock_actual, 0),
                           p.empresa_id, p.sucursal_id,
                           COALESCE(e.nombre_comercial, e.nombre, '—'), COALESCE(s.nombre, ''),
                           COALESCE(NULLIF(p.costo_unitario, 0), 0),
                           COALESCE(NULLIF(TRIM(p.promocion_tipo), ''), ''), COALESCE(p.promocion_valor, 0),
                           COALESCE(p.fraccionable, FALSE), p.unidades_por_caja, COALESCE(p.unidades_por_docena, 12),
                           COALESCE(NULLIF(TRIM(p.mh_codigo_unidad), ''), '59')
                    FROM productos p
                    LEFT JOIN empresas e ON e.id = p.empresa_id
                    LEFT JOIN sucursales s ON s.id = p.sucursal_id
                    WHERE 1=1{fe}{fa}{fq}
                    {orden}
                    LIMIT %s OFFSET %s
                    """,
                    bind,
                )
            except Exception:
                cur.connection.rollback()
                try:
                    cur.execute(
                        f"""SELECT p.id, p.codigo_barra, p.nombre, COALESCE(p.precio_unitario, 0), COALESCE(p.stock_actual, 0),
                                   p.empresa_id, p.sucursal_id,
                                   COALESCE(e.nombre_comercial, e.nombre, '—'), COALESCE(s.nombre, ''),
                                   COALESCE(NULLIF(p.costo_unitario, 0), 0),
                                   COALESCE(NULLIF(TRIM(p.promocion_tipo), ''), ''), COALESCE(p.promocion_valor, 0)
                            FROM productos p
                            LEFT JOIN empresas e ON e.id = p.empresa_id
                            LEFT JOIN sucursales s ON s.id = p.sucursal_id
                            WHERE 1=1{fe}{fa}{fq}{orden} LIMIT %s OFFSET %s""",
                        bind,
                    )
                except Exception:
                    cur.connection.rollback()
                    fq0, pq0 = _sql_filtro_busqueda_inventario(cur, q)
                    cur.execute(
                        f"SELECT p.id, p.codigo_barra, p.nombre, COALESCE(p.precio_unitario, 0), COALESCE(p.stock_actual, 0), p.empresa_id, p.sucursal_id, '', 0, '', 0 FROM productos p WHERE 1=1{fe}{fq0} ORDER BY p.id DESC LIMIT %s OFFSET %s",
                        (*pe, *pq0, lim, off),
                    )
        else:
            fq0, pq0 = _sql_filtro_busqueda_inventario(cur, q)
            cur.execute(
                f"SELECT p.id, p.codigo_barra, p.nombre, COALESCE(p.precio_unitario, 0), COALESCE(p.stock_actual, 0) FROM productos p WHERE 1=1{fa}{fq0} ORDER BY p.id DESC LIMIT %s OFFSET %s",
                (*pq0, lim, off),
            )
        rows = cur.fetchall()
    except Exception:
        cur.connection.rollback()
        fq0, pq0 = _sql_filtro_busqueda_inventario(cur, q)
        if empresa_id:
            cur.execute(
                f"SELECT p.id, p.codigo_barra, p.nombre, COALESCE(p.precio_unitario, 0), COALESCE(p.stock_actual, 0), p.empresa_id, p.sucursal_id, '', 0, '', 0 FROM productos p WHERE 1=1{fe}{fq0} ORDER BY p.id DESC LIMIT %s OFFSET %s",
                (*pe, *pq0, lim, off),
            )
        else:
            cur.execute(
                f"SELECT p.id, p.codigo_barra, p.nombre, COALESCE(p.precio_unitario, 0), COALESCE(p.stock_actual, 0) FROM productos p WHERE 1=1{fq0} ORDER BY p.id DESC LIMIT %s OFFSET %s",
                (*pq0, lim, off),
            )
        rows = cur.fetchall()
    umb_map = _umb_map_desde_presentaciones(cur, rows)
    return _normalizar_filas_inventario(rows, umb_por_producto=umb_map)


def _umb_map_desde_presentaciones(cur, rows) -> dict[int, str]:
    from azdigital.repositories import presentaciones_repo

    ids = [int(r[0]) for r in rows if r and r[0] is not None]
    return presentaciones_repo.nombres_umb_por_productos(cur, ids)


def listar_inventario_global(
    cur, limit: int = 500, q: str | None = None, offset: int = 0, solo_activos: bool = True
):
    """Superusuario: mismas columnas normalizadas que listar_inventario (incl. texto stock y nombre UMB)."""
    fa = _filtro_activos_sql(cur, "p", solo_activos=True) if solo_activos else ""
    fq, pq = _sql_filtro_busqueda_inventario(cur, q)
    off = max(0, int(offset or 0))
    lim = max(1, int(limit or 500))
    orden = _sql_orden_inventario(q)
    try:
        cur.execute(
            f"""
            SELECT p.id, p.codigo_barra, p.nombre, COALESCE(p.precio_unitario, 0), COALESCE(p.stock_actual, 0),
                   p.empresa_id, p.sucursal_id,
                   COALESCE(e.nombre_comercial, e.nombre, '—'),
                   COALESCE(s.nombre, '—'),
                   COALESCE(NULLIF(p.costo_unitario, 0), 0),
                   COALESCE(NULLIF(TRIM(p.promocion_tipo), ''), ''), COALESCE(p.promocion_valor, 0),
                   COALESCE(p.fraccionable, FALSE), p.unidades_por_caja, COALESCE(p.unidades_por_docena, 12),
                   COALESCE(NULLIF(TRIM(p.mh_codigo_unidad), ''), '59')
            FROM productos p
            LEFT JOIN empresas e ON e.id = p.empresa_id
            LEFT JOIN sucursales s ON s.id = p.sucursal_id
            WHERE 1=1{fa}{fq}
            {orden}
            LIMIT %s OFFSET %s
            """,
            (*pq, lim, off),
        )
        rows = cur.fetchall()
    except Exception:
        cur.connection.rollback()
        try:
            cur.execute(
                f"""
                SELECT p.id, p.codigo_barra, p.nombre, COALESCE(p.precio_unitario, 0), COALESCE(p.stock_actual, 0),
                       p.empresa_id, p.sucursal_id,
                       COALESCE(e.nombre_comercial, e.nombre, '—'),
                       COALESCE(s.nombre, '—'),
                       COALESCE(NULLIF(p.costo_unitario, 0), 0),
                       COALESCE(NULLIF(TRIM(p.promocion_tipo), ''), ''), COALESCE(p.promocion_valor, 0)
                FROM productos p
                LEFT JOIN empresas e ON e.id = p.empresa_id
                LEFT JOIN sucursales s ON s.id = p.sucursal_id
                WHERE 1=1{fq}
                {orden}
                LIMIT %s OFFSET %s
                """,
                (*pq, lim, off),
            )
            rows = cur.fetchall()
        except Exception:
            cur.connection.rollback()
            fq0, pq0 = _sql_filtro_busqueda_inventario(cur, q)
            cur.execute(
                f"""
                SELECT p.id, p.codigo_barra, p.nombre, COALESCE(p.precio_unitario, 0), COALESCE(p.stock_actual, 0),
                       p.empresa_id, p.sucursal_id,
                       COALESCE(e.nombre_comercial, e.nombre, '—'),
                       '—', 0, '', 0
                FROM productos p
                LEFT JOIN empresas e ON e.id = p.empresa_id
                WHERE 1=1{fq0}
                ORDER BY p.id DESC
                LIMIT %s OFFSET %s
                """,
                (*pq0, lim, off),
            )
            rows = cur.fetchall()
    umb_map = _umb_map_desde_presentaciones(cur, rows)
    return _normalizar_filas_inventario(rows, umb_por_producto=umb_map)


def _normalizar_filas_inventario(rows, umb_por_producto: dict[int, str] | None = None):
    """Salida: … mh_codigo (15), texto_stock (16), nombre_umb_corto (17)."""
    from azdigital.utils.stock_display import texto_stock_grupos

    umb = umb_por_producto or {}

    def _etq(rid) -> str | None:
        if rid is None:
            return None
        try:
            return umb.get(int(rid))
        except (TypeError, ValueError):
            return None

    out = []
    for r in rows:
        if len(r) >= 16:
            stock_f = float(r[4]) if r[4] is not None else 0
            upc = int(r[13]) if r[13] is not None else None
            upd = int(r[14]) if r[14] is not None else 12
            mh = _mh_codigo_producto(str(r[15]) if len(r) > 15 else None)
            eq = _etq(r[0])
            txt = texto_stock_grupos(
                stock_f,
                upc if upc and upc > 0 else None,
                upd if upd > 0 else None,
                etiqueta_umb=eq,
                fraccionable=bool(r[12]) if len(r) > 12 else False,
                mh_codigo_unidad=mh,
            )
            out.append(
                (
                    r[0],
                    r[1],
                    r[2],
                    float(r[3]) if r[3] is not None else 0,
                    stock_f,
                    r[5],
                    r[6],
                    str(r[7] or "—"),
                    str(r[8] or ""),
                    float(r[9]) if r[9] is not None else 0,
                    (r[10] or "").strip(),
                    float(r[11]) if r[11] is not None else 0,
                    bool(r[12]),
                    upc,
                    upd,
                    mh,
                    txt,
                    (eq or "").strip(),
                )
            )
        elif 12 <= len(r) < 16:
            stock_f = float(r[4]) if r[4] is not None else 0
            eq = _etq(r[0])
            txt = texto_stock_grupos(stock_f, None, None, etiqueta_umb=eq)
            out.append(
                (
                    r[0],
                    r[1],
                    r[2],
                    float(r[3]) if r[3] is not None else 0,
                    stock_f,
                    r[5],
                    r[6],
                    str(r[7] or "—"),
                    str(r[8] or ""),
                    float(r[9]) if r[9] is not None else 0,
                    (r[10] or "").strip(),
                    float(r[11]) if r[11] is not None else 0,
                    False,
                    None,
                    12,
                    "59",
                    txt,
                    (eq or "").strip(),
                )
            )
        elif len(r) >= 11:
            stock_f = float(r[4]) if r[4] is not None else 0
            eq = _etq(r[0])
            txt = texto_stock_grupos(stock_f, None, None, etiqueta_umb=eq)
            out.append(
                (
                    r[0],
                    r[1],
                    r[2],
                    float(r[3]) if r[3] is not None else 0,
                    stock_f,
                    r[5],
                    r[6],
                    "—",
                    str(r[7] or ""),
                    float(r[8]) if r[8] is not None else 0,
                    (r[9] or "").strip(),
                    float(r[10]) if r[10] is not None else 0,
                    False,
                    None,
                    12,
                    "59",
                    txt,
                    (eq or "").strip(),
                )
            )
        elif len(r) >= 10:
            stock_f = float(r[4]) if r[4] is not None else 0
            pv = float(r[9]) if len(r) > 9 and r[9] is not None else 0
            eq = _etq(r[0])
            txt = texto_stock_grupos(stock_f, None, None, etiqueta_umb=eq)
            out.append(
                (
                    r[0],
                    r[1],
                    r[2],
                    float(r[3]) if r[3] is not None else 0,
                    stock_f,
                    r[5],
                    r[6],
                    "—",
                    str(r[7] or ""),
                    0.0,
                    (r[8] or "").strip() if len(r) > 8 else "",
                    pv,
                    False,
                    None,
                    12,
                    "59",
                    txt,
                    (eq or "").strip(),
                )
            )
        elif len(r) >= 8:
            stock_f = float(r[4]) if r[4] is not None else 0
            eq = _etq(r[0])
            txt = texto_stock_grupos(stock_f, None, None, etiqueta_umb=eq)
            out.append(
                (
                    r[0],
                    r[1],
                    r[2],
                    float(r[3]) if r[3] is not None else 0,
                    stock_f,
                    r[5],
                    r[6],
                    "—",
                    str(r[7] or ""),
                    0.0,
                    "",
                    0.0,
                    False,
                    None,
                    12,
                    "59",
                    txt,
                    (eq or "").strip(),
                )
            )
        elif len(r) >= 5:
            stock_f = float(r[4]) if r[4] is not None else 0
            eq = _etq(r[0])
            txt = texto_stock_grupos(stock_f, None, None, etiqueta_umb=eq)
            out.append(
                (
                    r[0],
                    r[1],
                    r[2],
                    float(r[3]) if r[3] is not None else 0,
                    stock_f,
                    r[5],
                    r[6],
                    "—",
                    "—",
                    0.0,
                    "",
                    0.0,
                    False,
                    None,
                    12,
                    "59",
                    txt,
                    (eq or "").strip(),
                )
            )
        elif len(r) == 4:
            eq = _etq(r[0])
            txt = texto_stock_grupos(0.0, None, None, etiqueta_umb=eq)
            out.append(
                (
                    r[0],
                    r[1],
                    r[2],
                    float(r[3]) if r[3] is not None else 0,
                    0.0,
                    None,
                    None,
                    "—",
                    "—",
                    0.0,
                    "",
                    0.0,
                    False,
                    None,
                    12,
                    "59",
                    txt,
                    (eq or "").strip(),
                )
            )
        else:
            continue
    return out


def get_producto(cur, producto_id: int, empresa_id: int = None):
    if empresa_id:
        try:
            cur.execute(
                """
                SELECT id, codigo_barra, nombre, precio_unitario, COALESCE(stock_actual, 0), empresa_id, sucursal_id
                FROM productos WHERE id = %s AND empresa_id = %s
                """,
                (producto_id, empresa_id),
            )
        except Exception:
            cur.execute(
                "SELECT id, codigo_barra, nombre, precio_unitario, COALESCE(stock_actual, 0) FROM productos WHERE id = %s AND empresa_id = %s",
                (producto_id, empresa_id),
            )
    else:
        try:
            cur.execute(
                """
                SELECT id, codigo_barra, nombre, precio_unitario, COALESCE(stock_actual, 0), empresa_id, sucursal_id
                FROM productos WHERE id = %s
                """,
                (producto_id,),
            )
        except Exception:
            cur.execute(
                "SELECT id, codigo_barra, nombre, precio_unitario, COALESCE(stock_actual, 0) FROM productos WHERE id = %s",
                (producto_id,),
            )
    return cur.fetchone()


def crear_producto(
    cur,
    codigo_barra: str,
    nombre: str,
    precio_unitario: float,
    stock_inicial: float,
    empresa_id: int = 1,
    sucursal_id: int | None = None,
    promocion_tipo: str | None = None,
    promocion_valor: float | None = None,
    costo_unitario: float | None = None,
    *,
    fraccionable: bool = False,
    unidades_por_caja: int | None = None,
    unidades_por_docena: int | None = 12,
    mh_codigo_unidad: str | None = None,
) -> int:
    pt = (promocion_tipo or "").strip().upper() if promocion_tipo else None
    pv = float(promocion_valor) if promocion_valor is not None else None
    if pt and pt not in ("2X1", "PORCENTAJE"):
        pt = None
    costo = float(costo_unitario) if costo_unitario is not None else 0
    mh = _mh_codigo_producto(mh_codigo_unidad)
    upc = None
    if unidades_por_caja is not None:
        try:
            nx = int(unidades_por_caja)
            if nx > 0:
                upc = nx
        except (TypeError, ValueError):
            pass
    upd = 12
    if unidades_por_docena is not None:
        try:
            nd = int(unidades_por_docena)
            if nd > 0:
                upd = nd
        except (TypeError, ValueError):
            pass
    try:
        cur.execute(
            """
            INSERT INTO productos (
                empresa_id, codigo_barra, nombre, precio_unitario, stock_actual, sucursal_id,
                promocion_tipo, promocion_valor, costo_unitario,
                fraccionable, unidades_por_caja, unidades_por_docena, mh_codigo_unidad
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (
                empresa_id, codigo_barra or nombre[:20], nombre, precio_unitario, stock_inicial or 0, sucursal_id,
                pt, pv, costo,
                bool(fraccionable), upc, upd, mh,
            ),
        )
    except Exception:
        cur.connection.rollback()
        try:
            cur.execute(
                """
                INSERT INTO productos (empresa_id, codigo_barra, nombre, precio_unitario, stock_actual, sucursal_id, promocion_tipo, promocion_valor, costo_unitario)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (empresa_id, codigo_barra or nombre[:20], nombre, precio_unitario, stock_inicial or 0, sucursal_id, pt, pv, costo),
            )
        except Exception:
            cur.connection.rollback()
            try:
                cur.execute(
                    """
                    INSERT INTO productos (empresa_id, codigo_barra, nombre, precio_unitario, stock_actual, sucursal_id, promocion_tipo, promocion_valor)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (empresa_id, codigo_barra or nombre[:20], nombre, precio_unitario, stock_inicial or 0, sucursal_id, pt, pv),
                )
            except Exception:
                cur.connection.rollback()
                cur.execute(
                    """
                    INSERT INTO productos (empresa_id, codigo_barra, nombre, precio_unitario, stock_actual, sucursal_id)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (empresa_id, codigo_barra or nombre[:20], nombre, precio_unitario, stock_inicial or 0, sucursal_id),
                )
    return int(cur.fetchone()[0])


def _actualizar_conversion_producto(
    cur,
    producto_id: int,
    fraccionable: bool,
    unidades_por_caja: int | None,
    unidades_por_docena: int,
    mh_codigo_unidad: str,
    empresa_scope: int | None = None,
) -> None:
    mh = _mh_codigo_producto(mh_codigo_unidad)
    upc = None
    if unidades_por_caja is not None:
        try:
            nx = int(unidades_por_caja)
            if nx > 0:
                upc = nx
        except (TypeError, ValueError):
            pass
    upd = 12
    if unidades_por_docena is not None:
        try:
            nd = int(unidades_por_docena)
            if nd > 0:
                upd = nd
        except (TypeError, ValueError):
            pass
    # No usar rollback aquí: deshace el UPDATE principal del producto en la misma transacción
    # y el servidor seguía con presentaciones/Kardex + commit → datos «no guardados» al reabrir.
    if not _productos_tiene_columna(cur, "fraccionable"):
        return
    if empresa_scope is not None:
        cur.execute(
            """
            UPDATE productos SET fraccionable = %s, unidades_por_caja = %s, unidades_por_docena = %s, mh_codigo_unidad = %s
            WHERE id = %s AND empresa_id = %s
            """,
            (bool(fraccionable), upc, upd, mh, producto_id, empresa_scope),
        )
    else:
        cur.execute(
            """
            UPDATE productos SET fraccionable = %s, unidades_por_caja = %s, unidades_por_docena = %s, mh_codigo_unidad = %s
            WHERE id = %s
            """,
            (bool(fraccionable), upc, upd, mh, producto_id),
        )


def actualizar_producto(
    cur,
    producto_id: int,
    codigo_barra: str,
    nombre: str,
    precio_unitario: float,
    stock_actual: float,
    sucursal_id: int | None = None,
    *,
    empresa_scope: int | None = None,
    nueva_empresa_id: int | None = None,
    promocion_tipo: str | None = None,
    promocion_valor: float | None = None,
    costo_unitario: float | None = None,
    fraccionable: bool = False,
    unidades_por_caja: int | None = None,
    unidades_por_docena: int | None = 12,
    mh_codigo_unidad: str | None = None,
) -> None:
    cod = codigo_barra or nombre[:20]
    pt = (promocion_tipo or "").strip().upper() if promocion_tipo else None
    pv = float(promocion_valor) if promocion_valor is not None else None
    if pt and pt not in ("2X1", "PORCENTAJE"):
        pt = None
    costo = float(costo_unitario) if costo_unitario is not None else None
    mh_in = _mh_codigo_producto(mh_codigo_unidad)
    upd_in = int(unidades_por_docena) if unidades_por_docena is not None and int(unidades_por_docena) > 0 else 12
    if empresa_scope is not None:
        try:
            if costo is not None:
                cur.execute(
                    """
                    UPDATE productos SET codigo_barra = %s, nombre = %s, precio_unitario = %s, stock_actual = %s,
                        sucursal_id = %s, promocion_tipo = %s, promocion_valor = %s, costo_unitario = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (cod, nombre, precio_unitario, stock_actual, sucursal_id, pt, pv, costo, producto_id, empresa_scope),
                )
            else:
                cur.execute(
                    """
                    UPDATE productos SET codigo_barra = %s, nombre = %s, precio_unitario = %s, stock_actual = %s,
                        sucursal_id = %s, promocion_tipo = %s, promocion_valor = %s
                    WHERE id = %s AND empresa_id = %s
                    """,
                    (cod, nombre, precio_unitario, stock_actual, sucursal_id, pt, pv, producto_id, empresa_scope),
                )
        except Exception:
            cur.connection.rollback()
            cur.execute(
                """
                UPDATE productos SET codigo_barra = %s, nombre = %s, precio_unitario = %s, stock_actual = %s, sucursal_id = %s, promocion_tipo = %s, promocion_valor = %s
                WHERE id = %s AND empresa_id = %s
                """,
                (cod, nombre, precio_unitario, stock_actual, sucursal_id, pt, pv, producto_id, empresa_scope),
            )
        _actualizar_conversion_producto(
            cur, producto_id, fraccionable, unidades_por_caja, upd_in, mh_in, empresa_scope=empresa_scope
        )
        return
    parts = ["codigo_barra = %s", "nombre = %s", "precio_unitario = %s", "stock_actual = %s", "sucursal_id = %s", "promocion_tipo = %s", "promocion_valor = %s"]
    vals: list[Any] = [cod, nombre, precio_unitario, stock_actual, sucursal_id, pt, pv]
    if costo is not None:
        parts.append("costo_unitario = %s")
        vals.append(costo)
    if nueva_empresa_id is not None:
        parts.append("empresa_id = %s")
        vals.append(nueva_empresa_id)
    vals.append(producto_id)
    sql = f"UPDATE productos SET {', '.join(parts)} WHERE id = %s"
    try:
        cur.execute(sql, tuple(vals))
    except Exception:
        cur.connection.rollback()
        parts2 = ["codigo_barra = %s", "nombre = %s", "precio_unitario = %s", "stock_actual = %s", "sucursal_id = %s"]
        vals2: list[Any] = [cod, nombre, precio_unitario, stock_actual, sucursal_id]
        if nueva_empresa_id is not None:
            parts2.append("empresa_id = %s")
            vals2.append(nueva_empresa_id)
        vals2.append(producto_id)
        cur.execute(f"UPDATE productos SET {', '.join(parts2)} WHERE id = %s", tuple(vals2))
    _actualizar_conversion_producto(
        cur, producto_id, fraccionable, unidades_por_caja, upd_in, mh_in, empresa_scope=None
    )


def dar_baja_producto(
    cur,
    producto_id: int,
    motivo: str,
    usuario_baja_id: int | None = None,
    usuario_baja_username: str | None = None,
    empresa_id: int | None = None,
) -> bool:
    """Baja lógica: activo=FALSE, conserva fila y motivo para reporte."""
    asegurar_columnas_baja(cur)
    motivo_txt = (motivo or "").strip()[:2000]
    if not motivo_txt:
        return False
    uname = (usuario_baja_username or "").strip()[:100] or None
    if empresa_id:
        cur.execute(
            """
            UPDATE productos SET
                activo = FALSE,
                motivo_baja = %s,
                fecha_baja = CURRENT_TIMESTAMP,
                usuario_baja_id = %s,
                usuario_baja_username = %s
            WHERE id = %s AND empresa_id = %s
              AND COALESCE(activo, TRUE) = TRUE
            """,
            (motivo_txt, usuario_baja_id, uname, producto_id, empresa_id),
        )
    else:
        cur.execute(
            """
            UPDATE productos SET
                activo = FALSE,
                motivo_baja = %s,
                fecha_baja = CURRENT_TIMESTAMP,
                usuario_baja_id = %s,
                usuario_baja_username = %s
            WHERE id = %s AND COALESCE(activo, TRUE) = TRUE
            """,
            (motivo_txt, usuario_baja_id, uname, producto_id),
        )
    return cur.rowcount > 0


def eliminar_producto(cur, producto_id: int, empresa_id: int = None) -> bool:
    """Compatibilidad: delega en baja lógica (requiere motivo vía dar_baja_producto)."""
    return dar_baja_producto(cur, producto_id, "Baja sin motivo registrado (legacy)", empresa_id=empresa_id)


def reactivar_producto(cur, producto_id: int, empresa_id: int | None = None) -> bool:
    """Vuelve a activar un producto dado de baja; reaparece en inventario y caja."""
    asegurar_columnas_baja(cur)
    if empresa_id:
        cur.execute(
            """
            UPDATE productos SET
                activo = TRUE,
                motivo_baja = NULL,
                fecha_baja = NULL,
                usuario_baja_id = NULL,
                usuario_baja_username = NULL
            WHERE id = %s AND empresa_id = %s
              AND COALESCE(activo, TRUE) = FALSE
            """,
            (producto_id, empresa_id),
        )
    else:
        cur.execute(
            """
            UPDATE productos SET
                activo = TRUE,
                motivo_baja = NULL,
                fecha_baja = NULL,
                usuario_baja_id = NULL,
                usuario_baja_username = NULL
            WHERE id = %s AND COALESCE(activo, TRUE) = FALSE
            """,
            (producto_id,),
        )
    return cur.rowcount > 0


def listar_productos_baja(cur, empresa_id: int | None = None, limit: int = 500) -> list:
    """
    Productos dados de baja para reporte.
    (id, codigo, nombre, empresa, sucursal, motivo, fecha, usuario, rol_usuario, stock)
    """
    asegurar_columnas_baja(cur)
    fb = _filtro_activos_sql(cur, "p", solo_activos=False)
    cond = ""
    params: list[Any] = []
    if empresa_id is not None:
        cond = " AND p.empresa_id = %s"
        params.append(empresa_id)
    params.append(limit)
    try:
        cur.execute(
            f"""
            SELECT p.id, p.codigo_barra, p.nombre,
                   COALESCE(e.nombre_comercial, e.nombre, '—'),
                   COALESCE(s.nombre, '—'),
                   COALESCE(p.motivo_baja, '—'),
                   TO_CHAR(p.fecha_baja, 'DD/MM/YYYY HH24:MI'),
                   COALESCE(NULLIF(TRIM(p.usuario_baja_username), ''), u.username, '—'),
                   COALESCE(u.rol, '—'),
                   COALESCE(p.stock_actual, 0)
            FROM productos p
            LEFT JOIN empresas e ON e.id = p.empresa_id
            LEFT JOIN sucursales s ON s.id = p.sucursal_id
            LEFT JOIN usuarios u ON u.id = p.usuario_baja_id
            WHERE 1=1{fb}{cond}
            ORDER BY p.fecha_baja DESC NULLS LAST, p.id DESC
            LIMIT %s
            """,
            tuple(params),
        )
        return cur.fetchall() or []
    except Exception:
        cur.connection.rollback()
        return []


def productos_stock_bajo(cur, umbral: float = 5, empresa_id: int = None):
    fa = _filtro_activos_sql(cur, None, solo_activos=True)
    if empresa_id:
        cur.execute(
            f"""SELECT id, nombre, COALESCE(stock_actual, 0)
               FROM productos
               WHERE empresa_id = %s AND COALESCE(stock_actual, 0) < %s{fa}
               ORDER BY stock_actual ASC NULLS FIRST
               LIMIT 20""",
            (empresa_id, umbral),
        )
    else:
        cur.execute(
            f"""SELECT id, nombre, COALESCE(stock_actual, 0)
               FROM productos
               WHERE COALESCE(stock_actual, 0) < %s{fa}
               ORDER BY stock_actual ASC NULLS FIRST
               LIMIT 20""",
            (umbral,),
        )
    return cur.fetchall()


def contar_productos_stock_bajo(cur, umbral: float = 5, empresa_id: int = None):
    fa = _filtro_activos_sql(cur, None, solo_activos=True)
    if empresa_id:
        cur.execute(
            f"""SELECT COUNT(*)
               FROM productos
               WHERE empresa_id = %s AND COALESCE(stock_actual, 0) < %s{fa}""",
            (empresa_id, umbral),
        )
    else:
        cur.execute(
            f"""SELECT COUNT(*)
               FROM productos
               WHERE COALESCE(stock_actual, 0) < %s{fa}""",
            (umbral,),
        )
    row = cur.fetchone()
    return int(row[0]) if row else 0

