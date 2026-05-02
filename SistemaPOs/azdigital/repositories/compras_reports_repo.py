# Programador: Oscar Amaya Romero
"""Queries para reportes de compras: Libro IVA Compras."""

from __future__ import annotations


def listar_libro_iva_compras(
    cur,
    empresa_id: int,
    fecha_inicio: str,
    fecha_fin: str,
) -> list[tuple]:
    """
    Libro de IVA Compras: facturas de proveedores gravadas.
    Retorna: (id, fecha, proveedor, doc_nrc, compra_gravada, iva, total, retencion_iva, es_retencion_practicada)
    - compra_gravada = total/1.13
    - iva = total - compra_gravada
    - es_retencion_practicada: True si la empresa retuvo (empresa Grande, proveedor no); False si el proveedor retuvo.
    """
    try:
        cur.execute(
            """
            SELECT c.id, TO_CHAR(c.fecha, 'DD/MM/YYYY'),
                   COALESCE(p.nombre, '—'),
                   COALESCE(p.nrc, p.nit, '—'),
                   ROUND(COALESCE(c.total, 0) / 1.13, 2),
                   ROUND(COALESCE(c.total, 0) - (COALESCE(c.total, 0) / 1.13), 2),
                   COALESCE(c.total, 0),
                   COALESCE(c.retencion_iva, 0),
                   (e.es_gran_contribuyente = TRUE AND COALESCE(p.es_gran_contribuyente, FALSE) = FALSE)
            FROM compras c
            LEFT JOIN proveedores p ON p.id = c.proveedor_id
            LEFT JOIN empresas e ON e.id = c.empresa_id
            WHERE c.empresa_id = %s
              AND c.fecha::date BETWEEN %s AND %s
            ORDER BY c.fecha, c.id
            """,
            (empresa_id, fecha_inicio, fecha_fin),
        )
        return cur.fetchall() or []
    except Exception:
        cur.connection.rollback()
        try:
            cur.execute(
                """
                SELECT c.id, TO_CHAR(c.fecha, 'DD/MM/YYYY'),
                       COALESCE(p.nombre, '—'),
                       COALESCE(p.nrc, p.nit, '—'),
                       ROUND(COALESCE(c.total, 0) / 1.13, 2),
                       ROUND(COALESCE(c.total, 0) - (COALESCE(c.total, 0) / 1.13), 2),
                       COALESCE(c.total, 0),
                       0,
                       FALSE
                FROM compras c
                LEFT JOIN proveedores p ON p.id = c.proveedor_id
                WHERE c.empresa_id = %s
                  AND c.fecha::date BETWEEN %s AND %s
                ORDER BY c.fecha, c.id
                """,
                (empresa_id, fecha_inicio, fecha_fin),
            )
            return cur.fetchall() or []
        except Exception:
            return []
