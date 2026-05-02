# Programador: Oscar Amaya Romero
"""
Aprovisionamiento de filas locales (empresa, usuario) a partir de GET /api/auth/me/ de AgilDTE.
Evita registrar usuarios por duplicado: el SSO crea el usuario POS la primera vez.
"""
from __future__ import annotations

import secrets
from typing import Any

from werkzeug.security import generate_password_hash

from azdigital.repositories import empresas_repo, usuarios_repo


def map_agildte_role_to_pos_rol(
    api_role: str | None, *, is_superuser: bool = False
) -> str:
    """Mapea role JSON de AgilDTE a rol del POS (usuarios.rol).

    is_superuser (Django): se alinea con ADMIN en el POS (panel y permisos amplios).
    """
    if is_superuser:
        return "ADMIN"
    r = (api_role or "").strip().upper()
    if r in ("POSAGIL_VENDEDOR", "POS_VENDEDOR", "AGILDTE_VENDEDOR"):
        return "CAJERO"
    if r in ("POSAGIL_ADMIN", "AGILDTE_ADMIN", "ADMIN", "SUPERADMIN"):
        return "GERENTE"
    if r == "AGILDTE_CONTADOR":
        return "CONTADOR"
    return "CAJERO"


def extract_me_context(data: dict[str, Any]) -> tuple[str | None, int | None, str, str | None]:
    """
    Devuelve (username, empresa_id, nombre_empresa, role).
    empresa_id puede ser None si el perfil AgilDTE no tiene empresa (poco habitual para POS).
    """
    udj = data.get("user") or {}
    username = (udj.get("username") or "").strip() or None
    role = udj.get("role")
    if isinstance(role, str):
        role = role.strip() or None
    else:
        role = None

    empresa_id: int | None = None
    nombre_emp = "Empresa"
    ed = data.get("empresa_default")
    if isinstance(ed, dict) and ed.get("id") is not None:
        try:
            empresa_id = int(ed["id"])
        except (TypeError, ValueError):
            empresa_id = None
        nombre_emp = (ed.get("nombre") or ed.get("name") or "Empresa").strip() or "Empresa"
    if empresa_id is None and isinstance(udj.get("empresa_default"), dict):
        ed2 = udj["empresa_default"]
        try:
            empresa_id = int(ed2.get("id"))
        except (TypeError, ValueError):
            pass
        if empresa_id is not None:
            nombre_emp = (ed2.get("nombre") or "Empresa").strip() or "Empresa"

    return username, empresa_id, nombre_emp, role


def ensure_empresa_row(cur, empresa_id: int, nombre: str) -> None:
    """Inserta empresa con id = empresa_id (alineado con Django) si no existe."""
    cur.execute("SELECT 1 FROM empresas WHERE id = %s", (empresa_id,))
    if cur.fetchone():
        return
    nit, nrc = empresas_repo._nit_nrc_unicos_vacios(cur)
    nombre_c = (nombre or "Empresa")[:500]
    cur.execute(
        """
        INSERT INTO empresas (
            id, nombre_comercial, nit, nrc, actividad_economica, giro, suscripcion_activa
        ) VALUES (%s, %s, %s, %s, %s, %s, TRUE)
        """,
        (empresa_id, nombre_c, nit, nrc, "General", "General"),
    )
    cur.execute(
        "SELECT setval(pg_get_serial_sequence('empresas', 'id'), (SELECT MAX(id) FROM empresas))"
    )


def ensure_usuario_from_agildte(cur, username: str, pos_rol: str, empresa_id: int) -> None:
    """
    Crea usuario POS con contraseña inválida para login local (solo SSO).
    Si ya existe (mismo username), no hace nada.
    """
    cur.execute(
        "SELECT id FROM usuarios WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s))",
        (username,),
    )
    if cur.fetchone():
        return
    ph = generate_password_hash(secrets.token_urlsafe(48))
    usuarios_repo.crear_usuario(cur, username, ph, pos_rol, None, empresa_id)


def provision_if_missing(cur, me_json: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Crea o actualiza empresa y usuario local según /api/auth/me/.
    En cada login SSO debe ejecutarse: si el usuario ya existía como CAJERO y en AgilDTE
    pasó a administrador, se actualiza usuarios.rol (antes solo se insertaba la primera vez).
    Retorna (ok, mensaje_error).
    """
    username, empresa_id, nombre_emp, role = extract_me_context(me_json)
    if not username:
        return False, "Respuesta AgilDTE sin username."
    if empresa_id is None:
        return False, "Su perfil en AgilDTE no tiene empresa asignada. Asigne empresa en AgilDTE e intente de nuevo."

    udj = me_json.get("user") or {}
    is_super = bool(udj.get("is_superuser"))
    pos_rol = map_agildte_role_to_pos_rol(role, is_superuser=is_super)
    try:
        ensure_empresa_row(cur, empresa_id, nombre_emp)
        cur.execute(
            """
            UPDATE usuarios SET rol = %s, empresa_id = %s
            WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s))
            """,
            (pos_rol, empresa_id, username),
        )
        if cur.rowcount == 0:
            ensure_usuario_from_agildte(cur, username, pos_rol, empresa_id)
    except Exception as e:
        return False, str(e)
    return True, None
