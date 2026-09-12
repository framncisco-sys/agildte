"""Ítem facturado sin catálogo debe poder crearse; sin descripción no se inventa."""
from django.test import SimpleTestCase

from api.utils.producto_catalogo import asegurar_producto_desde_linea


class AsegurarProductoDesdeLineaTests(SimpleTestCase):
    def test_sin_empresa_no_crea(self):
        self.assertIsNone(asegurar_producto_desde_linea(None, descripcion="Leche"))

    def test_sin_descripcion_no_crea(self):
        self.assertIsNone(asegurar_producto_desde_linea(object(), descripcion="   "))
        self.assertIsNone(asegurar_producto_desde_linea(object(), descripcion=None))
