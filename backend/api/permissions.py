"""
Permisos por rol (RBAC). Grupos Django: Administrador, Contador, Vendedor.
"""
from rest_framework import permissions

GROUP_ADMIN = 'Administrador'
GROUP_CONTADOR = 'Contador'
GROUP_VENDEDOR = 'Vendedor'
ROLE_NAMES = (GROUP_ADMIN, GROUP_CONTADOR, GROUP_VENDEDOR)


def _user_in_group(user, group_name):
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=group_name).exists()


def get_user_role(user):
    """Devuelve rol para API: ADMIN, CONTADOR, VENDEDOR. Por defecto VENDEDOR."""
    if not user or not user.is_authenticated:
        return None
    if getattr(user, 'is_superuser', False):
        return 'ADMIN'
    if _user_in_group(user, GROUP_ADMIN):
        return 'ADMIN'
    if _user_in_group(user, GROUP_CONTADOR):
        return 'CONTADOR'
    if _user_in_group(user, GROUP_VENDEDOR):
        return 'VENDEDOR'
    try:
        from .models import PerfilUsuario
        perfil = PerfilUsuario.objects.get(user=user, activo=True)
        r = (perfil.rol or '').upper()
        if r in ('MASTER', 'ADMINISTRADOR', 'ADMIN'):
            return 'ADMIN'
        if r == 'CONTADOR':
            return 'CONTADOR'
        if r == 'VENDEDOR':
            return 'VENDEDOR'
    except Exception:
        pass
    return 'VENDEDOR'


class IsAdminUser(permissions.BasePermission):
    """Solo grupo Administrador o superuser."""
    message = 'Solo administradores pueden realizar esta acción.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'is_superuser', False):
            return True
        return _user_in_group(request.user, GROUP_ADMIN)


class IsContadorUser(permissions.BasePermission):
    """Grupo Contador o Administrador."""
    message = 'Se requiere rol Contador o Administrador.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'is_superuser', False) or _user_in_group(request.user, GROUP_ADMIN):
            return True
        return _user_in_group(request.user, GROUP_CONTADOR)


class IsVendedorUser(permissions.BasePermission):
    """Grupo Vendedor o Administrador."""
    message = 'Se requiere rol Vendedor o Administrador.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'is_superuser', False) or _user_in_group(request.user, GROUP_ADMIN):
            return True
        return _user_in_group(request.user, GROUP_VENDEDOR)


# Alias para compatibilidad
IsAdmin = IsAdminUser
IsContadorOrAdmin = IsContadorUser
IsVendedorOrAdmin = IsVendedorUser
