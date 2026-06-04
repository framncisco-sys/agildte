# Programador: Oscar Amaya Romero
"""Repositorio para lista de compras y sugerencias de precios justos."""

from __future__ import annotations

from typing import Any


def tabla_costos_existe(cur) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'producto_costos'"
    )
    return cur.fetchone() is not None


def listar_productos_para_compra(
    cur,
    empresa_id: int,
    umbral: float = 10,
    limit: int = 500,
    busqueda: str | None = None,
) -> list[tuple]:
    """
    Productos con stock bajo. Retorna: (id, codigo, nombre, stock, costo_actual, precio_actual).

    Si ``busqueda`` tiene texto, también incluye coincidencias por nombre o código aunque
    el stock sea >= umbral (para localizar un producto específico).
    """
    from azdigital.repositories import productos_repo

    productos_repo.asegurar_columnas_baja(cur)
    fa = productos_repo._filtro_activos_sql(cur, "p", solo_activos=True)
    term = (busqueda or "").strip()
    if term:
        like = f"%{term}%"
        term_trim = term.strip()
        sql = f"""
            SELECT p.id, COALESCE(TRIM(p.codigo_barra), '—'),
                   p.nombre, COALESCE(p.stock_actual, 0),
                   COALESCE(NULLIF(p.costo_unitario, 0), 0),
                   COALESCE(p.precio_unitario, 0)
            FROM productos p
            WHERE p.empresa_id = %s
              {fa}
              AND (
                COALESCE(p.stock_actual, 0) < %s
                OR p.nombre ILIKE %s
                OR COALESCE(TRIM(p.codigo_barra), '') ILIKE %s
                OR TRIM(COALESCE(p.codigo_barra, '')) = %s
              )
            ORDER BY
              CASE WHEN TRIM(COALESCE(p.codigo_barra, '')) = %s THEN 0
                   WHEN p.nombre ILIKE %s OR COALESCE(TRIM(p.codigo_barra), '') ILIKE %s THEN 1
                   ELSE 2 END,
              p.stock_actual ASC NULLS FIRST,
              p.nombre
            LIMIT %s
            """
        params = (
            empresa_id,
            umbral,
            like,
            like,
            term_trim,
            term_trim,
            like,
            like,
            max(limit, 50),
        )
        try:
            cur.execute(sql, params)
            rows = cur.fetchall() or []
            if rows:
                return rows
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                SELECT p.id, COALESCE(TRIM(p.codigo_barra), '—'),
                       p.nombre, COALESCE(p.stock_actual, 0), 0, COALESCE(p.precio_unitario, 0)
                FROM productos p
                WHERE p.empresa_id = %s
                  {fa}
                  AND (
                    COALESCE(p.stock_actual, 0) < %s
                    OR p.nombre ILIKE %s
                    OR COALESCE(TRIM(p.codigo_barra), '') ILIKE %s
                  )
                ORDER BY p.stock_actual ASC NULLS FIRST
                LIMIT %s
                """,
                (empresa_id, umbral, like, like, max(limit, 50)),
            )
            return cur.fetchall() or []
        except Exception:
            return []

    sql_base = f"""
        SELECT p.id, COALESCE(TRIM(p.codigo_barra), '—'),
               p.nombre, COALESCE(p.stock_actual, 0),
               COALESCE(NULLIF(p.costo_unitario, 0), 0),
               COALESCE(p.precio_unitario, 0)
        FROM productos p
        WHERE p.empresa_id = %s
          AND COALESCE(p.stock_actual, 0) < %s
          {fa}
        ORDER BY p.stock_actual ASC NULLS FIRST
        LIMIT %s
        """
    try:
        cur.execute(sql_base, (empresa_id, umbral, limit))
        return cur.fetchall() or []
    except Exception:
        cur.execute(
            f"""
            SELECT p.id, COALESCE(TRIM(p.codigo_barra), '—'),
                   p.nombre, COALESCE(p.stock_actual, 0), 0, COALESCE(p.precio_unitario, 0)
            FROM productos p
            WHERE p.empresa_id = %s AND COALESCE(p.stock_actual, 0) < %s
              {fa}
            ORDER BY p.stock_actual ASC NULLS FIRST
            LIMIT %s
            """,
            (empresa_id, umbral, limit),
        )
        return cur.fetchall() or []


def ultimos_costos_desde_compras_batch(
    cur, producto_ids: list[int], empresa_id: int
) -> dict[int, float]:
    """Último costo unitario (UMB) por producto según facturas de compra registradas."""
    if not producto_ids:
        return {}
    try:
        cur.execute(
            """
            SELECT DISTINCT ON (cd.producto_id)
                   cd.producto_id, cd.costo_unitario
            FROM compra_detalles cd
            INNER JOIN compras c ON c.id = cd.compra_id AND c.empresa_id = %s
            WHERE cd.producto_id = ANY(%s)
              AND COALESCE(cd.costo_unitario, 0) > 0
            ORDER BY cd.producto_id, c.fecha DESC NULLS LAST, cd.id DESC
            """,
            (empresa_id, producto_ids),
        )
        return {int(r[0]): float(r[1]) for r in (cur.fetchall() or []) if r[1]}
    except Exception:
        return {}


def resolver_costo_base(
    costo_en_producto: float,
    ultimo_historial: float | None,
    costo_promedio: float | None,
    ultimo_compra: float | None,
) -> tuple[float, str]:
    """
    Mejor costo disponible para calcular precio sugerido.
    Prioridad: última compra (factura) → historial → promedio → ficha producto.
    """
    if ultimo_compra and float(ultimo_compra) > 0:
        return float(ultimo_compra), "Última compra"
    if ultimo_historial and float(ultimo_historial) > 0:
        return float(ultimo_historial), "Historial costos"
    if costo_promedio and float(costo_promedio) > 0:
        return float(costo_promedio), "Costo promedio"
    if costo_en_producto and float(costo_en_producto) > 0:
        return float(costo_en_producto), "Ficha producto"
    return 0.0, "Sin costo"


def enriquecer_filas_lista_compra(
    cur,
    empresa_id: int,
    filas_raw: list[tuple],
    margen_sugerido: float,
    ventas_por_prod: dict[int, float],
    umbral: float,
) -> list[dict]:
    """Construye filas para plantilla con costos, precio sugerido y flags de acción."""
    pids = [int(r[0]) for r in filas_raw]
    costos_compra = ultimos_costos_desde_compras_batch(cur, pids, empresa_id)
    filas: list[dict] = []
    margen_pct = float(margen_sugerido)
    for r in filas_raw:
        pid = int(r[0])
        codigo, nombre = r[1], r[2]
        stock = float(r[3] or 0)
        costo_actual = float(r[4] or 0)
        precio_actual = float(r[5] or 0)
        ultimo_hist = ultimo_costo_desde_historial(cur, pid)
        costo_prom = costo_promedio_historico(cur, pid)
        ultimo_compra = costos_compra.get(pid)
        costo_base, origen_costo = resolver_costo_base(
            costo_actual, ultimo_hist, costo_prom, ultimo_compra
        )
        costo_ultimo = ultimo_compra or ultimo_hist or costo_actual
        costo_promedio = costo_prom if costo_prom and costo_prom > 0 else costo_base
        if costo_base > 0:
            precio_sugerido = round(costo_base * (1 + margen_pct / 100), 2)
        elif precio_actual > 0:
            precio_sugerido = precio_actual
        else:
            precio_sugerido = 0.0
        margen_actual = (
            ((precio_actual - costo_base) / costo_base * 100) if costo_base > 0 else 0.0
        )
        ventas_periodo = float(ventas_por_prod.get(pid, 0.0))
        cant_min_umbral = max(0.0, umbral - stock) if stock < umbral else 0.0
        cant_sugerida = max(ventas_periodo, cant_min_umbral)
        filas.append(
            {
                "id": pid,
                "codigo": codigo,
                "nombre": nombre,
                "stock": stock,
                "ventas_periodo": ventas_periodo,
                "cant_sugerida": cant_sugerida,
                "costo_actual": costo_actual,
                "costo_base": costo_base,
                "origen_costo": origen_costo,
                "costo_ultimo": costo_ultimo if costo_ultimo > 0 else costo_base,
                "costo_promedio": costo_promedio,
                "precio_actual": precio_actual,
                "margen_actual": margen_actual,
                "precio_sugerido": precio_sugerido,
                "margen_sugerido": margen_pct,
                "puede_aplicar_precio": costo_base > 0 and precio_sugerido > 0,
                "sin_costo": costo_base <= 0,
            }
        )
    return filas


def aplicar_precio_sugerido_producto(
    cur,
    producto_id: int,
    empresa_id: int,
    margen_sugerido: float,
    usuario_id: int | None,
) -> tuple[bool, str]:
    """Calcula y guarda costo + precio sugerido para un producto. Retorna (ok, mensaje)."""
    cur.execute(
        """
        SELECT COALESCE(NULLIF(costo_unitario, 0), 0), COALESCE(precio_unitario, 0)
        FROM productos WHERE id = %s AND empresa_id = %s
        """,
        (producto_id, empresa_id),
    )
    row = cur.fetchone()
    if not row:
        return False, "Producto no encontrado."
    costo_actual, precio_actual = float(row[0] or 0), float(row[1] or 0)
    ultimo_hist = ultimo_costo_desde_historial(cur, producto_id)
    costo_prom = costo_promedio_historico(cur, producto_id)
    compra_map = ultimos_costos_desde_compras_batch(cur, [producto_id], empresa_id)
    costo_base, _ = resolver_costo_base(
        costo_actual, ultimo_hist, costo_prom, compra_map.get(producto_id)
    )
    if costo_base <= 0:
        return False, "Sin costo de compra. Registre una factura o indique el costo en inventario."
    precio_new = round(costo_base * (1 + float(margen_sugerido) / 100), 2)
    if not actualizar_costo_y_precio_producto(cur, producto_id, empresa_id, costo_base, precio_new):
        return False, "No se pudo actualizar el producto."
    if tabla_costos_existe(cur):
        registrar_costo_compra(
            cur, producto_id, costo_base, 1, usuario_id, "Precio sugerido lista compras"
        )
    return True, f"Precio ${precio_new:.2f} (costo ${costo_base:.2f} + {margen_sugerido:g}%)"


def ultimo_costo_desde_historial(cur, producto_id: int) -> float | None:
    """Último costo registrado en historial (si existe tabla)."""
    if not tabla_costos_existe(cur):
        return None
    try:
        cur.execute(
            """
            SELECT costo FROM producto_costos
            WHERE producto_id = %s AND costo > 0
            ORDER BY creado_en DESC LIMIT 1
            """,
            (producto_id,),
        )
        r = cur.fetchone()
        return float(r[0]) if r and r[0] else None
    except Exception:
        return None


def costo_promedio_historico(cur, producto_id: int, ultimos_n: int = 5) -> float | None:
    """Promedio de los últimos N costos registrados."""
    if not tabla_costos_existe(cur):
        return None
    try:
        cur.execute(
            """
            SELECT AVG(costo) FROM (
                SELECT costo FROM producto_costos
                WHERE producto_id = %s AND costo > 0
                ORDER BY creado_en DESC LIMIT %s
            ) t
            """,
            (producto_id, ultimos_n),
        )
        r = cur.fetchone()
        return float(r[0]) if r and r[0] else None
    except Exception:
        return None


def registrar_costo_compra(
    cur,
    producto_id: int,
    costo: float,
    cantidad: float = 1,
    usuario_id: int | None = None,
    referencia: str | None = None,
) -> bool:
    """Registra un costo de compra en el historial."""
    if not tabla_costos_existe(cur) or not costo or float(costo) <= 0:
        return False
    try:
        cur.execute(
            """
            INSERT INTO producto_costos (producto_id, costo, cantidad, tipo, referencia, usuario_id)
            VALUES (%s, %s, %s, 'COMPRA', %s, %s)
            """,
            (producto_id, float(costo), float(cantidad), referencia or None, usuario_id),
        )
        return True
    except Exception:
        return False


def actualizar_costo_y_precio_producto(
    cur, producto_id: int, empresa_id: int, costo: float | None, precio: float | None
) -> bool:
    """Actualiza costo_unitario y/o precio_unitario del producto."""
    if costo is None and precio is None:
        return False
    updates: list[str] = []
    params: list[Any] = []
    if costo is not None:
        updates.append("costo_unitario = %s")
        params.append(float(costo))
    if precio is not None:
        updates.append("precio_unitario = %s")
        params.append(float(precio))
    if not updates:
        return False
    params.extend([producto_id, empresa_id])
    cur.execute(
        f"UPDATE productos SET {', '.join(updates)} WHERE id = %s AND empresa_id = %s",
        tuple(params),
    )
    return cur.rowcount > 0
