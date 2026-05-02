# Programador: Oscar Amaya Romero
"""Repositorio de proveedores."""

from __future__ import annotations


def listar(cur, empresa_id: int, incluir_inactivos: bool = False) -> list[tuple]:
    """Lista proveedores: (id, nombre, nit, telefono, contacto, activo, nrc, clasificacion, es_gran_contribuyente)."""
    q = """SELECT id, nombre, COALESCE(nit, ''), COALESCE(telefono, ''), COALESCE(contacto, ''), COALESCE(activo, TRUE),
            COALESCE(nrc, ''), COALESCE(clasificacion_contribuyente, 'PEQUEÑO'), COALESCE(es_gran_contribuyente, FALSE)
            FROM proveedores WHERE empresa_id = %s"""
    if not incluir_inactivos:
        q += " AND COALESCE(activo, TRUE) = TRUE"
    q += " ORDER BY nombre"
    cur.execute(q, (empresa_id,))
    return cur.fetchall() or []


def buscar_por_nit(cur, nit: str, empresa_id: int) -> tuple | None:
    """Busca proveedor por NIT (solo dígitos, sin guiones). Retorna mismo formato que get."""
    from azdigital.utils.validar_documentos import extraer_digitos
    digitos = extraer_digitos(nit)
    if not digitos:
        return None
    cur.execute(
        """SELECT id, empresa_id, nombre, COALESCE(nit, ''), COALESCE(nrc, ''), COALESCE(direccion, ''), COALESCE(telefono, ''), COALESCE(correo, ''),
            COALESCE(contacto, ''), COALESCE(activo, TRUE), COALESCE(tipo_documento, 'NIT'), COALESCE(giro_actividad, ''),
            COALESCE(clasificacion_contribuyente, 'PEQUEÑO'), COALESCE(es_gran_contribuyente, FALSE)
            FROM proveedores WHERE empresa_id = %s AND REPLACE(REPLACE(nit, '-', ''), ' ', '') = %s LIMIT 1""",
        (empresa_id, digitos),
    )
    return cur.fetchone()


def get(cur, proveedor_id: int, empresa_id: int) -> tuple | None:
    """Obtiene proveedor: (id, empresa_id, nombre, nit, nrc, direccion, telefono, correo, contacto, activo, tipo_documento, giro_actividad, clasificacion_contribuyente, es_gran_contribuyente)."""
    cur.execute(
        """SELECT id, empresa_id, nombre, COALESCE(nit, ''), COALESCE(nrc, ''), COALESCE(direccion, ''), COALESCE(telefono, ''), COALESCE(correo, ''),
            COALESCE(contacto, ''), COALESCE(activo, TRUE), COALESCE(tipo_documento, 'NIT'), COALESCE(giro_actividad, ''),
            COALESCE(clasificacion_contribuyente, 'PEQUEÑO'), COALESCE(es_gran_contribuyente, FALSE)
            FROM proveedores WHERE id = %s AND empresa_id = %s""",
        (proveedor_id, empresa_id),
    )
    return cur.fetchone()


def crear(
    cur,
    empresa_id: int,
    nombre: str,
    nit: str = "",
    nrc: str = "",
    direccion: str = "",
    telefono: str = "",
    correo: str = "",
    contacto: str = "",
    tipo_documento: str = "NIT",
    giro_actividad: str = "",
    clasificacion_contribuyente: str = "PEQUEÑO",
    es_gran_contribuyente: bool = False,
) -> int:
    """Crea proveedor. Retorna id."""
    tc = (tipo_documento or "NIT").strip().upper() or "NIT"
    if tc not in ("NIT", "DUI"):
        tc = "NIT"
    cla = (clasificacion_contribuyente or "PEQUEÑO").strip().upper() or "PEQUEÑO"
    if cla not in ("GRANDE", "MEDIANO", "PEQUEÑO"):
        cla = "PEQUEÑO"
    gran = es_gran_contribuyente or (cla == "GRANDE")
    cur.execute(
        """
        INSERT INTO proveedores (empresa_id, nombre, nit, nrc, direccion, telefono, correo, contacto,
            tipo_documento, giro_actividad, clasificacion_contribuyente, es_gran_contribuyente)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """,
        (empresa_id, nombre.strip(), nit.strip(), nrc.strip(), direccion.strip(), telefono.strip(),
         correo.strip(), contacto.strip(), tc, (giro_actividad or "").strip(), cla, gran),
    )
    return int(cur.fetchone()[0])


def actualizar(
    cur,
    proveedor_id: int,
    empresa_id: int,
    nombre: str,
    nit: str = "",
    nrc: str = "",
    direccion: str = "",
    telefono: str = "",
    correo: str = "",
    contacto: str = "",
    activo: bool = True,
    tipo_documento: str = "NIT",
    giro_actividad: str = "",
    clasificacion_contribuyente: str = "PEQUEÑO",
    es_gran_contribuyente: bool = False,
) -> bool:
    """Actualiza proveedor."""
    tc = (tipo_documento or "NIT").strip().upper() or "NIT"
    if tc not in ("NIT", "DUI"):
        tc = "NIT"
    cla = (clasificacion_contribuyente or "PEQUEÑO").strip().upper() or "PEQUEÑO"
    if cla not in ("GRANDE", "MEDIANO", "PEQUEÑO"):
        cla = "PEQUEÑO"
    gran = es_gran_contribuyente or (cla == "GRANDE")
    cur.execute(
        """
        UPDATE proveedores SET nombre = %s, nit = %s, nrc = %s, direccion = %s, telefono = %s, correo = %s, contacto = %s, activo = %s,
            tipo_documento = %s, giro_actividad = %s, clasificacion_contribuyente = %s, es_gran_contribuyente = %s
        WHERE id = %s AND empresa_id = %s
        """,
        (nombre.strip(), nit.strip(), nrc.strip(), direccion.strip(), telefono.strip(), correo.strip(),
         contacto.strip(), activo, tc, (giro_actividad or "").strip(), cla, gran, proveedor_id, empresa_id),
    )
    return cur.rowcount > 0


def eliminar(cur, proveedor_id: int, empresa_id: int) -> bool:
    """Elimina proveedor (o marca inactivo si tiene compras)."""
    cur.execute("SELECT 1 FROM compras WHERE proveedor_id = %s LIMIT 1", (proveedor_id,))
    if cur.fetchone():
        cur.execute("UPDATE proveedores SET activo = FALSE WHERE id = %s AND empresa_id = %s", (proveedor_id, empresa_id))
        return cur.rowcount > 0
    cur.execute("DELETE FROM proveedores WHERE id = %s AND empresa_id = %s", (proveedor_id, empresa_id))
    return cur.rowcount > 0
