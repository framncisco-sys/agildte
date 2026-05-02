# Programador: Oscar Amaya Romero
from __future__ import annotations

import uuid

from psycopg2 import errors as pg_errors

TABLA_STOCK = "producto_stock_sucursal"
TABLA_KARDEX = "inventario_kardex"

# Clasificación de pérdidas / ajustes (conteo físico, cierre de pesaje)
MOTIVO_MERMA_OPERATIVA = "MERMA_OPERATIVA"
MOTIVO_AVERIA = "AVERIA"
MOTIVO_FALTANTE = "FALTANTE"
MOTIVO_AJUSTE_INVENTARIO = "AJUSTE_INVENTARIO"
MOTIVO_SOBRANTE_CONTEO = "SOBRANTE_CONTEO"
MOTIVOS_AJUSTE_SALIDA = (
    MOTIVO_MERMA_OPERATIVA,
    MOTIVO_AVERIA,
    MOTIVO_FALTANTE,
    MOTIVO_AJUSTE_INVENTARIO,
)

# Seguridad: ajustes grandes requieren supervisor (si el rol no es gerente/admin)
UMBRAL_IMPACTO_AJUSTE_USD = 10.0
UMBRAL_CANTIDAD_AJUSTE_UMB = 5.0
MIN_CARACTERES_JUSTIFICACION_AJUSTE = 10


def etiqueta_motivo_ajuste(cod: str | None) -> str:
    if not cod:
        return "—"
    m = {
        MOTIVO_MERMA_OPERATIVA: "Merma natural / operativa",
        MOTIVO_AVERIA: "Avería o daño",
        MOTIVO_FALTANTE: "Faltante / no justificado",
        MOTIVO_AJUSTE_INVENTARIO: "Ajuste de inventario (cuadre / conteo)",
        MOTIVO_SOBRANTE_CONTEO: "Sobrante (conteo)",
    }
    return m.get(str(cod).strip().upper(), str(cod))


def tabla_existe(cur, nombre: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s",
        (nombre,),
    )
    return cur.fetchone() is not None


def primera_sucursal_empresa(cur, empresa_id: int) -> int | None:
    cur.execute("SELECT MIN(id) FROM sucursales WHERE empresa_id = %s", (empresa_id,))
    r = cur.fetchone()
    return int(r[0]) if r and r[0] is not None else None


def reemplazar_stock_unificado(cur, producto_id: int, sucursal_id: int | None, cantidad: float, registrar_entrada: bool = False) -> None:
    """Una sola fila de stock por producto (tras guardar producto en modal)."""
    if not tabla_existe(cur, TABLA_STOCK):
        return
    cur.execute("SELECT empresa_id FROM productos WHERE id = %s", (producto_id,))
    r = cur.fetchone()
    if not r:
        return
    emp = int(r[0])
    sid = sucursal_id
    if sid is None:
        sid = primera_sucursal_empresa(cur, emp)
    if sid is None:
        return
    cur.execute("SELECT 1 FROM producto_stock_sucursal WHERE producto_id = %s LIMIT 1", (producto_id,))
    tenia_stock = cur.fetchone() is not None
    cur.execute("DELETE FROM producto_stock_sucursal WHERE producto_id = %s", (producto_id,))
    cur.execute(
        "INSERT INTO producto_stock_sucursal (producto_id, sucursal_id, cantidad) VALUES (%s, %s, %s)",
        (producto_id, sid, cantidad),
    )
    cur.execute("UPDATE productos SET stock_actual = %s WHERE id = %s", (cantidad, producto_id))
    if (registrar_entrada or not tenia_stock) and cantidad and float(cantidad) > 0:
        insertar_kardex(cur, emp, producto_id, "ENTRADA", float(cantidad), sid, None, None, "Stock inicial al crear producto", None)


def producto_usa_tabla_sucursal(cur, producto_id: int) -> bool:
    if not tabla_existe(cur, TABLA_STOCK):
        return False
    cur.execute("SELECT 1 FROM producto_stock_sucursal WHERE producto_id = %s LIMIT 1", (producto_id,))
    return cur.fetchone() is not None


