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
    """Crea los grupos Administrador, Contador y Vendedor si no existen."""
    try:
        from django.contrib.auth.models import Group
        for nombre in ('Administrador', 'Contador', 'Vendedor'):
            Group.objects.get_or_create(name=nombre)
    except Exception:
        pass
