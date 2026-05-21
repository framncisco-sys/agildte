"""
Management command: cargar actividades económicas desde CSV o Excel (catálogo MH).
"""
from django.core.management.base import BaseCommand

from api.services.actividades_import import import_actividades_from_fileobj, parse_rows_from_path


class Command(BaseCommand):
    help = "Carga el catálogo de actividades económicas desde CSV (;) o Excel (.xlsx)."

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            nargs="?",
            type=str,
            default=None,
            help="Ruta al archivo CSV (;) o Excel (.xlsx).",
        )

    def handle(self, *args, **options):
        file_path = options.get("file")
        if not file_path:
            self.stderr.write(self.style.ERROR("Uso: python manage.py cargar_actividades <ruta_al_archivo>"))
            return
        try:
            with open(file_path, "rb") as f:
                stats = import_actividades_from_fileobj(f, file_path)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Archivo no encontrado: {file_path}"))
            return
        except ValueError as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: {stats['created']} creados, {stats['updated']} actualizados, "
                f"{stats['skipped']} ignoradas. Total en BD: {stats['total_en_bd']}."
            )
        )