def sincronizar_stock_total_producto(cur, producto_id: int) -> None:
    if not tabla_existe(cur, TABLA_STOCK):
        return
    cur.execute(
        "SELECT COALESCE(SUM(cantidad), 0) FROM producto_stock_sucursal WHERE producto_id = %s",
        (producto_id,),
    )
    total = float(cur.fetchone()[0] or 0)
    cur.execute("UPDATE productos SET stock_actual = %s WHERE id = %s", (total, producto_id))


def stock_total_en_tabla(cur, producto_id: int) -> float:
    if not tabla_existe(cur, TABLA_STOCK):
        return 0.0
    cur.execute(
        "SELECT COALESCE(SUM(cantidad), 0) FROM producto_stock_sucursal WHERE producto_id = %s",
        (producto_id,),
    )
    return float(cur.fetchone()[0] or 0)


def listar_stock_por_sucursal(cur, producto_id: int) -> list[tuple]:
    if not tabla_existe(cur, TABLA_STOCK):
        return []
    cur.execute(
        """
        SELECT s.id, s.nombre, COALESCE(pss.cantidad, 0)
        FROM producto_stock_sucursal pss
        JOIN sucursales s ON s.id = pss.sucursal_id
        WHERE pss.producto_id = %s
        ORDER BY s.nombre
        """,
        (producto_id,),
    )
    return cur.fetchall() or []


def descontar_solo_sucursal(cur, producto_id: int, sucursal_id: int, cantidad: float) -> bool:
    """Descuenta solo de una sucursal (salida manual y traslado)."""
    cur.execute(
        """
        SELECT cantidad FROM producto_stock_sucursal
        WHERE producto_id = %s AND sucursal_id = %s FOR UPDATE
        """,
        (producto_id, sucursal_id),
    )
    r = cur.fetchone()
    if not r or float(r[0] or 0) < float(cantidad):
        return False
    cur.execute(
        """
        UPDATE producto_stock_sucursal SET cantidad = cantidad - %s
        WHERE producto_id = %s AND sucursal_id = %s
        """,
        (cantidad, producto_id, sucursal_id),
    )
    sincronizar_stock_total_producto(cur, producto_id)
    return True


def descontar_stock_sucursal(cur, producto_id: int, cantidad: float, sucursal_id: int | None) -> bool:
    """Descuenta cantidad; prioriza sucursal del usuario. True si hubo stock suficiente en total."""
    cur.execute(
        "SELECT sucursal_id, cantidad FROM producto_stock_sucursal WHERE producto_id = %s ORDER BY sucursal_id FOR UPDATE",
        (producto_id,),
    )
    rows = [(int(a), float(b or 0)) for a, b in cur.fetchall()]
    if not rows:
        return False
    total = sum(c for _, c in rows)
    if total < float(cantidad):
        return False
    restante = float(cantidad)
    orden = []
    if sucursal_id is not None:
        for sid, c in rows:
            if sid == int(sucursal_id):
                orden.append((sid, c))
        for sid, c in rows:
            if sid != int(sucursal_id):
                orden.append((sid, c))
    else:
        orden = list(rows)
    for sid, c in orden:
        if restante <= 0:
            break
        tomar = min(c, restante)
        if tomar <= 0:
            continue
        cur.execute(
            """
            UPDATE producto_stock_sucursal SET cantidad = cantidad - %s
            WHERE producto_id = %s AND sucursal_id = %s
            """,
            (tomar, producto_id, sid),
        )
        restante -= tomar
    if restante > 0.000001:
        return False
    sincronizar_stock_total_producto(cur, producto_id)
    return True


