# Programador: Oscar Amaya Romero
"""Queries para reportes de inventario tributarios: Kardex Art. 142, F-983, Valuación NIC 2, Movimientos."""

from __future__ import annotations


def listar_kardex_detallado(
    cur,
    empresa_id: int,
    producto_id: int | None = None,
    sucursal_id: int | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    limit: int = 500,
) -> list[tuple]:
    """
    Kardex detallado Art. 142/142-A: fecha, tipo doc, cant entrada/salida, costo unit, saldo.
    Retorna: (fecha, tipo, cantidad, es_entrada, costo_unitario, saldo_acumulado, sucursal_origen, sucursal_destino, referencia)
    """
    filtros = ["k.empresa_id = %s"]
    params: list = [empresa_id]
    if producto_id is not None:
        filtros.append("k.producto_id = %s")
        params.append(producto_id)
    if sucursal_id is not None:
        filtros.append("(k.sucursal_id = %s OR k.sucursal_destino_id = %s)")
        params.extend([sucursal_id, sucursal_id])
    if fecha_inicio:
        filtros.append("k.creado_en::date >= %s")
        params.append(fecha_inicio)
    if fecha_fin:
        filtros.append("k.creado_en::date <= %s")
        params.append(fecha_fin)
    params.append(limit)
    where = " AND ".join(filtros)

    sql = f"""
    WITH movs AS (
        SELECT
            k.id,
            k.creado_en,
            k.tipo,
            k.cantidad,
            k.sucursal_id,
            k.sucursal_destino_id,
            k.referencia,
            GREATEST(0, COALESCE(NULLIF(k.costo_unitario, 0), NULLIF(p.costo_unitario, 0), p.precio_unitario, 0)) AS costo_unit,
            p.nombre AS producto_nombre,
            so.nombre AS suc_origen,
            sd.nombre AS suc_destino,
            CASE
                WHEN k.tipo IN ('ENTRADA', 'AJUSTE_ENTRADA') THEN 1
                WHEN k.tipo IN ('SALIDA', 'SALIDA_VENTA', 'AJUSTE_SALIDA') THEN -1
                ELSE 0
            END AS signo
        FROM inventario_kardex k
        JOIN productos p ON p.id = k.producto_id
        LEFT JOIN sucursales so ON so.id = k.sucursal_id
        LEFT JOIN sucursales sd ON sd.id = k.sucursal_destino_id
        WHERE {where}
    )
    SELECT
        m.creado_en,
        m.tipo,
        m.cantidad,
        CASE WHEN m.signo > 0 THEN m.cantidad ELSE 0 END,
        CASE WHEN m.signo < 0 THEN m.cantidad ELSE 0 END,
        m.costo_unit,
        m.referencia,
        m.suc_origen,
        m.suc_destino,
        m.producto_nombre
    FROM movs m
    ORDER BY m.creado_en ASC, m.id ASC
    LIMIT %s
    """
    cur.execute(sql, params)
    rows = cur.fetchall() or []

    # Calcular saldo acumulado por producto
    saldo_por_producto: dict[str, float] = {}
    out = []
    for r in rows:
        prod = r[8] or ""
        tipo = (r[1] or "").upper()
        cant = float(r[2] or 0)
        ent = float(r[3] or 0)
        sal = float(r[4] or 0)
        saldo_actual = saldo_por_producto.get(prod, 0) + ent - sal
        saldo_por_producto[prod] = saldo_actual
        out.append((*r[:6], round(saldo_actual, 4), *r[6:9]))
    return out


def listar_productos_para_f983(
    cur,
    empresa_id: int,
    ejercicio: int,
) -> list[tuple]:
    """
    Datos para F-983: nombre, codigo, unidad, inv_inicial, compras, ventas, inv_final, costo_unit.
    inv_final = stock actual; inv_inicial = inv_final - compras + ventas (para cuadrar).
    Solo productos con inv_final > 0 (F-983 no reporta existencia cero).
    """
    fecha_inicio = f"{ejercicio}-01-01"
    fecha_fin = f"{ejercicio}-12-31"
    sql = """
    WITH movs AS (
        SELECT
            k.producto_id,
            SUM(CASE WHEN k.tipo IN ('ENTRADA', 'AJUSTE_ENTRADA') THEN k.cantidad ELSE 0 END) AS compras,
            SUM(CASE WHEN k.tipo IN ('SALIDA_VENTA', 'SALIDA', 'AJUSTE_SALIDA') THEN k.cantidad ELSE 0 END) AS ventas
        FROM inventario_kardex k
        WHERE k.empresa_id = %s
          AND k.creado_en::date >= %s
          AND k.creado_en::date <= %s
        GROUP BY k.producto_id
    )
    SELECT
        LEFT(p.nombre, 50),
        LEFT(COALESCE(p.codigo_barra, p.id::text), 25),
        LEFT(COALESCE(NULLIF(TRIM(p.unidad_medida), ''), 'UNI'), 5),
        GREATEST(0, COALESCE(p.stock_actual, 0) - COALESCE(m.compras, 0) + COALESCE(m.ventas, 0)),
        COALESCE(m.compras, 0),
        COALESCE(m.ventas, 0),
        GREATEST(0, COALESCE(p.stock_actual, 0)),
        GREATEST(0.01, COALESCE(NULLIF(p.costo_unitario, 0), p.precio_unitario, 0.01))
    FROM productos p
    LEFT JOIN movs m ON m.producto_id = p.id
    WHERE p.empresa_id = %s
      AND COALESCE(p.stock_actual, 0) > 0
    ORDER BY p.nombre
    """
    cur.execute(sql, (empresa_id, fecha_inicio, fecha_fin, empresa_id))
    return cur.fetchall() or []


