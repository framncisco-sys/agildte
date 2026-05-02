# Programador: Oscar Amaya Romero
"""Queries para reportes de facturación: Libro IVA, Ventas por Producto, Documentos Anulados, Cuentas por Cobrar."""

from __future__ import annotations


def listar_libro_iva(
    cur,
    empresa_id: int,
    fecha_inicio: str,
    fecha_fin: str,
) -> list[tuple]:
    """
    Libro de IVA: ventas por tipo DTE (contribuyente vs consumidor final).
    Retorna: (id, fecha, tipo_dte, cliente, doc_cliente, venta_gravada, iva, total, es_contribuyente)
    IVA 13%: venta_gravada = total/1.13, iva = total - venta_gravada
    """
    try:
        cur.execute(
            """
            SELECT v.id, TO_CHAR(v.fecha_registro, 'DD/MM/YYYY'), COALESCE(v.tipo_comprobante, 'TICKET'),
                   COALESCE(c.nombre_cliente, v.cliente_nombre, 'Consumidor Final'),
                   COALESCE(c.tipo_documento || ': ' || c.numero_documento, c.numero_documento, '—'),
                   ROUND(v.total_pagar / 1.13, 2),
                   ROUND(v.total_pagar - (v.total_pagar / 1.13), 2),
                   v.total_pagar,
                   COALESCE(c.es_contribuyente, FALSE),
                   COALESCE(v.retencion_iva, 0)
            FROM ventas v
            LEFT JOIN clientes c ON c.id = v.cliente_id
            WHERE (v.empresa_id IS NULL OR v.empresa_id = %s)
              AND COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
              AND v.fecha_registro::date BETWEEN %s AND %s
            ORDER BY v.fecha_registro, v.id
            """,
            (empresa_id, fecha_inicio, fecha_fin),
        )
        return cur.fetchall() or []
    except Exception:
        cur.connection.rollback()
        cur.execute(
            """
            SELECT v.id, TO_CHAR(v.fecha_registro, 'DD/MM/YYYY'), COALESCE(v.tipo_comprobante, 'TICKET'),
                   COALESCE(c.nombre_cliente, v.cliente_nombre, 'Consumidor Final'),
                   COALESCE(c.tipo_documento || ': ' || c.numero_documento, c.numero_documento, '—'),
                   ROUND(v.total_pagar / 1.13, 2),
                   ROUND(v.total_pagar - (v.total_pagar / 1.13), 2),
                   v.total_pagar,
                   COALESCE(c.es_contribuyente, FALSE)
            FROM ventas v
            LEFT JOIN clientes c ON c.id = v.cliente_id
            WHERE (v.empresa_id IS NULL OR v.empresa_id = %s)
              AND COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
              AND v.fecha_registro::date BETWEEN %s AND %s
            ORDER BY v.fecha_registro, v.id
            """,
            (empresa_id, fecha_inicio, fecha_fin),
        )
        rows = cur.fetchall() or []
        return [(*r, 0.0) for r in rows]


def ventas_cantidad_por_producto(
    cur,
    empresa_id: int,
    fecha_inicio: str,
    fecha_fin: str,
) -> dict[int, float]:
    """
    Cantidad vendida por producto en el período. Retorna {producto_id: cantidad}.
    """
    try:
        cur.execute(
            """
            SELECT dv.producto_id, COALESCE(SUM(dv.cantidad), 0)
            FROM venta_detalles dv
            JOIN ventas v ON v.id = dv.venta_id
            WHERE (v.empresa_id IS NULL OR v.empresa_id = %s)
              AND COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
              AND v.fecha_registro::date BETWEEN %s AND %s
            GROUP BY dv.producto_id
            """,
            (empresa_id, fecha_inicio, fecha_fin),
        )
        return {int(r[0]): float(r[1] or 0) for r in (cur.fetchall() or [])}
    except Exception:
        cur.connection.rollback()
        return {}


def listar_ventas_por_producto(
    cur,
    empresa_id: int,
    fecha_inicio: str,
    fecha_fin: str,
) -> list[tuple]:
    """
    Ventas por producto: producto, codigo, cantidad, subtotal, num_ventas.
    """
    cur.execute(
        """
        SELECT p.nombre, COALESCE(p.codigo_barra, ''),
               SUM(dv.cantidad), SUM(dv.subtotal), COUNT(DISTINCT v.id)
        FROM venta_detalles dv
        JOIN ventas v ON v.id = dv.venta_id
        JOIN productos p ON p.id = dv.producto_id
        WHERE (v.empresa_id IS NULL OR v.empresa_id = %s)
          AND COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
          AND v.fecha_registro::date BETWEEN %s AND %s
        GROUP BY p.id, p.nombre, p.codigo_barra
        ORDER BY SUM(dv.subtotal) DESC
        """,
        (empresa_id, fecha_inicio, fecha_fin),
    )
    return cur.fetchall() or []


