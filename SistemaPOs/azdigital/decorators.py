# Programador: Oscar Amaya Romero
from __future__ import annotations

import os
from functools import wraps
from typing import Callable, TypeVar, cast

from flask import redirect, session, url_for

F = TypeVar("F", bound=Callable[..., object])


def redirect_to_login_page():
    """Sin sesión PosAgil: enviar al login local o al portal AgilDTE si está configurado."""
    portal = (os.environ.get("AGILDTE_PORTAL_LOGIN_URL") or os.environ.get("AZ_AGILDTE_PORTAL_LOGIN_URL") or "").strip()
    if portal:
        return redirect(portal)
    return redirect(url_for("auth.login"))

ROLES_SUPER = ("ADMIN", "SUPERADMIN")
ROLES_GERENTE = ROLES_SUPER + ("GERENTE",)
ROLES_CONTADOR = ROLES_GERENTE + ("CONTADOR",)
ROLES_BODEGUERO = ROLES_GERENTE + ("BODEGUERO",)
ROLES_CAJERO = ROLES_GERENTE + ("CAJERO",)  # Ventas y clientes (BODEGUERO no ve ventas)


def login_required(fn: F) -> F:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect_to_login_page()
        return fn(*args, **kwargs)

    return cast(F, wrapper)


def _rol_desde_bd():
    """Obtiene el rol actual desde BD (más fiable que sesión)."""
    uid = session.get("user_id")
    if not uid:
        return None
    try:
        import psycopg2
        from database import ConexionDB
        db = ConexionDB()
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        cur.execute("SELECT rol FROM usuarios WHERE id = %s AND activo = TRUE", (uid,))
        r = cur.fetchone()
        cur.close()
        conn.close()
        if r and r[0]:
            rol = str(r[0]).strip().upper()
            session["rol"] = rol
            return rol
    except Exception:
        pass
    return session.get("rol")


def _rol_tiene_acceso(rol: str | None, roles_permitidos: tuple[str, ...]) -> bool:
    """True si el rol está en la tupla de roles permitidos."""
    r = (rol or "").strip().upper()
    return r in roles_permitidos


def rol_requerido(*roles_permitidos: str):
    """Decorador: permite acceso solo a los roles indicados. Superusuario siempre tiene acceso."""
    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect_to_login_page()
            rol = _rol_desde_bd()
            if rol in ROLES_SUPER:
                return fn(*args, **kwargs)
            if rol in roles_permitidos:
                return fn(*args, **kwargs)
            return redirect(url_for("core.index"))
        return cast(F, wrapper)
    return decorator


def admin_required(fn: F) -> F:
    """ADMIN, SUPERADMIN, GERENTE (antes Admin)."""
    return rol_requerido("GERENTE")(fn)


def superadmin_required(fn: F) -> F:
    """Solo ADMIN, SUPERADMIN."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect_to_login_page()
        rol = _rol_desde_bd()
        if rol not in ROLES_SUPER:
            return redirect(url_for("core.index"))
        return fn(*args, **kwargs)
    return cast(F, wrapper)


def _es_superusuario(rol: str | None) -> bool:
    """ADMIN y SUPERADMIN = superusuario (control total)."""
    r = (rol or "").strip().upper()
    return r in ROLES_SUPER


def puede_ver_ventas(rol: str | None) -> bool:
    """POS, ventas, clientes: CAJERO, BODEGUERO, GERENTE, ADMIN."""
    return _rol_tiene_acceso(rol, ROLES_CAJERO)


def puede_ver_inventario(rol: str | None) -> bool:
    """Inventario, movimientos, kardex: BODEGUERO, GERENTE, ADMIN."""
    return _rol_tiene_acceso(rol, ROLES_BODEGUERO)


def puede_ver_reportes_contables(rol: str | None) -> bool:
    """Libro IVA, F-983, valuación, cuentas cobrar: CONTADOR, GERENTE, ADMIN."""
    return _rol_tiene_acceso(rol, ROLES_CONTADOR)


def puede_ver_administracion(rol: str | None) -> bool:
    """Usuarios, sucursales, config: GERENTE, ADMIN."""
    return _rol_tiene_acceso(rol, ROLES_GERENTE)


def puede_gestionar_ventas(rol: str | None) -> bool:
    """Gestión de ventas (editar / anular): GERENTE, ADMIN, SUPERADMIN."""
    return _rol_tiene_acceso(rol, ROLES_GERENTE)

