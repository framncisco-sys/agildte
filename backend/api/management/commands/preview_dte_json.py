"""
Muestra el JSON DTE que se enviaría a MH para una venta.
Uso: python manage.py preview_dte_json <venta_id|ultimo>
  venta_id: ID numérico de la venta
  ultimo:   última venta creada (por ID)
Sirve para validar el formato (emisor.nrc, etc.) antes de enviar.
"""
import json
from django.core.management.base import BaseCommand

from api.models import Venta
from api.utils.builders import generar_dte


class Command(BaseCommand):
    help = 'Muestra el JSON DTE que se enviaría a MH para una venta (para validar formato emisor.nrc, etc.)'

    def add_arguments(self, parser):
        parser.add_argument('venta_id', type=str, help='ID de la venta o "ultimo" para la última emitida')
        parser.add_argument(
            '--ambiente',
            type=str,
            default=None,
            help='Ambiente DTE: 00 (pruebas) o 01 (producción). Por defecto usa empresa.ambiente invertido.',
        )

    def handle(self, *args, **options):
        venta_id_arg = options['venta_id']
        if str(venta_id_arg).lower() == 'ultimo':
            venta = Venta.objects.order_by('-id').first()
            if not venta:
                self.stderr.write(self.style.ERROR('No hay ventas en el sistema'))
                return
            self.stdout.write(self.style.WARNING(f'Usando última venta: #{venta.id}'))
        else:
            try:
                venta_id = int(venta_id_arg)
            except ValueError:
                self.stderr.write(self.style.ERROR(f'Venta ID debe ser un número o "ultimo"'))
                return
            try:
                venta = Venta.objects.get(pk=venta_id)
            except Venta.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Venta {venta_id} no encontrada'))
                return

        if not venta.empresa:
            self.stderr.write(self.style.ERROR('La venta no tiene empresa asociada'))
            return

        emp = venta.empresa
        ambiente_emp = (emp.ambiente or '01').strip()
        DTE_AMBIENTE = {'01': '00', '00': '01'}
        ambiente_dte = options.get('ambiente') or DTE_AMBIENTE.get(ambiente_emp, '00')

        self.stdout.write(f'\n=== Venta #{venta.id} | Empresa: {emp.nombre} ===')
        self.stdout.write(f'Empresa.ambiente: {ambiente_emp} → DTE ambiente: {ambiente_dte}')
        self.stdout.write(f'Empresa NRC (crudo): {repr(emp.nrc)}')
        self.stdout.write('')

        try:
            json_dte = generar_dte(venta, ambiente=ambiente_dte)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error generando DTE: {e}'))
            import traceback
            self.stderr.write(traceback.format_exc())
            return

        emisor = json_dte.get('emisor', {})
        self.stdout.write(self.style.SUCCESS('--- EMISOR (fragmento) ---'))
        self.stdout.write(json.dumps({
            'nit': emisor.get('nit'),
            'nrc': emisor.get('nrc'),
            'nombre': emisor.get('nombre'),
        }, indent=2, ensure_ascii=False))
        self.stdout.write('')

        self.stdout.write('--- JSON DTE COMPLETO ---')
        self.stdout.write(json.dumps(json_dte, indent=2, ensure_ascii=False))
        self.stdout.write('')