def listar_valuacion_inventario(
    cur,
    empresa_id: int,
    sucursal_id: int | None = None,
) -> list[tuple]:
    """
    Valuación: producto, codigo, unidad, cantidad, costo_unit, valor_total, metodo.
    """
    if sucursal_id is not None:
        sql = """
        SELECT
            p.nombre,
            COALESCE(p.codigo_barra, ''),
            COALESCE(NULLIF(TRIM(p.unidad_medida), ''), 'UNI'),
            COALESCE(pss.cantidad, 0),
            GREATEST(0, COALESCE(NULLIF(p.costo_unitario, 0), p.precio_unitario, 0)),
            COALESCE(pss.cantidad, 0) * GREATEST(0, COALESCE(NULLIF(p.costo_unitario, 0), p.precio_unitario, 0)),
            COALESCE(p.metodo_valuacion, 'PROMEDIO')
        FROM productos p
        LEFT JOIN producto_stock_sucursal pss ON pss.producto_id = p.id AND pss.sucursal_id = %s
        WHERE p.empresa_id = %s
        ORDER BY p.nombre
        """
        cur.execute(sql, (sucursal_id, empresa_id))
    else:
        sql = """
        SELECT
            p.nombre,
            COALESCE(p.codigo_barra, ''),
            COALESCE(NULLIF(TRIM(p.unidad_medida), ''), 'UNI'),
            COALESCE(p.stock_actual, 0),
            GREATEST(0, COALESCE(NULLIF(p.costo_unitario, 0), p.precio_unitario, 0)),
            COALESCE(p.stock_actual, 0) * GREATEST(0, COALESCE(NULLIF(p.costo_unitario, 0), p.precio_unitario, 0)),
            COALESCE(p.metodo_valuacion, 'PROMEDIO')
        FROM productos p
        WHERE p.empresa_id = %s
        ORDER BY p.nombre
        """
        cur.execute(sql, (empresa_id,))
    return cur.fetchall() or []


def listar_movimientos_global(
    cur,
    empresa_id: int,
    producto_id: int | None = None,
    sucursal_id: int | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    limit: int = 300,
) -> list[tuple]:
    """
    Movimientos por producto: ajustes, traslados, bajas. id, fecha, tipo, producto, cantidad, origen, destino, notas.
    """
    filtros = ["k.empresa_id = %s"]
    params: list = [empresa_id]
    if producto_id is not None:
        filtros.append("k.producto_id = %s")
        params.append(producto_id)
    if sucursal_id is not None:
        filtros.append("(k.sucursal_id = %s OR k.sucursal_destino_id = %s)")
        params.extend([sucursal_id, sucursal_id])
    if fecha_inicio:
        filtros.append("k.creado_en::date >= %s")
        params.append(fecha_inicio)
    if fecha_fin:
        filtros.append("k.creado_en::date <= %s")
        params.append(fecha_fin)
    params.append(limit)
    where = " AND ".join(filtros)

    sql = f"""
    SELECT
        k.id,
        k.creado_en,
        k.tipo,
        p.nombre,
        p.codigo_barra,
        k.cantidad,
        so.nombre,
        sd.nombre,
        k.notas,
        k.referencia,
        COALESCE(k.motivo_ajuste, '')
    FROM inventario_kardex k
    JOIN productos p ON p.id = k.producto_id
    LEFT JOIN sucursales so ON so.id = k.sucursal_id
    LEFT JOIN sucursales sd ON sd.id = k.sucursal_destino_id
    WHERE {where}
    ORDER BY k.creado_en DESC, k.id DESC
    LIMIT %s
    """
    cur.execute(sql, params)
    return cur.fetchall() or []


