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


def es_suscripcion_vigente(activa: bool, vencimiento, hoy: date | None = None) -> bool:
    """
    Vigencia para usar el POS:
    - Si hay fecha_vencimiento, manda la fecha (futura = vigente aunque el switch esté apagado).
    - Sin fecha, depende del switch suscripcion_activa.
    """
    from azdigital.utils.fecha_sv import hoy_sv

    hoy = hoy if hoy is not None else hoy_sv()
    if vencimiento is not None:
        try:
            return vencimiento >= hoy
        except TypeError:
            return bool(activa)
    return bool(activa)


def get_suscripcion_detalle(cur, empresa_id: int = 1):
    """
    Retorna dict: activa, vencimiento, dias_restantes, vigente.
    - vigente: True si puede usar el sistema (fecha futura o switch activo sin fecha).
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
    from azdigital.utils.fecha_sv import hoy_sv

    hoy = hoy_sv()
    if vencimiento:
        dias = (vencimiento - hoy).days
    else:
        dias = 999 if activa else 0
    vigente = es_suscripcion_vigente(activa, vencimiento, hoy)
    return {
        "activa": activa,
        "vencimiento": vencimiento,
        "dias_restantes": dias,
        "vigente": vigente,
    }


def get_empresa(cur, empresa_id: int = 1):
    cur.execute("SELECT * FROM empresas WHERE id = %s", (empresa_id,))
    return cur.fetchone()


def empresa_row_a_vista(row: tuple | None) -> dict | None:
    """Mapea fila SELECT * de empresas a dict para plantillas (índices fijos del esquema POS)."""
    if not row:
        return None
    n = len(row)

    def _g(i: int, default=""):
        if n <= i or row[i] is None:
            return default
        return row[i]

    return {
        "id": row[0],
        "nombre_comercial": _g(1),
        "nombre": _g(2),
        "nit": _g(3),
        "nrc": _g(4),
        "actividad_economica": _g(5),
        "giro": _g(6),
        "direccion": _g(7),
        "telefono": _g(8),
        "correo": _g(9),
        "suscripcion_activa": bool(row[10]) if n > 10 else False,
        "fecha_vencimiento": row[11] if n > 11 else None,
        "codigo_actividad_economica": (_g(12) or "").strip() if n > 12 else "",
        "es_gran_contribuyente": bool(row[13]) if n > 13 else False,
    }


def _es_mascara_vacia(valor) -> bool:
    """Detecta restos de IMask (____-____) guardados por error en BD."""
    s = str(valor or "").strip()
    if not s:
        return True
    solo_guiones = s.replace("-", "").replace("_", "").replace(" ", "")
    return not solo_guiones


def _es_placeholder_empresa(campo: str, valor) -> bool:
    """Valores locales que no deben bloquear datos reales de AgilDTE."""
    if valor is None:
        return True
    if _es_mascara_vacia(valor):
        return True
    s = str(valor).strip()
    if not s:
        return True
    bajo = s.lower()
    if campo == "correo" and bajo in ("correo@empresa.com", "correo@empresa.com", "@"):
        return True
    if campo in ("direccion", "actividad_economica", "giro", "nombre") and bajo in (
        "general",
        "sin nombre",
        "n/a",
        "na",
    ):
        return True
    if campo == "nrc" and s.startswith("0614") and len("".join(c for c in s if c.isdigit())) <= 10:
        return True
    return False


def agildte_empresa_a_vista(agildte: dict) -> dict:
    """Normaliza JSON GET /api/empresas/{id}/ al formato del formulario POS."""
    if not agildte:
        return {}
    cod = str(agildte.get("cod_actividad") or agildte.get("codigo_actividad_economica") or "").strip()
    desc = str(agildte.get("desc_actividad") or agildte.get("actividad_economica") or "").strip()
    correo = str(agildte.get("correo") or agildte.get("email_lectura") or "").strip()
    return {
        "nombre_comercial": str(agildte.get("nombre") or agildte.get("nombre_comercial") or "").strip(),
        "nit": str(agildte.get("nit") or "").strip(),
        "nrc": str(agildte.get("nrc") or "").strip(),
        "direccion": str(agildte.get("direccion") or "").strip(),
        "telefono": str(agildte.get("telefono") or "").strip(),
        "correo": correo,
        "codigo_actividad_economica": cod,
        "actividad_economica": desc,
    }


def limpiar_valor_formulario(campo: str, valor: str) -> str:
    """Quita máscaras/placeholders antes de guardar en BD."""
    s = str(valor or "").strip()
    return "" if _es_placeholder_empresa(campo, s) else s


def sanitizar_empresa_vista(vista: dict | None) -> dict:
    """Limpia máscaras y placeholders en datos locales antes de mostrar o fusionar."""
    if not vista:
        return {}
    out = dict(vista)
    for campo in ("nit", "nrc", "telefono", "correo", "direccion", "actividad_economica", "giro", "nombre_comercial"):
        if campo in out and _es_placeholder_empresa(campo, out.get(campo)):
            out[campo] = ""
    return out


def combinar_empresa_con_agildte(local: dict | None, agildte: dict | None) -> dict:
    """
    Fusiona POS + AgilDTE para el formulario.
    Si hay respuesta de AgilDTE, sus campos tienen prioridad cuando el local está vacío o es placeholder.
    """
    base = sanitizar_empresa_vista(local)
    if not agildte:
        return base
    remoto = agildte_empresa_a_vista(agildte)
    campos = (
        "nombre_comercial",
        "nit",
        "nrc",
        "direccion",
        "telefono",
        "correo",
        "codigo_actividad_economica",
        "actividad_economica",
    )
    for campo in campos:
        valor_remoto = (remoto.get(campo) or "").strip()
        if not valor_remoto:
            continue
        if _es_placeholder_empresa(campo, base.get(campo)) or not (base.get(campo) or "").strip():
            base[campo] = valor_remoto
    base["_datos_agildte"] = True
    return base


def empresa_necesita_sync_agildte(vista: dict | None) -> bool:
    """True si faltan datos fiscales reales (solo placeholders en POS)."""
    if not vista:
        return True
    for campo in ("nit", "nrc", "direccion", "telefono", "correo"):
        if _es_placeholder_empresa(campo, vista.get(campo)):
            return True
    if _es_placeholder_empresa("actividad_economica", vista.get("actividad_economica")):
        return True
    if not (vista.get("codigo_actividad_economica") or "").strip():
        return True
    return False


def aplicar_empresa_agildte_en_bd(cur, empresa_id: int, agildte: dict) -> None:
    """Persiste en PostgreSQL del POS los datos maestros devueltos por AgilDTE."""
    remoto = agildte_empresa_a_vista(agildte)
    row = get_empresa(cur, empresa_id)
    local = sanitizar_empresa_vista(empresa_row_a_vista(row) or {"id": empresa_id})
    nombre = remoto.get("nombre_comercial") or local.get("nombre_comercial") or ""
    nit = remoto.get("nit") or local.get("nit") or ""
    nrc = remoto.get("nrc") or local.get("nrc") or ""
    actividad = remoto.get("actividad_economica") or local.get("actividad_economica") or ""
    cod_act = remoto.get("codigo_actividad_economica") or local.get("codigo_actividad_economica") or ""
    if cod_act and not actividad:
        try:
            from azdigital.repositories import actividades_repo

            desc = actividades_repo.get_descripcion_por_codigo(cur, cod_act)
            if desc:
                actividad = desc
        except Exception:
            pass
    actualizar_empresa(
        cur,
        empresa_id,
        nombre,
        nit,
        nrc,
        actividad,
        remoto.get("direccion") or local.get("direccion") or "",
        remoto.get("telefono") or local.get("telefono") or "",
        remoto.get("correo") or local.get("correo") or "",
        bool(local.get("suscripcion_activa")),
        local.get("fecha_vencimiento"),
        codigo_actividad_economica=cod_act,
        es_gran_contribuyente=get_empresa_es_gran_contribuyente(cur, empresa_id),
    )
    amb = (agildte.get("ambiente") or "").strip()
    if amb in ("00", "01"):
        set_ambiente_mh(cur, empresa_id, amb)


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


def get_ambiente_mh(cur, empresa_id: int) -> str | None:
    try:
        cur.execute(
            "SELECT ambiente_mh FROM empresas WHERE id = %s",
            (int(empresa_id),),
        )
        row = cur.fetchone()
        if row and row[0]:
            return str(row[0]).strip()
    except Exception:
        pass
    return None


def contar_empresas(cur) -> int:
    cur.execute("SELECT COUNT(*) FROM empresas")
    row = cur.fetchone()
    return int(row[0]) if row else 0


def eliminar_empresa(cur, empresa_id: int) -> bool:
    """Elimina la empresa por ID. Los hijos con ON DELETE CASCADE se borran en cascada."""
    cur.execute("DELETE FROM empresas WHERE id = %s", (int(empresa_id),))
    return cur.rowcount > 0


def set_ambiente_mh(cur, empresa_id: int, ambiente: str) -> None:
    amb = (ambiente or "01").strip()[:2]
    if amb not in ("00", "01"):
        amb = "01"
    try:
        cur.execute(
            "UPDATE empresas SET ambiente_mh = %s WHERE id = %s",
            (amb, int(empresa_id)),
        )
    except Exception:
        pass

