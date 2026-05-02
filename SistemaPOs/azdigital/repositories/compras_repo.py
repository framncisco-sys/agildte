# Programador: Oscar Amaya Romero
"""Repositorio de compras (facturas de proveedores)."""

from __future__ import annotations


def columnas_detalle_presentacion_existen(cur) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'compra_detalles' AND column_name = 'factor_conversion'
        """
    )
    return cur.fetchone() is not None


def listar(cur, empresa_id: int, limit: int = 100) -> list[tuple]:
    """Lista compras recientes: (id, fecha, proveedor_nombre, numero_factura, total)."""
    cur.execute(
        """
        SELECT c.id, c.fecha, COALESCE(p.nombre, '—'), COALESCE(c.numero_factura, '—'), COALESCE(c.total, 0)
        FROM compras c
        LEFT JOIN proveedores p ON p.id = c.proveedor_id
        WHERE c.empresa_id = %s
        ORDER BY c.fecha DESC, c.id DESC
        LIMIT %s
        """,
        (empresa_id, limit),
    )
    return cur.fetchall() or []


def get(cur, compra_id: int, empresa_id: int) -> tuple | None:
    """Obtiene compra: (id, proveedor_id, numero_factura, fecha, total, notas, retencion_iva)."""
    try:
        cur.execute(
            "SELECT id, proveedor_id, numero_factura, fecha, total, notas, COALESCE(retencion_iva, 0) FROM compras WHERE id = %s AND empresa_id = %s",
            (compra_id, empresa_id),
        )
        return cur.fetchone()
    except Exception:
        cur.execute(
            "SELECT id, proveedor_id, numero_factura, fecha, total, notas FROM compras WHERE id = %s AND empresa_id = %s",
            (compra_id, empresa_id),
        )
        row = cur.fetchone()
        return (*row, 0) if row else None


def get_detalles(cur, compra_id: int) -> list[tuple]:
    """
    Detalle: (producto_id, nombre, codigo, cantidad_umb, costo_unitario_umb, subtotal
              [, cantidad_recibida_presentacion, factor_conversion, presentacion_nombre]).
    """
    if columnas_detalle_presentacion_existen(cur):
        cur.execute(
            """
            SELECT cd.producto_id, p.nombre, COALESCE(p.codigo_barra, ''),
                   cd.cantidad, cd.costo_unitario, cd.subtotal,
                   cd.cantidad_recibida_presentacion, cd.factor_conversion, cd.presentacion_nombre
            FROM compra_detalles cd
            JOIN productos p ON p.id = cd.producto_id
            WHERE cd.compra_id = %s
            ORDER BY cd.id
            """,
            (compra_id,),
        )
        return cur.fetchall() or []
    cur.execute(
        """
        SELECT cd.producto_id, p.nombre, COALESCE(p.codigo_barra, ''), cd.cantidad, cd.costo_unitario, cd.subtotal
        FROM compra_detalles cd
        JOIN productos p ON p.id = cd.producto_id
        WHERE cd.compra_id = %s
        ORDER BY cd.id
        """,
        (compra_id,),
    )
    return cur.fetchall() or []


def crear(
    cur,
    empresa_id: int,
    proveedor_id: int,
    numero_factura: str,
    fecha: str,
    usuario_id: int | None,
    notas: str = "",
    codigo_generacion: str = "",
    sello_recepcion: str = "",
) -> int:
    """Crea compra. Retorna id."""
    try:
        cur.execute(
            """
            INSERT INTO compras (empresa_id, proveedor_id, numero_factura, fecha, total, notas, usuario_id, codigo_generacion, sello_recepcion)
            VALUES (%s, %s, %s, %s, 0, %s, %s, %s, %s) RETURNING id
            """,
            (empresa_id, proveedor_id, numero_factura.strip(), fecha, notas.strip(), usuario_id, (codigo_generacion or "").strip() or None, (sello_recepcion or "").strip() or None),
        )
    except Exception:
        cur.connection.rollback()
        cur.execute(
            """
            INSERT INTO compras (empresa_id, proveedor_id, numero_factura, fecha, total, notas, usuario_id)
            VALUES (%s, %s, %s, %s, 0, %s, %s) RETURNING id
            """,
            (empresa_id, proveedor_id, numero_factura.strip(), fecha, notas.strip(), usuario_id),
        )
    return int(cur.fetchone()[0])


def agregar_detalle(
    cur,
    compra_id: int,
    producto_id: int,
    cantidad: float,
    costo_unitario: float,
    *,
    cantidad_recibida_presentacion: float | None = None,
    factor_conversion: float | None = None,
    presentacion_nombre: str | None = None,
) -> None:
    """
    Agrega línea al detalle. cantidad y costo_unitario van siempre en UMB (inventario).
    Si hay conversión, se guardan snapshot de factura: cantidad recibida, factor y nombre de empaque.
    """
    subtotal = float(cantidad) * float(costo_unitario)
    if columnas_detalle_presentacion_existen(cur):
        cur.execute(
            """
            INSERT INTO compra_detalles (
                compra_id, producto_id, cantidad, costo_unitario, subtotal,
                cantidad_recibida_presentacion, factor_conversion, presentacion_nombre
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                compra_id,
                producto_id,
                cantidad,
                costo_unitario,
                subtotal,
                cantidad_recibida_presentacion,
                factor_conversion,
                (presentacion_nombre or "").strip() or None,
            ),
        )
        return
    cur.execute(
        """
        INSERT INTO compra_detalles (compra_id, producto_id, cantidad, costo_unitario, subtotal)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (compra_id, producto_id, cantidad, costo_unitario, subtotal),
    )


def actualizar_total(cur, compra_id: int, retencion_iva: float = 0) -> None:
    """Recalcula total de la compra y opcionalmente actualiza retención IVA."""
    cur.execute(
        "SELECT COALESCE(SUM(subtotal), 0) FROM compra_detalles WHERE compra_id = %s",
        (compra_id,),
    )
    total = float(cur.fetchone()[0] or 0)
    cur.execute(
        "UPDATE compras SET total = %s, retencion_iva = COALESCE(%s, 0) WHERE id = %s",
        (total, retencion_iva, compra_id),
    )