def _costo_snapshot_producto(cur, producto_id: int) -> float | None:
    cur.execute(
        """
        SELECT COALESCE(NULLIF(costo_unitario, 0), NULLIF(precio_unitario, 0))
        FROM productos WHERE id = %s
        """,
        (producto_id,),
    )
    r = cur.fetchone()
    if not r or r[0] is None:
        return None
    try:
        v = float(r[0])
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def insertar_kardex(
    cur,
    empresa_id: int,
    producto_id: int,
    tipo: str,
    cantidad: float,
    sucursal_id: int | None,
    sucursal_destino_id: int | None,
    usuario_id: int | None,
    notas: str | None,
    referencia: str | None = None,
    *,
    motivo_ajuste: str | None = None,
    costo_unitario: float | None = None,
) -> None:
    if not tabla_existe(cur, TABLA_KARDEX):
        return
    mot = (motivo_ajuste or "").strip().upper() or None
    if mot is not None and len(mot) > 32:
        mot = mot[:32]
    cu = costo_unitario
    if cu is not None:
        try:
            cu = float(cu)
        except (TypeError, ValueError):
            cu = None
        if cu is not None and cu <= 0:
            cu = None
    notas_v = (notas or "").strip() or None
    sp = "spik" + uuid.uuid4().hex[:12]
    cur.execute(f"SAVEPOINT {sp}")
    try:
        cur.execute(
            """
            INSERT INTO inventario_kardex
                (empresa_id, producto_id, tipo, cantidad, sucursal_id, sucursal_destino_id, referencia, notas, usuario_id, motivo_ajuste, costo_unitario)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                empresa_id,
                producto_id,
                tipo.upper(),
                cantidad,
                sucursal_id,
                sucursal_destino_id,
                referencia,
                notas_v,
                usuario_id,
                mot,
                cu,
            ),
        )
        cur.execute(f"RELEASE SAVEPOINT {sp}")
    except Exception:
        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        cur.execute(
            """
            INSERT INTO inventario_kardex
                (empresa_id, producto_id, tipo, cantidad, sucursal_id, sucursal_destino_id, referencia, notas, usuario_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                empresa_id,
                producto_id,
                tipo.upper(),
                cantidad,
                sucursal_id,
                sucursal_destino_id,
                referencia,
                notas_v,
                usuario_id,
            ),
        )


def listar_kardex_producto(cur, producto_id: int, limit: int = 200) -> list[tuple]:
    if not tabla_existe(cur, TABLA_KARDEX):
        return []
    sql_full = """
        SELECT k.id, k.tipo, k.cantidad, k.sucursal_id, k.sucursal_destino_id, k.notas, k.creado_en,
               COALESCE(u.username, ''), COALESCE(so.nombre, ''), COALESCE(sd.nombre, ''),
               COALESCE(k.motivo_ajuste, '')
        FROM inventario_kardex k
        LEFT JOIN usuarios u ON u.id = k.usuario_id
        LEFT JOIN sucursales so ON so.id = k.sucursal_id
        LEFT JOIN sucursales sd ON sd.id = k.sucursal_destino_id
        WHERE k.producto_id = %s
        ORDER BY k.creado_en DESC, k.id DESC
        LIMIT %s
    """
    sql_sin_motivo = """
        SELECT k.id, k.tipo, k.cantidad, k.sucursal_id, k.sucursal_destino_id, k.notas, k.creado_en,
               COALESCE(u.username, ''), COALESCE(so.nombre, ''), COALESCE(sd.nombre, ''),
               ''::text
        FROM inventario_kardex k
        LEFT JOIN usuarios u ON u.id = k.usuario_id
        LEFT JOIN sucursales so ON so.id = k.sucursal_id
        LEFT JOIN sucursales sd ON sd.id = k.sucursal_destino_id
        WHERE k.producto_id = %s
        ORDER BY k.creado_en DESC, k.id DESC
        LIMIT %s
    """
    params = (producto_id, limit)
    sp = "sp_lkp" + uuid.uuid4().hex[:12]
    cur.execute(f"SAVEPOINT {sp}")
    try:
        cur.execute(sql_full, params)
        rows = cur.fetchall() or []
        cur.execute(f"RELEASE SAVEPOINT {sp}")
        return rows
    except pg_errors.UndefinedColumn:
        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        cur.execute(sql_sin_motivo, params)
        return cur.fetchall() or []
    except Exception:
        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        raise


