from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # Crear los grupos base DESPUÉS de que las migraciones terminen,
        # no durante el arranque (evita el error "relation auth_group does not exist")
        from django.db.models.signals import post_migrate
        post_migrate.connect(_crear_grupos_base, sender=self)


def _crear_grupos_base(sender, **kwargs):
    """Crea los grupos RBAC con nombres estandarizados (ver permissions.GRUPO_*)."""
    try:
        from django.contrib.auth.models import Group
        from .permissions import (
            GRUPO_AGILDTE_ADMIN,
            GRUPO_AGILDTE_CONTADOR,
            GRUPO_AGILDTE_VENDEDOR,
            GRUPO_POSAGIL_ADMIN,
            GRUPO_POSAGIL_VENDEDOR,
        )

        for nombre in (
            GRUPO_AGILDTE_ADMIN,
            GRUPO_AGILDTE_CONTADOR,
            GRUPO_AGILDTE_VENDEDOR,
            GRUPO_POSAGIL_ADMIN,
            GRUPO_POSAGIL_VENDEDOR,
        ):
            Group.objects.get_or_create(name=nombre)
    except Exception:
        pass
