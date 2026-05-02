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
    limit: int = 100,
) -> list[tuple]:
    """
    Productos con stock bajo. Retorna: (id, codigo, nombre, stock, costo_actual, precio_actual).
    """
    try:
        cur.execute(
            """
            SELECT p.id, COALESCE(TRIM(p.codigo_barra), '—'),
                   p.nombre, COALESCE(p.stock_actual, 0),
                   COALESCE(NULLIF(p.costo_unitario, 0), 0),
                   COALESCE(p.precio_unitario, 0)
            FROM productos p
            WHERE p.empresa_id = %s AND COALESCE(p.stock_actual, 0) < %s
            ORDER BY p.stock_actual ASC NULLS FIRST
            LIMIT %s
            """,
            (empresa_id, umbral, limit),
        )
        return cur.fetchall() or []
    except Exception:
        cur.execute(
            """
            SELECT p.id, COALESCE(TRIM(p.codigo_barra), '—'),
                   p.nombre, COALESCE(p.stock_actual, 0), 0, COALESCE(p.precio_unitario, 0)
            FROM productos p
            WHERE p.empresa_id = %s AND COALESCE(p.stock_actual, 0) < %s
            ORDER BY p.stock_actual ASC NULLS FIRST
            LIMIT %s
            """,
            (empresa_id, umbral, limit),
        )
        return cur.fetchall() or []


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
