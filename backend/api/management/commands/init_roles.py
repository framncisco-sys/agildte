"""
Crea los grupos de roles para RBAC (nombres alineados con api/permissions.py).
Ejecutar: python manage.py init_roles
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from api.permissions import (
    GRUPO_AGILDTE_ADMIN,
    GRUPO_AGILDTE_CONTADOR,
    GRUPO_AGILDTE_VENDEDOR,
    GRUPO_POSAGIL_ADMIN,
    GRUPO_POSAGIL_VENDEDOR,
)

ROLES = [
    (GRUPO_AGILDTE_ADMIN, 'Administración AgilDTE (empresa)'),
    (GRUPO_AGILDTE_CONTADOR, 'Reportes y libros IVA'),
    (GRUPO_AGILDTE_VENDEDOR, 'Facturación y clientes en AgilDTE'),
    (GRUPO_POSAGIL_ADMIN, 'Administración vía portal + PosAgil'),
    (GRUPO_POSAGIL_VENDEDOR, 'Punto de venta PosAgil (solo POS)'),
]


class Command(BaseCommand):
    help = 'Crea los grupos AgilDTE / PosAgil si no existen'

    def handle(self, *args, **options):
        for name, desc in ROLES:
            g, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Grupo creado: {name} ({desc})'))
            else:
                self.stdout.write(f'Grupo ya existe: {name}')
        self.stdout.write(self.style.SUCCESS('Roles listos.'))
