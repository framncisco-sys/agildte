# Programador: Oscar Amaya Romero
"""Repositorio para historial de actividad de usuarios (logins, logouts, etc.)."""
from __future__ import annotations

import uuid


# Eventos predefinidos — Sesión
EVENTO_LOGIN_OK = "LOGIN"
EVENTO_LOGIN_FALLO = "LOGIN_FALLO"
EVENTO_LOGOUT = "LOGOUT"
EVENTO_CAMBIO_PASSWORD = "CAMBIO_PASSWORD"

# Eventos — Acciones del sistema
EVENTO_VENTA_CREADA = "VENTA_CREADA"
EVENTO_VENTA_ANULADA = "VENTA_ANULADA"
EVENTO_VENTA_EDITADA = "VENTA_EDITADA"
EVENTO_PRODUCTO_CREADO = "PRODUCTO_CREADO"
EVENTO_PRODUCTO_EDITADO = "PRODUCTO_EDITADO"
EVENTO_PRODUCTO_ELIMINADO = "PRODUCTO_ELIMINADO"
EVENTO_AJUSTE_INVENTARIO = "AJUSTE_INVENTARIO"
EVENTO_CONTEO_FISICO = "CONTEO_FISICO"
EVENTO_CLIENTE_CREADO = "CLIENTE_CREADO"
EVENTO_CLIENTE_EDITADO = "CLIENTE_EDITADO"
EVENTO_CLIENTE_ELIMINADO = "CLIENTE_ELIMINADO"
EVENTO_COMPRA_REGISTRADA = "COMPRA_REGISTRADA"
EVENTO_PROVEEDOR_GUARDADO = "PROVEEDOR_GUARDADO"
EVENTO_PROVEEDOR_ELIMINADO = "PROVEEDOR_ELIMINADO"
EVENTO_USUARIO_CREADO = "USUARIO_CREADO"
EVENTO_USUARIO_EDITADO = "USUARIO_EDITADO"
EVENTO_USUARIO_ELIMINADO = "USUARIO_ELIMINADO"
EVENTO_PROMOCION_CREADA = "PROMOCION_CREADA"
EVENTO_PROMOCION_EDITADA = "PROMOCION_EDITADA"
EVENTO_PROMOCION_ELIMINADA = "PROMOCION_ELIMINADA"
EVENTO_SUCURSAL_CREADA = "SUCURSAL_CREADA"
EVENTO_SUCURSAL_EDITADA = "SUCURSAL_EDITADA"
EVENTO_SUCURSAL_ELIMINADA = "SUCURSAL_ELIMINADA"
EVENTO_CONFIG_EMPRESA = "CONFIG_EMPRESA"


def registrar(
    cur,
    evento: str,
    usuario_id: int | None = None,
    username: str | None = None,
    detalle: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Registra un evento en el historial de usuarios."""
    uname = (username or "")[:100] if username else None
    ev = (evento or "")[:50]

    def _try_insert(full: bool) -> bool:
        sp = "sphu" + uuid.uuid4().hex[:12]
        cur.execute(f"SAVEPOINT {sp}")
        try:
            if full:
                cur.execute(
                    """
                    INSERT INTO historial_usuarios (usuario_id, username, evento, detalle, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        usuario_id,
                        uname,
                        ev,
                        (detalle or "")[:2000] if detalle else None,
                        (ip_address or "")[:45] if ip_address else None,
                        (user_agent or "")[:500] if user_agent else None,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO historial_usuarios (usuario_id, username, evento, detalle)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        usuario_id,
                        uname,
                        ev,
                        (detalle or "")[:500] if detalle else None,
                    ),
                )
            cur.execute(f"RELEASE SAVEPOINT {sp}")
            return True
        except Exception:
            cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
            return False

    if _try_insert(True):
        return
    _try_insert(False)


def listar(
    cur,
    empresa_id: int | None = None,
    usuario_id: int | None = None,
    evento: str | None = None,
    limite: int = 200,
    offset: int = 0,
) -> list:
    """
    Lista registros del historial.
    Retorna: [(id, usuario_id, username, evento, detalle, ip_address, created_at), ...]
    Si empresa_id: solo usuarios de esa empresa + registros sin usuario (logins fallidos).
    """
    condiciones = []
    params = []
    if usuario_id is not None:
        condiciones.append("h.usuario_id = %s")
        params.append(usuario_id)
    if evento:
        condiciones.append("h.evento = %s")
        params.append(evento)
    if empresa_id is not None:
        condiciones.append(
            "(h.usuario_id IS NULL OR h.usuario_id IN (SELECT id FROM usuarios WHERE empresa_id = %s))"
        )
        params.append(empresa_id)
    where = " AND ".join(condiciones) if condiciones else "1=1"
    params.extend([limite, offset])
    try:
        cur.execute(
            f"""
            SELECT h.id, h.usuario_id, COALESCE(h.username, u.username, '—'),
                   h.evento, h.detalle, h.ip_address,
                   TO_CHAR(h.created_at, 'DD/MM/YYYY HH24:MI:SS')
            FROM historial_usuarios h
            LEFT JOIN usuarios u ON u.id = h.usuario_id
            WHERE {where}
            ORDER BY h.created_at DESC
            LIMIT %s OFFSET %s
            """,
            params,
        )
        return cur.fetchall() or []
    except Exception:
        cur.connection.rollback()
        params_simple = [limite, offset]
        if usuario_id is not None:
            cur.execute(
                """
                SELECT id, usuario_id, username, evento, detalle, ip_address,
                       TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI:SS')
                FROM historial_usuarios
                WHERE usuario_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (usuario_id, limite, offset),
            )
        else:
            cur.execute(
                """
                SELECT id, usuario_id, username, evento, detalle, ip_address,
                       TO_CHAR(created_at, 'DD/MM/YYYY HH24:MI:SS')
                FROM historial_usuarios
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limite, offset),
            )
        return cur.fetchall() or []


def tabla_existe(cur) -> bool:
    """Verifica si la tabla historial_usuarios existe."""
    cur.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'historial_usuarios'
        """
    )
    return cur.fetchone() is not None
