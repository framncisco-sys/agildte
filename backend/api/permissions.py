"""
Permisos por rol (RBAC) — fuente única: Grupos de Django.

Grupos:  Administrador | Contador | Vendedor
Roles API devueltos: ADMIN | CONTADOR | VENDEDOR

Jerarquía:
  Superusuario Django  → ADMIN  (acceso total + todas las empresas)
  Grupo Administrador  → ADMIN  (gestión completa de su empresa)
  Grupo Contador       → CONTADOR (solo reportes/libros)
  Grupo Vendedor       → VENDEDOR (facturación)
  Sin grupo            → VENDEDOR (mínimo seguro)
"""
from rest_framework import permissions

GROUP_ADMIN = 'Administrador'
GROUP_CONTADOR = 'Contador'
GROUP_VENDEDOR = 'Vendedor'


def _in_group(user, group_name: str) -> bool:
    """Verifica si el usuario pertenece al grupo dado."""
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=group_name).exists()


def get_user_role(user) -> str | None:
    """
    Devuelve el rol del usuario según su grupo Django.
    Única fuente de verdad: los Grupos de Django.
    """
    if not user or not user.is_authenticated:
        return None
    if getattr(user, 'is_superuser', False):
        return 'ADMIN'
    if _in_group(user, GROUP_ADMIN):
        return 'ADMIN'
    if _in_group(user, GROUP_CONTADOR):
        return 'CONTADOR'
    if _in_group(user, GROUP_VENDEDOR):
        return 'VENDEDOR'
    # Sin grupo asignado → mínimo seguro
    return 'VENDEDOR'


class IsAdminUser(permissions.BasePermission):
    """Solo grupo Administrador o superusuario."""
    message = 'Solo administradores pueden realizar esta acción.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'is_superuser', False) or _in_group(request.user, GROUP_ADMIN)


class IsContadorUser(permissions.BasePermission):
    """Grupo Contador o Administrador (o superusuario)."""
    message = 'Se requiere rol Contador o Administrador.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'is_superuser', False):
            return True
        return _in_group(request.user, GROUP_ADMIN) or _in_group(request.user, GROUP_CONTADOR)


class IsVendedorUser(permissions.BasePermission):
    """Grupo Vendedor o Administrador (o superusuario). Permite facturar."""
    message = 'Se requiere rol Vendedor o Administrador.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'is_superuser', False):
            return True
        return _in_group(request.user, GROUP_ADMIN) or _in_group(request.user, GROUP_VENDEDOR)


# Aliases para compatibilidad con código existente
IsAdmin = IsAdminUser
IsContadorOrAdmin = IsContadorUser
IsVendedorOrAdmin = IsVendedorUser
