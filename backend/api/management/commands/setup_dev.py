"""
Comando para inicializar el entorno de desarrollo local.
Crea superusuario, empresa de prueba y configura credenciales MH.

Uso:
  python manage.py setup_dev
  python manage.py setup_dev --reset   # borra y recrea la empresa
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Inicializa el entorno de desarrollo local con datos de prueba'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Elimina y recrea la empresa')

    def handle(self, *args, **options):
        from api.models import Empresa

        self.stdout.write(self.style.SUCCESS('\n=== SETUP DEV - AgilDTE ===\n'))

        # 1. Superusuario
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@agildte.local', 'admin123')
            self.stdout.write('✅ Superusuario creado: admin / admin123')
        else:
            self.stdout.write('ℹ️  Superusuario admin ya existe')

        # 2. Empresa de prueba
        if options['reset']:
            Empresa.objects.all().delete()
            self.stdout.write('🗑️  Empresas eliminadas')

        empresa, created = Empresa.objects.get_or_create(
            nit='12092310921022',
            defaults={
                'nombre': 'Francisco Jose Salamanca',
                'nombre_comercial': 'AgilDTE Dev',
                'nrc': '1234567',
                'giro': 'Servicios de Software',
                'telefono': '22221111',
                'correo': 'prueba@agildte.com',
                'direccion': 'San Salvador',
                'departamento': '06',
                'municipio': '14',
                'cod_establecimiento': 'M001',
                'cod_punto_venta': 'P001',
                # Credenciales MH - PRUEBAS
                'user_api_mh': '12092310921022',
                'clave_api_mh': '2Caballo.Azul',
                'ambiente': '01',   # '01' = PRUEBAS (apitest.dtes.mh.gob.sv)
            }
        )

        if created:
            self.stdout.write('✅ Empresa de prueba creada')
        else:
            # Asegurar que el ambiente sea '01' (PRUEBAS)
            changed = False
            if empresa.ambiente != '01':
                empresa.ambiente = '01'
                changed = True
            if empresa.user_api_mh != '12092310921022':
                empresa.user_api_mh = '12092310921022'
                changed = True
            if empresa.clave_api_mh != '2Caballo.Azul':
                empresa.clave_api_mh = '2Caballo.Azul'
                changed = True
            if changed:
                empresa.save()
                self.stdout.write('✅ Empresa actualizada (ambiente=01, credenciales corregidas)')
            else:
                self.stdout.write('ℹ️  Empresa ya configurada correctamente')

        self.stdout.write(f'\n📋 Estado de la empresa:')
        self.stdout.write(f'   Nombre:      {empresa.nombre}')
        self.stdout.write(f'   NIT:         {empresa.nit}')
        self.stdout.write(f'   ambiente:    {empresa.ambiente} ({"PRUEBAS/apitest" if empresa.ambiente == "01" else "PRODUCCION/api"})')
        self.stdout.write(f'   user_api_mh: {empresa.user_api_mh}')
        self.stdout.write(f'   clave_api_mh len: {len(empresa.clave_api_mh or "")}')

        self.stdout.write(self.style.SUCCESS('\n✅ Setup completado. Accede a http://localhost:8000/admin con admin/admin123\n'))
