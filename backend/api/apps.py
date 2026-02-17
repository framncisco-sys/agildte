from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        from django.contrib.auth.models import Group
        for name in ('Administrador', 'Contador', 'Vendedor'):
            Group.objects.get_or_create(name=name)
