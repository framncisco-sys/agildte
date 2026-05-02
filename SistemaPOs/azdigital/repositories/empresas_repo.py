# Programador: Oscar Amaya Romero
from __future__ import annotations

import time
from datetime import date


def _nit_nrc_unicos_vacios(cur) -> tuple[str, str]:
    """Genera NIT y NRC únicos cuando el usuario no los ingresa (evita violar UNIQUE)."""
    ts = int(time.time() * 1000) % 100000000
    nit = f"0614-{ts:06d}-001-4"
    nrc = f"{ts % 1000000:06d}-7"
    cur.execute("SELECT 1 FROM empresas WHERE nit = %s OR nrc = %s", (nit, nrc))
    if cur.fetchone():
        nit = f"0614-{ts:06d}-002-4"
        nrc = f"{(ts + 1) % 1000000:06d}-7"
    return nit, nrc


def get_estado_suscripcion(cur, empresa_id: int = 1):
    cur.execute(
        "SELECT suscripcion_activa, fecha_vencimiento FROM empresas WHERE id = %s",
        (empresa_id,),
    )
    return cur.fetchone()


def get_suscripcion_detalle(cur, empresa_id: int = 1):
    """
    Retorna dict: activa, vencimiento, dias_restantes, vigente.
    - vigente: True si puede usar el sistema (activa y no vencida).
    - dias_restantes: días hasta vencimiento (0 si hoy, negativo si ya venció).
    """
    cur.execute(
        "SELECT suscripcion_activa, fecha_vencimiento FROM empresas WHERE id = %s",
        (empresa_id,),
    )
    row = cur.fetchone()
    if not row:
        return {"activa": False, "vencimiento": None, "dias_restantes": 0, "vigente": False}
    activa = bool(row[0])
    vencimiento = row[1]
    hoy = date.today()
    if vencimiento:
        dias = (vencimiento - hoy).days
    else:
        dias = 999 if activa else 0
    vigente = activa and (vencimiento is None or vencimiento >= hoy)
    return {
        "activa": activa,
        "vencimiento": vencimiento,
        "dias_restantes": dias,
        "vigente": vigente,
    }


def get_empresa(cur, empresa_id: int = 1):
    cur.execute("SELECT * FROM empresas WHERE id = %s", (empresa_id,))
    return cur.fetchone()


def listar_empresas(cur):
    try:
        cur.execute("SELECT id, nombre_comercial FROM empresas ORDER BY nombre_comercial")
        return cur.fetchall()
    except Exception:
        cur.execute("SELECT id, nombre FROM empresas ORDER BY nombre")
        return cur.fetchall()


def listar_empresas_detalle(cur):
    """Retorna (id, nombre, nit, nrc, suscripcion_activa, fecha_vencimiento) para listado."""
    try:
        cur.execute(
            "SELECT id, nombre_comercial, COALESCE(nit,''), COALESCE(nrc,''), "
            "COALESCE(suscripcion_activa,false), fecha_vencimiento "
            "FROM empresas ORDER BY nombre_comercial"
        )
        return cur.fetchall()
    except Exception:
        try:
            cur.execute(
                "SELECT id, nombre, COALESCE(nit,''), COALESCE(nrc,''), "
                "COALESCE(suscripcion_activa,false), fecha_vencimiento "
                "FROM empresas ORDER BY nombre"
            )
            return cur.fetchall()
        except Exception:
            pass
    # Fallback: solo id y nombre
    try:
        cur.execute("SELECT id, nombre_comercial FROM empresas ORDER BY nombre_comercial")
        return [(r[0], r[1], "", "", False, None) for r in cur.fetchall()]
    except Exception:
        try:
            cur.execute("SELECT id, nombre FROM empresas ORDER BY nombre")
            return [(r[0], r[1], "", "", False, None) for r in cur.fetchall()]
        except Exception:
            return []


def crear_empresa(
    cur,
    nombre: str,
    nit: str = "",
    nrc: str = "",
    actividad: str = "",
    direccion: str = "",
    telefono: str = "",
    correo: str = "",
    suscripcion_activa: bool = True,
    fecha_vencimiento=None,
    codigo_actividad_economica: str = "",
) -> int:
    """Crea una nueva empresa. Retorna el id. NIT y NRC tienen UNIQUE en BD."""
    nit_val = (nit or "").strip()
    nrc_val = (nrc or "").strip()
    if not nit_val or not nrc_val:
        nit_gen, nrc_gen = _nit_nrc_unicos_vacios(cur)
        nit_val = nit_val or nit_gen
        nrc_val = nrc_val or nrc_gen
    act_val = (actividad or "").strip() or "Actividad económica"
    giro_val = act_val
    dir_val = (direccion or "").strip() or None
    tel_val = (telefono or "").strip() or None
    cor_val = (correo or "").strip() or None
    cod_act = (codigo_actividad_economica or "").strip() or None

    try:
        sql = """INSERT INTO empresas (nombre_comercial, nit, nrc, actividad_economica, giro, direccion, telefono, correo, suscripcion_activa, fecha_vencimiento, codigo_actividad_economica)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""
        cur.execute(sql, (nombre, nit_val, nrc_val, act_val, giro_val, dir_val, tel_val, cor_val, bool(suscripcion_activa), fecha_vencimiento, cod_act))
    except Exception:
        cur.connection.rollback()
        sql = """INSERT INTO empresas (nombre_comercial, nit, nrc, actividad_economica, giro, direccion, telefono, correo, suscripcion_activa, fecha_vencimiento)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""
        cur.execute(sql, (nombre, nit_val, nrc_val, act_val, giro_val, dir_val, tel_val, cor_val, bool(suscripcion_activa), fecha_vencimiento))
    return cur.fetchone()[0]

def get_empresa_es_gran_contribuyente(cur, empresa_id: int = 1) -> bool:
    """Retorna True si la empresa es Gran Contribuyente (para retención IVA 1%)."""
    try:
        cur.execute("SELECT COALESCE(es_gran_contribuyente, FALSE) FROM empresas WHERE id = %s", (empresa_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else False
    except Exception:
        return False


def actualizar_empresa(
    cur,
    empresa_id: int,
    nombre: str,
    nit: str,
    nrc: str,
    actividad: str,
    direccion: str,
    telefono: str,
    correo: str,
    suscripcion_activa: bool,
    fecha_vencimiento,
    codigo_actividad_economica: str = "",
    es_gran_contribuyente: bool = False,
):
    cod_act = (codigo_actividad_economica or "").strip() or None
    try:
        cur.execute(
            """
            UPDATE empresas SET
                nombre_comercial = %s, nit = %s, nrc = %s,
                actividad_economica = %s, direccion = %s, telefono = %s, correo = %s,
                suscripcion_activa = %s, fecha_vencimiento = %s,
                codigo_actividad_economica = %s, es_gran_contribuyente = %s
            WHERE id = %s
            """,
            (nombre, nit, nrc, actividad, direccion, telefono, correo,
             suscripcion_activa, fecha_vencimiento, cod_act, es_gran_contribuyente, empresa_id),
        )
    except Exception:
        cur.connection.rollback()
        cur.execute(
            """
            UPDATE empresas SET
                nombre_comercial = %s, nit = %s, nrc = %s,
                actividad_economica = %s, direccion = %s, telefono = %s, correo = %s,
                suscripcion_activa = %s, fecha_vencimiento = %s
            WHERE id = %s
            """,
            (nombre, nit, nrc, actividad, direccion, telefono, correo,
             suscripcion_activa, fecha_vencimiento, empresa_id),
        )

