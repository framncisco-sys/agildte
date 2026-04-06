from django.test import TestCase, Client
from django.urls import resolve


class DescargaZipFacturasTests(TestCase):
    """Rutas y respuesta mínima para GET /api/facturas/descarga-zip/ (ZIP filtrado)."""

    def test_resolve_facturas_descarga_zip(self):
        match = resolve('/api/facturas/descarga-zip/')
        self.assertEqual(match.func.__name__, 'descargar_lote_ventas_api')

    def test_resolve_alias_api_descarga_zip(self):
        match = resolve('/api/descarga-zip/')
        self.assertEqual(match.func.__name__, 'descargar_lote_ventas_api')

    def test_get_no_devuelve_404_ruta_inexistente(self):
        """Si ves 404 {'detail':'No encontrado.'}, la URL no está en urlpatterns."""
        c = Client()
        r = c.get('/api/facturas/descarga-zip/?format=pdf')
        self.assertNotEqual(
            r.status_code,
            404,
            'La ruta /api/facturas/descarga-zip/ debe existir (revisa api/urls.py bajo path api/).',
        )

    def test_get_sin_credenciales_no_autorizado(self):
        c = Client()
        r = c.get('/api/facturas/descarga-zip/?format=pdf')
        # DRF IsAuthenticated suele responder 403 sin JWT; el cuerpo no debe ser 404 de Django.
        self.assertIn(r.status_code, (401, 403))
