# Programador: Oscar Amaya Romero
from __future__ import annotations

from datetime import date
from typing import Any


def listar_promociones(cur, empresa_id: int | None = None) -> list:
    """Lista promociones con cantidad de productos. empresa_id None = todas (super)."""
    if empresa_id is not None:
        cur.execute(
            """
            SELECT p.id, p.nombre, p.tipo, p.valor, p.fecha_inicio, p.fecha_fin, p.activa,
                   p.cantidad_min_compra,
                   (SELECT COUNT(*) FROM promocion_productos pp WHERE pp.promocion_id = p.id)
            FROM promociones p
            WHERE p.empresa_id = %s
            ORDER BY p.fecha_inicio DESC NULLS LAST, p.id DESC
            """,
            (empresa_id,),
        )
    else:
        cur.execute(
            """
            SELECT p.id, p.nombre, p.tipo, p.valor, p.fecha_inicio, p.fecha_fin, p.activa, p.empresa_id,
                   p.cantidad_min_compra,
                   (SELECT COUNT(*) FROM promocion_productos pp WHERE pp.promocion_id = p.id)
            FROM promociones p
            ORDER BY p.fecha_inicio DESC NULLS LAST, p.id DESC
            """
        )
    return cur.fetchall() or []


def get_promocion(cur, promocion_id: int, empresa_id: int | None = None) -> tuple | None:
    """Retorna (id, empresa_id, nombre, tipo, valor, fecha_inicio, fecha_fin, activa, valor_comprar, valor_pagar, descuento_monto, producto_regalo_id, cantidad_min_compra, cantidad_regalo)."""
    cols = "id, empresa_id, nombre, tipo, valor, fecha_inicio, fecha_fin, COALESCE(activa, TRUE), valor_comprar, valor_pagar, descuento_monto, producto_regalo_id, cantidad_min_compra, cantidad_regalo"
    try:
        if empresa_id is not None:
            cur.execute(
                f"SELECT {cols} FROM promociones WHERE id = %s AND empresa_id = %s",
                (promocion_id, empresa_id),
            )
        else:
            cur.execute(
                f"SELECT {cols} FROM promociones WHERE id = %s",
                (promocion_id,),
            )
        return cur.fetchone()
    except Exception:
        if empresa_id is not None:
            cur.execute(
                "SELECT id, empresa_id, nombre, tipo, valor, fecha_inicio, fecha_fin, COALESCE(activa, TRUE) FROM promociones WHERE id = %s AND empresa_id = %s",
                (promocion_id, empresa_id),
            )
        else:
            cur.execute(
                "SELECT id, empresa_id, nombre, tipo, valor, fecha_inicio, fecha_fin, COALESCE(activa, TRUE) FROM promociones WHERE id = %s",
                (promocion_id,),
            )
        r = cur.fetchone()
        if r and len(r) >= 8:
            return r + (None, None, None, None, 1, 1)
        return r


def get_productos_promocion(cur, promocion_id: int) -> list:
    """Lista producto_id de productos asignados a la promoción."""
    cur.execute(
        "SELECT producto_id FROM promocion_productos WHERE promocion_id = %s",
        (promocion_id,),
    )
    return [r[0] for r in (cur.fetchall() or [])]


TIPOS_VALIDOS = ("2X1", "3X2", "PORCENTAJE", "DESCUENTO_MONTO", "VOLUMEN", "REGALO", "PRECIO_FIJO", "DESCUENTO_CANTIDAD")


def crear_promocion(
    cur,
    empresa_id: int,
    nombre: str,
    tipo: str,
    valor: float,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
    activa: bool = True,
    producto_ids: list[int] | None = None,
    valor_comprar: float | None = None,
    valor_pagar: float | None = None,
    descuento_monto: float | None = None,
    producto_regalo_id: int | None = None,
    cantidad_min_compra: float | None = None,
    cantidad_regalo: float | None = None,
) -> int:
    tipo = (tipo or "").strip().upper()
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo debe ser uno de: {', '.join(TIPOS_VALIDOS)}")
    try:
        cur.execute(
            """
            INSERT INTO promociones (empresa_id, nombre, tipo, valor, fecha_inicio, fecha_fin, activa,
                valor_comprar, valor_pagar, descuento_monto, producto_regalo_id, cantidad_min_compra, cantidad_regalo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (empresa_id, nombre.strip(), tipo, valor, fecha_inicio, fecha_fin, activa,
             valor_comprar, valor_pagar, descuento_monto, producto_regalo_id, cantidad_min_compra, cantidad_regalo),
        )
    except Exception:
        cur.execute(
            """
            INSERT INTO promociones (empresa_id, nombre, tipo, valor, fecha_inicio, fecha_fin, activa)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (empresa_id, nombre.strip(), tipo, valor, fecha_inicio, fecha_fin, activa),
        )
    pid = int(cur.fetchone()[0])
    if producto_ids:
        for prod_id in producto_ids:
            try:
                cur.execute(
                    "INSERT INTO promocion_productos (promocion_id, producto_id) VALUES (%s, %s)",
                    (pid, int(prod_id)),
                )
            except Exception:
                pass
    return pid


