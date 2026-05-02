"""
Permisos por rol (RBAC) — fuente única: Grupos de Django.

Nombres de grupo en BD (constantes GRUPO_*):
  AgilDTE - Administrador | AgilDTE - Contador | AgilDTE - Vendedor
  PosAgil - Administrador | PosAgil - Vendedor

Roles en JWT / API (constantes ROLE_*):
  AGILDTE_ADMIN | AGILDTE_CONTADOR | AGILDTE_VENDEDOR | POSAGIL_ADMIN | POSAGIL_VENDEDOR

Se aceptan también nombres heredados (Administrador, Contador, …) hasta que la migración renombre grupos.
"""
from __future__ import annotations

from rest_framework import permissions

# --- Nombres exactos de grupos en la base de datos (estándar actual) ---
GRUPO_AGILDTE_ADMIN = "AgilDTE - Administrador"
GRUPO_AGILDTE_CONTADOR = "AgilDTE - Contador"
GRUPO_AGILDTE_VENDEDOR = "AgilDTE - Vendedor"
GRUPO_POSAGIL_ADMIN = "PosAgil - Administrador"
GRUPO_POSAGIL_VENDEDOR = "PosAgil - Vendedor"

# --- Nombres heredados (antes de migración de renombrado / despliegues antiguos) ---
_LEGACY_GRUPO_ADMIN = "Administrador"
_LEGACY_GRUPO_CONTADOR = "Contador"
_LEGACY_GRUPO_VENDEDOR = "Vendedor"
_LEGACY_GRUPO_POS_VENDEDOR = "PosAgil Vendedor"

# --- Valores de `user.role` en login /auth/me (API JSON) ---
ROLE_AGILDTE_ADMIN = "AGILDTE_ADMIN"
ROLE_AGILDTE_CONTADOR = "AGILDTE_CONTADOR"
ROLE_AGILDTE_VENDEDOR = "AGILDTE_VENDEDOR"
ROLE_POSAGIL_ADMIN = "POSAGIL_ADMIN"
ROLE_POSAGIL_VENDEDOR = "POSAGIL_VENDEDOR"

# Rol por defecto si el usuario no tiene grupos asignados
ROLE_DEFAULT = ROLE_AGILDTE_VENDEDOR


def _group_names_agildte_admin() -> tuple[str, ...]:
    return (GRUPO_AGILDTE_ADMIN, _LEGACY_GRUPO_ADMIN)


def _group_names_agildte_contador() -> tuple[str, ...]:
    return (GRUPO_AGILDTE_CONTADOR, _LEGACY_GRUPO_CONTADOR)


def _group_names_agildte_vendedor() -> tuple[str, ...]:
    return (GRUPO_AGILDTE_VENDEDOR, _LEGACY_GRUPO_VENDEDOR)


def _group_names_posagil_vendedor() -> tuple[str, ...]:
    return (GRUPO_POSAGIL_VENDEDOR, _LEGACY_GRUPO_POS_VENDEDOR)


def _group_names_posagil_admin() -> tuple[str, ...]:
    return (GRUPO_POSAGIL_ADMIN,)


def _user_has_any_group(user, *group_names: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    names = [n for n in group_names if n]
    if not names:
        return False
    return user.groups.filter(name__in=names).exists()


def get_perfil_pos_flags(user) -> tuple[bool, bool]:
    """
    (acceso_posagil, facturacion_solo_pos) desde PerfilUsuario activo.
    """
    if not user or not user.is_authenticated:
        return False, False
    from .models import PerfilUsuario

    try:
        p = PerfilUsuario.objects.get(user=user, activo=True)
        return bool(p.acceso_posagil), bool(p.facturacion_solo_pos)
    except PerfilUsuario.DoesNotExist:
        return False, False


def get_user_role(user) -> str | None:
    """
    Rol lógico para JWT / frontend (ROLE_*).
    Prioridad: vendedor PosAgil antes que grupos AgilDTE (evita solapamientos accidentales).
    """
    if not user or not user.is_authenticated:
        return None
    if getattr(user, "is_superuser", False):
        return ROLE_AGILDTE_ADMIN
    if _user_has_any_group(user, *_group_names_posagil_vendedor()):
        return ROLE_POSAGIL_VENDEDOR
    if _user_has_any_group(user, *_group_names_posagil_admin()):
        return ROLE_POSAGIL_ADMIN
    if _user_has_any_group(user, *_group_names_agildte_admin()):
        return ROLE_AGILDTE_ADMIN
    if _user_has_any_group(user, *_group_names_agildte_contador()):
        return ROLE_AGILDTE_CONTADOR
    if _user_has_any_group(user, *_group_names_agildte_vendedor()):
        return ROLE_AGILDTE_VENDEDOR
    return ROLE_DEFAULT


def _is_platform_admin(user) -> bool:
    """Administración AgilDTE o PosAgil (no incluye solo contador/vendedor)."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _user_has_any_group(
        user,
        *_group_names_agildte_admin(),
        *_group_names_posagil_admin(),
    )


def _is_contador_o_admin(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _user_has_any_group(
        user,
        *_group_names_agildte_admin(),
        *_group_names_posagil_admin(),
        *_group_names_agildte_contador(),
    )


def _is_vendedor_o_admin(user) -> bool:
    """Puede operar ventas/DTE en API (incluye vendedor PosAgil)."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _user_has_any_group(
        user,
        *_group_names_agildte_admin(),
        *_group_names_posagil_admin(),
        *_group_names_agildte_vendedor(),
        *_group_names_posagil_vendedor(),
    )


class IsAdminUser(permissions.BasePermission):
    """Solo administradores AgilDTE o PosAgil (o superusuario)."""

    message = "Solo administradores pueden realizar esta acción."

    def has_permission(self, request, view):
        return _is_platform_admin(request.user)


class IsContadorUser(permissions.BasePermission):
    """Contador o administradores (AgilDTE o PosAgil) o superusuario."""

    message = "Se requiere rol Contador o Administrador."

    def has_permission(self, request, view):
        return _is_contador_o_admin(request.user)


class IsVendedorUser(permissions.BasePermission):
    """Vendedor (AgilDTE o PosAgil) o administradores; permite facturar vía API."""

    message = "Se requiere rol Vendedor o Administrador."

    def has_permission(self, request, view):
        return _is_vendedor_o_admin(request.user)


# Aliases para compatibilidad con código existente
IsAdmin = IsAdminUser
IsContadorOrAdmin = IsContadorUser
IsVendedorOrAdmin = IsVendedorUser
