# Programador: Oscar Amaya Romero
from __future__ import annotations


def listar_sucursales(cur, empresa_id: int = None):
    if empresa_id:
        cur.execute(
            "SELECT id, nombre, codigo_hacienda, direccion, telefono FROM sucursales WHERE empresa_id = %s ORDER BY id DESC",
            (empresa_id,),
        )
    else:
        cur.execute("SELECT id, nombre, codigo_hacienda, direccion, telefono FROM sucursales ORDER BY id DESC")
    return cur.fetchall()


def get_sucursal(cur, sucursal_id: int):
    cur.execute(
        "SELECT id, nombre, codigo_hacienda, direccion, telefono, empresa_id FROM sucursales WHERE id = %s",
        (sucursal_id,),
    )
    return cur.fetchone()


def actualizar_sucursal(
    cur,
    sucursal_id: int,
    nombre: str,
    codigo_hacienda: str,
    direccion: str,
    telefono: str,
    empresa_id: int | None = None,
) -> None:
    if empresa_id is not None:
        cur.execute(
            """
            UPDATE sucursales SET nombre = %s, codigo_hacienda = %s, direccion = %s, telefono = %s, empresa_id = %s
            WHERE id = %s
            """,
            (nombre, codigo_hacienda, direccion, telefono, empresa_id, sucursal_id),
        )
        cur.execute("UPDATE usuarios SET empresa_id = %s WHERE sucursal_id = %s", (empresa_id, sucursal_id))
        try:
            cur.execute("UPDATE clientes SET empresa_id = %s WHERE sucursal_id = %s", (empresa_id, sucursal_id))
        except Exception:
            pass
    else:
        cur.execute(
            """
            UPDATE sucursales SET nombre = %s, codigo_hacienda = %s, direccion = %s, telefono = %s
            WHERE id = %s
            """,
            (nombre, codigo_hacienda, direccion, telefono, sucursal_id),
        )


def listar_sucursales_min(cur, empresa_id: int = None):
    if empresa_id:
        cur.execute(
            "SELECT id, nombre FROM sucursales WHERE empresa_id = %s ORDER BY nombre ASC",
            (empresa_id,),
        )
    else:
        cur.execute("SELECT id, nombre FROM sucursales ORDER BY nombre ASC")
    return cur.fetchall()


def listar_sucursales_con_empresa(cur):
    """Retorna (id, nombre, empresa_id) para todas las sucursales. Para superusuario."""
    cur.execute(
        "SELECT id, nombre, empresa_id FROM sucursales ORDER BY empresa_id, nombre ASC"
    )
    return cur.fetchall()


def listar_sucursales_todas_con_empresa(cur):
    """(id, nombre, codigo_hacienda, direccion, telefono, nombre_empresa) — listado global superusuario."""
    try:
        cur.execute(
            """
            SELECT s.id, s.nombre, s.codigo_hacienda, s.direccion, s.telefono,
                   COALESCE(e.nombre_comercial, e.nombre, '—')
            FROM sucursales s
            LEFT JOIN empresas e ON e.id = s.empresa_id
            ORDER BY COALESCE(e.nombre_comercial, e.nombre, ''), s.nombre
            """
        )
        return cur.fetchall()
    except Exception:
        cur.execute(
            """
            SELECT s.id, s.nombre, s.codigo_hacienda, s.direccion, s.telefono, COALESCE(e.nombre, '—')
            FROM sucursales s
            LEFT JOIN empresas e ON e.id = s.empresa_id
            ORDER BY e.nombre, s.nombre
            """
        )
        return cur.fetchall()


def crear_sucursal(cur, nombre: str, codigo_hacienda: str, direccion: str, telefono: str, empresa_id: int = 1):
    cur.execute(
        """
        INSERT INTO sucursales (nombre, codigo_hacienda, direccion, telefono, empresa_id)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (nombre, codigo_hacienda, direccion, telefono, empresa_id),
    )


def eliminar_sucursal(cur, sucursal_id: int) -> bool:
    cur.execute("UPDATE usuarios SET sucursal_id = NULL WHERE sucursal_id = %s", (sucursal_id,))
    cur.execute("DELETE FROM sucursales WHERE id = %s", (sucursal_id,))
    return cur.rowcount > 0