def _get_empresa_producto(cur, producto_id: int) -> int | None:
    cur.execute("SELECT empresa_id FROM productos WHERE id = %s", (producto_id,))
    r = cur.fetchone()
    return int(r[0]) if r and r[0] is not None else None


def registrar_entrada(
    cur,
    producto_id: int,
    sucursal_id: int,
    cantidad: float,
    usuario_id: int | None,
    notas: str | None,
) -> None:
    emp = _get_empresa_producto(cur, producto_id)
    if emp is None:
        raise ValueError("Producto no encontrado")
    if not tabla_existe(cur, TABLA_STOCK):
        raise ValueError("Kardex no configurado en base de datos")
    cur.execute(
        """
        INSERT INTO producto_stock_sucursal (producto_id, sucursal_id, cantidad)
        VALUES (%s, %s, %s)
        ON CONFLICT (producto_id, sucursal_id)
        DO UPDATE SET cantidad = producto_stock_sucursal.cantidad + EXCLUDED.cantidad
        """,
        (producto_id, sucursal_id, cantidad),
    )
    sincronizar_stock_total_producto(cur, producto_id)
    insertar_kardex(cur, emp, producto_id, "ENTRADA", cantidad, sucursal_id, None, usuario_id, notas)


def registrar_salida(
    cur,
    producto_id: int,
    sucursal_id: int,
    cantidad: float,
    usuario_id: int | None,
    notas: str | None,
) -> None:
    emp = _get_empresa_producto(cur, producto_id)
    if emp is None:
        raise ValueError("Producto no encontrado")
    if not tabla_existe(cur, TABLA_STOCK):
        raise ValueError("Kardex no configurado en base de datos")
    ok = descontar_solo_sucursal(cur, producto_id, sucursal_id, cantidad)
    if not ok:
        raise ValueError("Stock insuficiente en la sucursal indicada")
    insertar_kardex(cur, emp, producto_id, "SALIDA", cantidad, sucursal_id, None, usuario_id, notas)


def registrar_traslado(
    cur,
    producto_id: int,
    sucursal_origen: int,
    sucursal_destino: int,
    cantidad: float,
    usuario_id: int | None,
    notas: str | None,
) -> None:
    if sucursal_origen == sucursal_destino:
        raise ValueError("Origen y destino deben ser distintos")
    emp = _get_empresa_producto(cur, producto_id)
    if emp is None:
        raise ValueError("Producto no encontrado")
    if not tabla_existe(cur, TABLA_STOCK):
        raise ValueError("Kardex no configurado en base de datos")
    ok = descontar_solo_sucursal(cur, producto_id, sucursal_origen, cantidad)
    if not ok:
        raise ValueError("Stock insuficiente en sucursal origen")
    cur.execute(
        """
        INSERT INTO producto_stock_sucursal (producto_id, sucursal_id, cantidad)
        VALUES (%s, %s, %s)
        ON CONFLICT (producto_id, sucursal_id)
        DO UPDATE SET cantidad = producto_stock_sucursal.cantidad + EXCLUDED.cantidad
        """,
        (producto_id, sucursal_destino, cantidad),
    )
    sincronizar_stock_total_producto(cur, producto_id)
    insertar_kardex(
        cur, emp, producto_id, "TRASLADO", cantidad, sucursal_origen, sucursal_destino, usuario_id, notas
    )


