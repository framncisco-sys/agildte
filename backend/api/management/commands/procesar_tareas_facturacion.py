"""
Management command para procesar tareas de facturación pendientes.
Ejecutar periódicamente (cron cada 1-5 min) cuando USE_ASYNC_FACTURACION=True.

Uso:
  python manage.py procesar_tareas_facturacion
  python manage.py procesar_tareas_facturacion --loop  # Bucle continuo (cada 30s)
"""
import time
import logging

from django.core.management.base import BaseCommand

from api.tasks import procesar_tareas_pendientes

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Procesa tareas de facturación pendientes (envío a MH, correo)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loop',
            action='store_true',
            help='Ejecutar en bucle cada 30 segundos',
        )
        parser.add_argument(
            '--limite',
            type=int,
            default=20,
            help='Máximo de tareas a procesar por ejecución',
        )

    def handle(self, *args, **options):
        loop = options['loop']
        limite = options['limite']

        if loop:
            self.stdout.write('Modo bucle: procesando cada 30 segundos. Ctrl+C para salir.')
            while True:
                n = procesar_tareas_pendientes(limite=limite)
                if n > 0:
                    self.stdout.write(self.style.SUCCESS(f'Procesadas {n} tareas'))
                time.sleep(30)
        else:
            n = procesar_tareas_pendientes(limite=limite)
            self.stdout.write(self.style.SUCCESS(f'Procesadas {n} tareas'))
