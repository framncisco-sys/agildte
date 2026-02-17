"""
Crea los grupos de roles para RBAC.
Ejecutar: python manage.py init_roles
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

ROLES = [
    ('Administrador', 'Acceso total'),
    ('Contador', 'Acceso a Reportes y Libros IVA (solo lectura en Ventas)'),
    ('Vendedor', 'Acceso a Crear Facturas y Clientes'),
]


class Command(BaseCommand):
    help = 'Crea los grupos Administrador, Contador y Vendedor si no existen'

    def handle(self, *args, **options):
        for name, desc in ROLES:
            g, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Grupo creado: {name}'))
            else:
                self.stdout.write(f'Grupo ya existe: {name}')
        self.stdout.write(self.style.SUCCESS('Roles listos.'))