def ajustar_por_conteo_fisico(
    cur,
    producto_id: int,
    stock_sistema: float,
    conteo_fisico: float,
    sucursal_id: int | None,
    usuario_id: int | None,
    referencia: str,
    motivo_ajuste: str | None = None,
    comentario_justificacion: str | None = None,
) -> None:
    """
    Ajusta inventario tras conteo físico. Registra ENTRADA o SALIDA según diferencia.
    referencia: ej. "Conteo físico 20/03/2025"
    motivo_ajuste: obligatorio si hay faltante (salida); MERMA_OPERATIVA, AVERIA, FALTANTE, AJUSTE_INVENTARIO.
    Si hay sobrante (entrada), se usa SOBRANTE_CONTEO si no se indica otro.
    comentario_justificacion: texto de auditoría (obligatorio vía rutas antes de llamar).
    """
    emp = _get_empresa_producto(cur, producto_id)
    if emp is None:
        raise ValueError("Producto no encontrado")
    diff = float(conteo_fisico) - float(stock_sistema)
    if abs(diff) < 0.0001:
        return
    notas = f"Sistema: {stock_sistema}, Físico: {conteo_fisico}"
    cj = (comentario_justificacion or "").strip()
    if cj:
        notas = f"{notas}. Justificación: {cj[:800]}"
    costo_snap = _costo_snapshot_producto(cur, producto_id)
    mot_raw = (motivo_ajuste or "").strip().upper() or None
    if diff < 0:
        if mot_raw not in MOTIVOS_AJUSTE_SALIDA:
            raise ValueError(
                "Indique el motivo del faltante: merma operativa, avería, faltante o ajuste de inventario."
            )
        mot = mot_raw
    else:
        mot = MOTIVO_SOBRANTE_CONTEO
    if producto_usa_tabla_sucursal(cur, producto_id):
        if not tabla_existe(cur, TABLA_STOCK):
            raise ValueError("Kardex no configurado")
        sid = sucursal_id
        if sid is None:
            cur.execute(
                "SELECT sucursal_id FROM producto_stock_sucursal WHERE producto_id = %s ORDER BY sucursal_id LIMIT 1",
                (producto_id,),
            )
            r = cur.fetchone()
            sid = int(r[0]) if r and r[0] else None
        if sid is None:
            raise ValueError("Producto sin sucursal asignada")
        if diff > 0:
            cur.execute(
                """
                INSERT INTO producto_stock_sucursal (producto_id, sucursal_id, cantidad)
                VALUES (%s, %s, %s)
                ON CONFLICT (producto_id, sucursal_id)
                DO UPDATE SET cantidad = producto_stock_sucursal.cantidad + EXCLUDED.cantidad
                """,
                (producto_id, sid, diff),
            )
            sincronizar_stock_total_producto(cur, producto_id)
            insertar_kardex(
                cur, emp, producto_id, "AJUSTE_ENTRADA", diff, sid, None, usuario_id, notas, referencia,
                motivo_ajuste=mot, costo_unitario=costo_snap,
            )
        else:
            ok = descontar_solo_sucursal(cur, producto_id, sid, abs(diff))
            if not ok:
                raise ValueError(f"Stock insuficiente para ajuste: sistema {stock_sistema}, físico {conteo_fisico}")
            insertar_kardex(
                cur, emp, producto_id, "AJUSTE_SALIDA", abs(diff), sid, None, usuario_id, notas, referencia,
                motivo_ajuste=mot, costo_unitario=costo_snap,
            )
    else:
        if diff > 0:
            cur.execute(
                "UPDATE productos SET stock_actual = COALESCE(stock_actual, 0) + %s WHERE id = %s",
                (diff, producto_id),
            )
            insertar_kardex(
                cur, emp, producto_id, "AJUSTE_ENTRADA", diff, None, None, usuario_id, notas, referencia,
                motivo_ajuste=mot, costo_unitario=costo_snap,
            )
        else:
            cur.execute(
                "SELECT stock_actual FROM productos WHERE id = %s FOR UPDATE",
                (producto_id,),
            )
            r = cur.fetchone()
            actual = float(r[0] or 0) if r else 0
            if actual < abs(diff):
                raise ValueError(f"Stock insuficiente para ajuste: sistema {stock_sistema}, físico {conteo_fisico}")
            cur.execute(
                "UPDATE productos SET stock_actual = stock_actual - %s WHERE id = %s",
                (abs(diff), producto_id),
            )
            insertar_kardex(
                cur, emp, producto_id, "AJUSTE_SALIDA", abs(diff), None, None, usuario_id, notas, referencia,
                motivo_ajuste=mot, costo_unitario=costo_snap,
            )