def listar_productos_para_conteo(
    cur,
    empresa_id: int,
    sucursal_id: int | None = None,
) -> list[tuple]:
    """
    Lista productos para conteo físico: (producto_id, codigo, nombre, stock_sistema, unidad, costo_unit).
    Si sucursal_id: stock de esa sucursal. Si no: stock total.
    """
    if sucursal_id is not None:
        sql = """
        SELECT p.id, COALESCE(p.codigo_barra, ''), p.nombre,
               COALESCE(pss.cantidad, 0),
               COALESCE(NULLIF(TRIM(p.unidad_medida), ''), 'UNI'),
               GREATEST(0, COALESCE(NULLIF(p.costo_unitario, 0), p.precio_unitario, 0))
        FROM productos p
        JOIN producto_stock_sucursal pss ON pss.producto_id = p.id AND pss.sucursal_id = %s
        WHERE p.empresa_id = %s
          AND pss.cantidad > 0
        ORDER BY p.nombre
        """
        cur.execute(sql, (sucursal_id, empresa_id))
    else:
        sql = """
        SELECT p.id, COALESCE(p.codigo_barra, ''), p.nombre,
               COALESCE(p.stock_actual, 0),
               COALESCE(NULLIF(TRIM(p.unidad_medida), ''), 'UNI'),
               GREATEST(0, COALESCE(NULLIF(p.costo_unitario, 0), p.precio_unitario, 0))
        FROM productos p
        WHERE p.empresa_id = %s
          AND COALESCE(p.stock_actual, 0) > 0
        ORDER BY p.nombre
        """
        cur.execute(sql, (empresa_id,))
    rows = list(cur.fetchall() or [])
    from azdigital.repositories import presentaciones_repo

    ids = [int(r[0]) for r in rows if r and r[0] is not None]
    umb_map = presentaciones_repo.nombres_umb_por_productos(cur, ids)
    out: list[tuple] = []
    for r in rows:
        r = list(r)
        try:
            uid = int(r[0])
        except (TypeError, ValueError):
            out.append(tuple(r))
            continue
        u = umb_map.get(uid)
        if u:
            r[4] = u
        else:
            old = str(r[4] or "").strip()
            if not old or old.upper() in ("UNI", "UNIDAD", "U", "UND", "UN"):
                r[4] = "UMB"
        out.append(tuple(r))
    return out


def listar_reporte_mermas_ajustes(
    cur,
    empresa_id: int,
    fecha_inicio: str,
    fecha_fin: str,
    sucursal_id: int | None = None,
    solo_perdidas: bool = True,
    usuario_id: int | None = None,
) -> tuple[list[tuple], dict[str, float]]:
    """
    Movimientos de ajuste con costo y motivo (merma, avería, faltante, sobrante).
    Filas: fecha, tipo, producto, codigo, cantidad, costo_unit, valor_impacto, motivo_cod, sucursal, referencia, usuario.
    """
    filtros = ["k.empresa_id = %s", "k.creado_en::date >= %s", "k.creado_en::date <= %s"]
    params: list = [empresa_id, fecha_inicio, fecha_fin]
    if solo_perdidas:
        filtros.append("k.tipo = 'AJUSTE_SALIDA'")
    else:
        filtros.append("k.tipo IN ('AJUSTE_SALIDA', 'AJUSTE_ENTRADA')")
    if sucursal_id is not None:
        filtros.append("k.sucursal_id = %s")
        params.append(sucursal_id)
    if usuario_id is not None:
        filtros.append("k.usuario_id = %s")
        params.append(usuario_id)
    where = " AND ".join(filtros)
    sql = f"""
    SELECT
        k.creado_en,
        k.tipo,
        p.nombre,
        COALESCE(p.codigo_barra, ''),
        k.cantidad,
        COALESCE(NULLIF(k.costo_unitario, 0), NULLIF(p.costo_unitario, 0), p.precio_unitario, 0)::numeric,
        (k.cantidad * COALESCE(NULLIF(k.costo_unitario, 0), NULLIF(p.costo_unitario, 0), p.precio_unitario, 0))::numeric,
        COALESCE(k.motivo_ajuste, ''),
        COALESCE(so.nombre, ''),
        COALESCE(k.referencia, ''),
        COALESCE(u.username, '')
    FROM inventario_kardex k
    JOIN productos p ON p.id = k.producto_id
    LEFT JOIN sucursales so ON so.id = k.sucursal_id
    LEFT JOIN usuarios u ON u.id = k.usuario_id
    WHERE {where}
    ORDER BY k.creado_en DESC, k.id DESC
    """
    cur.execute(sql, params)
    rows = list(cur.fetchall() or [])
    total = 0.0
    for r in rows:
        if len(r) > 6:
            try:
                total += float(r[6] or 0)
            except (TypeError, ValueError):
                pass
    return rows, {"total_valor": total, "n_movs": len(rows)}


def get_stock_producto(cur, producto_id: int, sucursal_id: int | None = None) -> float:
    """Stock actual de un producto. Si sucursal_id: de esa sucursal (pss). Si no: stock total."""
    if sucursal_id is not None:
        cur.execute(
            "SELECT COALESCE(cantidad, 0) FROM producto_stock_sucursal WHERE producto_id = %s AND sucursal_id = %s",
            (producto_id, sucursal_id),
        )
        r = cur.fetchone()
        return float(r[0] or 0) if r else 0.0
    cur.execute("SELECT COALESCE(stock_actual, 0) FROM productos WHERE id = %s", (producto_id,))
    r = cur.fetchone()
    return float(r[0] or 0) if r else 0.0
