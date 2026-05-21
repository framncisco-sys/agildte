"""Tests unitarios — WhatsApp Cloud (sin llamar a Meta)."""
from django.test import SimpleTestCase

from api.services.whatsapp_cloud_service import (
    construir_mensaje_factura,
    normalizar_telefono_meta,
    resolver_nis_factura,
)


class NormalizarTelefonoTests(SimpleTestCase):
    def test_ocho_digitos_sv(self):
        self.assertEqual(normalizar_telefono_meta('71234567'), '50371234567')

    def test_con_prefijo_503(self):
        self.assertEqual(normalizar_telefono_meta('+503 7123-4567'), '50371234567')


class MensajeFacturaTests(SimpleTestCase):
    def test_incluye_nombre_y_enlace(self):
        msg = construir_mensaje_factura(nombre_cliente='Juan', nis='ABC-123')
        self.assertIn('Juan', msg)
        self.assertIn('ABC-123', msg)
        self.assertIn('edesaldocs.com', msg)


class ResolverNisTests(SimpleTestCase):
    def test_usa_codigo_generacion(self):
        class V:
            pk = 9
            codigo_generacion = 'UUID-1'

        self.assertEqual(resolver_nis_factura(V()), 'UUID-1')

    def test_fallback_id(self):
        class V:
            pk = 9
            codigo_generacion = ''

        self.assertEqual(resolver_nis_factura(V()), '9')
