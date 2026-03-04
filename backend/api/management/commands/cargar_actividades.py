"""
Management command: cargar actividades económicas desde CSV o Excel.
- CSV: delimitador ;  →  CÓDIGO;ACTIVIDADES ECONÓMICAS
- Excel (.xlsx): columna A = Código, columna B = Descripción
Ignora filas sin código numérico (títulos). Usa update_or_create para idempotencia.
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
    if val is None:
        return False
    s = str(val).strip()
    if not s or s.lower() == 'nan':
        return False
    return bool(re.match(r'^[\d.]+$', s))


class Command(BaseCommand):
    help = 'Carga el catálogo de actividades económicas desde CSV (;) o Excel (.xlsx).'

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            nargs='?',
            type=str,
            default=None,
            help='Ruta al archivo CSV (;) o Excel (.xlsx). CSV: CÓDIGO;ACTIVIDAD. Excel: col A=código, col B=descripción.',
        )

    def handle(self, *args, **options):
        file_path = options.get('file')
        if not file_path:
            self.stderr.write(self.style.ERROR('Uso: python manage.py cargar_actividades <ruta_al_archivo>'))
            self.stderr.write(self.style.WARNING('Soporta CSV (;) o Excel (.xlsx). Ej: python manage.py cargar_actividades "Listado de actividades.xlsx"'))
            return
        path = Path(file_path).resolve()
        if not path.exists():
            self.stderr.write(self.style.ERROR(f'Archivo no encontrado: {path}'))
            return

        suffix = path.suffix.lower()
        if suffix == '.xlsx':
            try:
                import pandas as pd
                df = pd.read_excel(path, header=None, dtype=str)
                rows = []
                for _, row in df.iterrows():
                    c0 = str(row.iloc[0]) if len(row) > 0 else ''
                    c1 = str(row.iloc[1]) if len(row) > 1 else ''
                    rows.append([c0, c1])
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error al leer Excel: {e}'))
                return
        else:
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
            rows = list(csv.reader(io.StringIO(content), delimiter=';'))

        created = 0
        updated = 0
        skipped = 0
        with transaction.atomic():
            for row in rows:
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
