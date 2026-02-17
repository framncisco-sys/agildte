"""
Management command: cargar actividades económicas desde CSV (delimitador ;).
Estructura esperada: CÓDIGO;ACTIVIDADES ECONÓMICAS
Ignora filas sin código numérico (títulos de categoría). Usa update_or_create para idempotencia.
"""
import csv
import io
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import ActividadEconomica


def codigo_es_numerico(val):
    """True si el valor parece un código numérico (solo dígitos, posiblemente con puntos)."""
    if not val or not isinstance(val, str):
        return False
    s = val.strip()
    if not s:
        return False
    return bool(re.match(r'^[\d.]+$', s))


class Command(BaseCommand):
    help = 'Carga el catálogo de actividades económicas desde un CSV (delimitador ;).'

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            nargs='?',
            type=str,
            default=None,
            help='Ruta al archivo CSV delimitado por ; (ej: "C:\\Users\\...\\codigo de actividades.csv"). Estructura: CÓDIGO;ACTIVIDADES ECONÓMICAS',
        )

    def handle(self, *args, **options):
        file_path = options.get('file')
        if not file_path:
            self.stderr.write(self.style.ERROR('Uso: python manage.py cargar_actividades <ruta_al_csv>'))
            self.stderr.write(self.style.WARNING('Ejemplo: python manage.py cargar_actividades "C:\\Users\\...\\codigo de actividades.csv"'))
            return
        path = Path(file_path).resolve()
        if not path.exists():
            self.stderr.write(self.style.ERROR(f'Archivo no encontrado: {path}'))
            return
        encoding_candidates = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        content = None
        for enc in encoding_candidates:
            try:
                content = path.read_text(encoding=enc)
                break
            except Exception:
                continue
        if content is None:
            self.stderr.write(self.style.ERROR('No se pudo leer el archivo con ninguna codificación probada.'))
            return
        reader = csv.reader(io.StringIO(content), delimiter=';')
        created = 0
        updated = 0
        skipped = 0
        with transaction.atomic():
            for row in reader:
                if len(row) < 2:
                    skipped += 1
                    continue
                codigo_raw = (row[0] or '').strip()
                descripcion = (row[1] or '').strip()
                if not codigo_es_numerico(codigo_raw):
                    skipped += 1
                    continue
                codigo = codigo_raw[:10]
                if not descripcion:
                    descripcion = codigo
                obj, was_created = ActividadEconomica.objects.update_or_create(
                    codigo=codigo,
                    defaults={'descripcion': descripcion},
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
        self.stdout.write(self.style.SUCCESS(f'Listo: {created} creados, {updated} actualizados, {skipped} filas ignoradas.'))