def listar_documentos_anulados(
    cur,
    empresa_id: int,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    limit: int = 200,
) -> list[tuple]:
    """
    Documentos anulados: id, fecha, total, cliente, tipo_comprobante, motivo, usuario_anulo, fecha_anulacion, codigo_generacion.
    """
    filtros = ["(v.empresa_id IS NULL OR v.empresa_id = %s)", "COALESCE(v.estado, 'ACTIVO') = 'ANULADO'"]
    params: list = [empresa_id]
    if fecha_inicio:
        filtros.append("v.fecha_registro::date >= %s")
        params.append(fecha_inicio)
    if fecha_fin:
        filtros.append("v.fecha_registro::date <= %s")
        params.append(fecha_fin)
    params.append(limit)
    where = " AND ".join(filtros)
    try:
        cur.execute(
            f"""
            SELECT v.id, TO_CHAR(v.fecha_registro, 'DD/MM/YYYY HH24:MI'),
                   v.total_pagar, COALESCE(v.cliente_nombre, '—'),
                   COALESCE(v.tipo_comprobante, 'TICKET'),
                   COALESCE(v.motivo_anulacion, '—'),
                   COALESCE(u.username, '—'),
                   TO_CHAR(v.fecha_anulacion, 'DD/MM/YYYY HH24:MI'),
                   COALESCE(v.codigo_generacion, '')
            FROM ventas v
            LEFT JOIN usuarios u ON u.id = v.usuario_anulo_id
            WHERE {where}
            ORDER BY v.fecha_anulacion DESC NULLS LAST, v.id DESC
            LIMIT %s
            """,
            params,
        )
        return cur.fetchall() or []
    except Exception:
        cur.connection.rollback()
        try:
            cur.execute(
                f"""
                SELECT v.id, TO_CHAR(v.fecha_registro, 'DD/MM/YYYY HH24:MI'),
                       v.total_pagar, COALESCE(v.cliente_nombre, '—'),
                       COALESCE(v.tipo_comprobante, 'TICKET'),
                       COALESCE(v.motivo_anulacion, '—'),
                       COALESCE(u.username, '—'),
                       TO_CHAR(v.fecha_anulacion, 'DD/MM/YYYY HH24:MI'),
                       COALESCE(v.codigo_generacion, '')
                FROM ventas v
                LEFT JOIN usuarios u ON u.id = v.usuario_anulo_id
                WHERE {where}
                ORDER BY v.fecha_anulacion DESC NULLS LAST, v.id DESC
                LIMIT %s
                """,
                params,
            )
            rows = cur.fetchall() or []
            return [(r[0], r[1], r[2], r[3], r[4], r[5] if len(r) > 5 else "—", r[6] if len(r) > 6 else "—", r[7] if len(r) > 7 else "—", r[8] if len(r) > 8 else "") for r in rows]
        except Exception:
            cur.connection.rollback()
            cur.execute(
                f"""
                SELECT v.id, TO_CHAR(v.fecha_registro, 'DD/MM/YYYY HH24:MI'),
                       v.total_pagar, COALESCE(v.cliente_nombre, '—'),
                       COALESCE(v.tipo_comprobante, 'TICKET')
                FROM ventas v
                WHERE {where}
                ORDER BY v.id DESC
                LIMIT %s
                """,
                params,
            )
            rows = cur.fetchall() or []
            return [(r[0], r[1], r[2], r[3], r[4], "—", "—", "—", "") for r in rows]


def listar_cuentas_por_cobrar(
    cur,
    empresa_id: int,
) -> list[tuple]:
    """
    Cartera de clientes: ventas pendientes de cobro.
    Retorna: (id, fecha, cliente, doc, tipo_comprobante, total, dias_vencido)
    """
    cur.execute(
        """
        SELECT v.id, TO_CHAR(v.fecha_registro, 'DD/MM/YYYY'),
               COALESCE(c.nombre_cliente, v.cliente_nombre, '—'),
               COALESCE(c.numero_documento, '—'),
               COALESCE(v.tipo_comprobante, 'TICKET'),
               v.total_pagar,
               CURRENT_DATE - v.fecha_registro::date
        FROM ventas v
        LEFT JOIN clientes c ON c.id = v.cliente_id
        WHERE (v.empresa_id IS NULL OR v.empresa_id = %s)
          AND COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
          AND COALESCE(v.estado_cobro, 'COBRADO') = 'PENDIENTE'
        ORDER BY v.fecha_registro ASC
        """,
        (empresa_id,),
    )
    return cur.fetchall() or []
