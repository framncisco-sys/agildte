"""Tests importación catálogo actividades MH."""
from django.test import TestCase

from api.models import ActividadEconomica
from api.services.actividades_import import import_actividades_rows, parse_rows_from_bytes


class ActividadesImportTest(TestCase):
    def test_csv_mh_semicolon(self):
        content = b"45201;Reparacion mecanica\nCABECERA;Ignorar\n45202;Carrocerias\n"
        rows = parse_rows_from_bytes(content, "actividades.csv")
        self.assertEqual(len(rows), 2)
        stats = import_actividades_rows(rows)
        self.assertEqual(stats["created"], 2)
        self.assertEqual(ActividadEconomica.objects.count(), 2)

    def test_update_or_create(self):
        import_actividades_rows([["62010", "Programacion"]])
        stats = import_actividades_rows([["62010", "Programacion informatica"]])
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(ActividadEconomica.objects.get(pk="62010").descripcion, "Programacion informatica")