def actualizar_promocion(
    cur,
    promocion_id: int,
    nombre: str,
    tipo: str,
    valor: float,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
    activa: bool = True,
    producto_ids: list[int] | None = None,
    empresa_id: int | None = None,
    valor_comprar: float | None = None,
    valor_pagar: float | None = None,
    descuento_monto: float | None = None,
    producto_regalo_id: int | None = None,
    cantidad_min_compra: float | None = None,
    cantidad_regalo: float | None = None,
) -> None:
    tipo = (tipo or "").strip().upper()
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo debe ser uno de: {', '.join(TIPOS_VALIDOS)}")
    sql = """
        UPDATE promociones SET nombre = %s, tipo = %s, valor = %s, fecha_inicio = %s, fecha_fin = %s, activa = %s,
            valor_comprar = %s, valor_pagar = %s, descuento_monto = %s, producto_regalo_id = %s,
            cantidad_min_compra = %s, cantidad_regalo = %s
        WHERE id = %s
    """
    params: list[Any] = [
        nombre.strip(), tipo, valor, fecha_inicio, fecha_fin, activa,
        valor_comprar, valor_pagar, descuento_monto, producto_regalo_id, cantidad_min_compra, cantidad_regalo,
        promocion_id
    ]
    if empresa_id is not None:
        sql = sql.replace("WHERE id = %s", "WHERE id = %s AND empresa_id = %s")
        params.insert(-1, empresa_id)
    cur.execute(sql, tuple(params))
    if producto_ids is not None:
        cur.execute("DELETE FROM promocion_productos WHERE promocion_id = %s", (promocion_id,))
        for prod_id in producto_ids:
            try:
                cur.execute(
                    "INSERT INTO promocion_productos (promocion_id, producto_id) VALUES (%s, %s)",
                    (promocion_id, int(prod_id)),
                )
            except Exception:
                pass


def eliminar_promocion(cur, promocion_id: int, empresa_id: int | None = None) -> bool:
    if empresa_id is not None:
        cur.execute("DELETE FROM promociones WHERE id = %s AND empresa_id = %s", (promocion_id, empresa_id))
    else:
        cur.execute("DELETE FROM promociones WHERE id = %s", (promocion_id,))
    return cur.rowcount > 0


def get_promocion_activa_producto(cur, producto_id: int, empresa_id: int, fecha: date | None = None) -> tuple | None:
    """
    Retorna la promoción activa que aplica al producto en la fecha dada.
    Retorna (tipo, valor, valor_comprar, valor_pagar, descuento_monto, producto_regalo_id, cantidad_min_compra, cantidad_regalo).
    """
    if fecha is None:
        fecha = date.today()
    cur.execute(
        """
        SELECT pr.tipo, pr.valor, COALESCE(pr.valor_comprar, pr.valor, 2), COALESCE(pr.valor_pagar, 1),
               pr.descuento_monto, pr.producto_regalo_id, COALESCE(pr.cantidad_min_compra, 1), COALESCE(pr.cantidad_regalo, 1)
        FROM promociones pr
        JOIN promocion_productos pp ON pp.promocion_id = pr.id
        WHERE pp.producto_id = %s
          AND pr.empresa_id = %s
          AND COALESCE(pr.activa, TRUE) = TRUE
          AND (pr.fecha_inicio IS NULL OR pr.fecha_inicio <= %s)
          AND (pr.fecha_fin IS NULL OR pr.fecha_fin >= %s)
        ORDER BY pr.fecha_inicio DESC NULLS LAST
        LIMIT 1
        """,
        (producto_id, empresa_id, fecha, fecha),
    )
    return cur.fetchone()
