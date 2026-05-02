# Programador: Oscar Amaya Romero
from __future__ import annotations


def texto_snapshot_cliente_venta(
    nombre: str | None, numero_documento: str | None, tipo_documento: str | None
) -> str:
    """Texto que se guarda en ventas.cliente_nombre para identificar al comprador en listados e informes."""
    n = (nombre or "").strip()
    if not n:
        n = "Cliente"
    doc = (numero_documento or "").strip()
    td = (tipo_documento or "").strip()
    if doc and td:
        return f"{n} · {td}: {doc}"
    if doc:
        return f"{n} · Doc. {doc}"
    return n


def snapshot_cliente_venta_por_id(cur, cliente_id: int, empresa_id: int) -> str | None:
    cur.execute(
        """
        SELECT nombre_cliente, COALESCE(numero_documento, ''), COALESCE(tipo_documento, '')
        FROM clientes
        WHERE id = %s AND empresa_id = %s
        """,
        (cliente_id, empresa_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    return texto_snapshot_cliente_venta(row[0], row[1], row[2])


def buscar_clientes(cur, q: str, empresa_id: int = 1, limit: int = 15):
    if not q:
        return []
    params = (empresa_id, f"%{q}%", f"%{q}%", f"%{q.replace(' ', '').replace('-', '')}%", limit)
    try:
        cur.execute(
            """
            SELECT id, nombre_cliente, numero_documento, tipo_documento, COALESCE(es_contribuyente, FALSE), COALESCE(es_gran_contribuyente, FALSE), COALESCE(telefono, '')
            FROM clientes
            WHERE empresa_id = %s AND (
                UPPER(nombre_cliente) LIKE %s OR
                UPPER(COALESCE(numero_documento, '')) LIKE %s OR
                REPLACE(REPLACE(COALESCE(numero_documento, ''), '-', ''), ' ', '') LIKE %s
            )
            ORDER BY nombre_cliente
            LIMIT %s
            """,
            params,
        )
        return cur.fetchall()
    except Exception:
        cur.connection.rollback()
        cur.execute(
            """
            SELECT id, nombre_cliente, numero_documento, tipo_documento, COALESCE(es_contribuyente, FALSE), COALESCE(telefono, '')
            FROM clientes
            WHERE empresa_id = %s AND (
                UPPER(nombre_cliente) LIKE %s OR
                UPPER(COALESCE(numero_documento, '')) LIKE %s OR
                REPLACE(REPLACE(COALESCE(numero_documento, ''), '-', ''), ' ', '') LIKE %s
            )
            ORDER BY nombre_cliente
            LIMIT %s
            """,
            params,
        )
        return [(r[0], r[1], r[2], r[3], r[4], False, (r[5] or "").strip()) for r in cur.fetchall()]


def listar_clientes(cur, empresa_id: int = 1):
    try:
        cur.execute(
            """
            SELECT id, nombre_cliente, tipo_documento, numero_documento, correo, es_contribuyente, COALESCE(es_gran_contribuyente, FALSE), direccion, telefono
            FROM clientes
            WHERE empresa_id = %s
            ORDER BY nombre_cliente ASC
            """,
            (empresa_id,),
        )
        return cur.fetchall()
    except Exception:
        cur.connection.rollback()
        cur.execute(
            """
            SELECT id, nombre_cliente, tipo_documento, numero_documento, correo, es_contribuyente, direccion, telefono
            FROM clientes
            WHERE empresa_id = %s
            ORDER BY nombre_cliente ASC
            """,
            (empresa_id,),
        )
        rows = cur.fetchall()
        return [(r[0], r[1], r[2], r[3], r[4], r[5], False, r[6], r[7]) for r in rows] if rows else []


def get_cliente(cur, cliente_id: int):
    """Retorna (id, empresa_id, sucursal_id, nombre_cliente, tipo_documento, numero_documento, correo, es_contribuyente, es_gran_contribuyente, direccion, telefono, codigo_actividad_economica)."""
    try:
        cur.execute(
            """
            SELECT id, empresa_id, nombre_cliente, tipo_documento, numero_documento, correo, es_contribuyente, COALESCE(es_gran_contribuyente, FALSE), direccion, telefono, COALESCE(codigo_actividad_economica, '')
            FROM clientes
            WHERE id = %s
            """,
            (cliente_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return (row[0], row[1], None, row[2], row[3], row[4], row[5], row[6], bool(row[7]), row[8], row[9], row[10])
    except Exception:
        cur.connection.rollback()
        try:
            cur.execute(
                """
                SELECT id, empresa_id, nombre_cliente, tipo_documento, numero_documento, correo, es_contribuyente, direccion, telefono, COALESCE(codigo_actividad_economica, '')
                FROM clientes
                WHERE id = %s
                """,
                (cliente_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return (row[0], row[1], None, row[2], row[3], row[4], row[5], row[6], False, row[7], row[8], row[9] if len(row) > 9 else "")
        except Exception:
            cur.connection.rollback()
            cur.execute(
                """
                SELECT id, empresa_id, nombre_cliente, tipo_documento, numero_documento, correo, es_contribuyente, direccion, telefono
                FROM clientes
                WHERE id = %s
                """,
                (cliente_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return (row[0], row[1], None, row[2], row[3], row[4], row[5], row[6], False, row[7], row[8], "")


def crear_cliente(
    cur,
    empresa_id: int,
    nombre_cliente: str,
    tipo_documento: str,
    numero_documento: str,
    correo: str,
    es_contribuyente: bool,
    direccion: str = "",
    telefono: str = "",
    sucursal_id: int | None = None,
    codigo_actividad_economica: str = "",
    es_gran_contribuyente: bool = False,
) -> int:
    cod_act = (codigo_actividad_economica or "").strip() or None
    try:
        cur.execute(
            """
            INSERT INTO clientes (empresa_id, sucursal_id, nombre_cliente, tipo_documento, numero_documento, correo, es_contribuyente, es_gran_contribuyente, direccion, telefono, codigo_actividad_economica)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (empresa_id, sucursal_id, nombre_cliente, tipo_documento or None, numero_documento or None, correo or None, es_contribuyente, es_gran_contribuyente, direccion or None, telefono or None, cod_act),
        )
    except Exception:
        cur.connection.rollback()
        try:
            cur.execute(
                """
                INSERT INTO clientes (empresa_id, sucursal_id, nombre_cliente, tipo_documento, numero_documento, correo, es_contribuyente, direccion, telefono)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (empresa_id, sucursal_id, nombre_cliente, tipo_documento or None, numero_documento or None, correo or None, es_contribuyente, direccion or None, telefono or None),
            )
        except Exception:
            cur.connection.rollback()
            cur.execute(
                """
                INSERT INTO clientes (empresa_id, nombre_cliente, tipo_documento, numero_documento, correo, es_contribuyente, direccion, telefono)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (empresa_id, nombre_cliente, tipo_documento or None, numero_documento or None, correo or None, es_contribuyente, direccion or None, telefono or None),
            )
    return int(cur.fetchone()[0])


def actualizar_cliente(
    cur,
    cliente_id: int,
    nombre_cliente: str,
    tipo_documento: str,
    numero_documento: str,
    correo: str,
    es_contribuyente: bool,
    direccion: str = "",
    telefono: str = "",
    empresa_id: int | None = None,
    sucursal_id: int | None = None,
    actualizar_sucursal: bool = False,
    codigo_actividad_economica: str = "",
    es_gran_contribuyente: bool = False,
) -> None:
    set_extra = ["codigo_actividad_economica = %s", "es_gran_contribuyente = %s"]
    cod_act = (codigo_actividad_economica or "").strip() or None
    vals = [nombre_cliente, tipo_documento or None, numero_documento or None, correo or None, es_contribuyente, direccion or None, telefono or None, cod_act, es_gran_contribuyente]
    if empresa_id is not None:
        set_extra.append("empresa_id = %s")
        vals.append(empresa_id)
    if actualizar_sucursal:
        set_extra.append("sucursal_id = %s")
        vals.append(sucursal_id)
    vals.append(cliente_id)
    extra_sql = ", ".join(set_extra)
    sep = ", " + extra_sql if extra_sql else ""
    try:
        cur.execute(
            f"""
            UPDATE clientes
            SET nombre_cliente = %s, tipo_documento = %s, numero_documento = %s, correo = %s, es_contribuyente = %s, direccion = %s, telefono = %s{sep}
            WHERE id = %s
            """,
            tuple(vals),
        )
    except Exception:
        cur.connection.rollback()
        try:
            set_extra = ["codigo_actividad_economica = %s"]
            vals = [nombre_cliente, tipo_documento or None, numero_documento or None, correo or None, es_contribuyente, direccion or None, telefono or None, cod_act]
            if empresa_id is not None:
                set_extra.append("empresa_id = %s")
                vals.append(empresa_id)
            if actualizar_sucursal:
                set_extra.append("sucursal_id = %s")
                vals.append(sucursal_id)
            vals.append(cliente_id)
            extra_sql = ", ".join(set_extra)
            sep = ", " + extra_sql if extra_sql else ""
            cur.execute(
                f"""
                UPDATE clientes
                SET nombre_cliente = %s, tipo_documento = %s, numero_documento = %s, correo = %s, es_contribuyente = %s, direccion = %s, telefono = %s{sep}
                WHERE id = %s
                """,
                tuple(vals),
            )
        except Exception:
            cur.connection.rollback()
            set_extra = []
            vals = [nombre_cliente, tipo_documento or None, numero_documento or None, correo or None, es_contribuyente, direccion or None, telefono or None]
            if empresa_id is not None:
                set_extra.append("empresa_id = %s")
                vals.append(empresa_id)
            if actualizar_sucursal:
                set_extra.append("sucursal_id = %s")
                vals.append(sucursal_id)
            vals.append(cliente_id)
            extra_sql = ", ".join(set_extra) if set_extra else ""
            sep = ", " + extra_sql if extra_sql else ""
            cur.execute(
                f"""
                UPDATE clientes
                SET nombre_cliente = %s, tipo_documento = %s, numero_documento = %s, correo = %s, es_contribuyente = %s, direccion = %s, telefono = %s{sep}
                WHERE id = %s
                """,
                tuple(vals),
            )


def eliminar_cliente(cur, cliente_id: int) -> bool:
    cur.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
    return cur.rowcount > 0
