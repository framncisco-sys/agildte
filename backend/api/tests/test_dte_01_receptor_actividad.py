"""Tests DTE-01 receptor: NRC y actividad opcionales desde el formulario."""
from types import SimpleNamespace
from django.test import SimpleTestCase

from api.utils.builders.dte_01_builder import DTE01Builder


class DTE01ReceptorNrcActividadTests(SimpleTestCase):
    def _builder(self, **venta_fields):
        cliente = venta_fields.pop('cliente', None)
        venta = SimpleNamespace(
            cliente=cliente,
            nombre_receptor='Corvera S.A de C.V.',
            documento_receptor='12172409981012',
            tipo_doc_receptor='NIT',
            nrc_receptor=None,
            cod_actividad_receptor=None,
            desc_actividad_receptor=None,
            departamento_receptor='12',
            municipio_receptor='22',
            distrito_receptor='17',
            direccion_receptor='3a calle poniente',
            telefono_receptor='50326608900',
            correo_receptor='test@example.com',
            condicion_operacion=1,
            plazo_pago='',
            periodo_pago='',
            iva_retenido_1=0,
            observaciones='',
        )
        for k, v in venta_fields.items():
            setattr(venta, k, v)
        empresa = SimpleNamespace(
            nit='06142805901012',
            nrc='12345',
            nombre='Emisor Test',
            cod_actividad='62010',
            desc_actividad='Servicios',
            departamento='06',
            municipio='23',
            distrito='14',
            direccion='Calle 1',
            telefono='22222222',
            correo='emisor@test.com',
            cod_establecimiento='M001',
            nombre_comercial='',
        )
        b = DTE01Builder.__new__(DTE01Builder)
        b.venta = venta
        b.empresa = empresa
        return b

    def test_sin_nrc_ni_actividad_queda_null(self):
        b = self._builder()
        nrc, cod, desc = b._receptor_nrc_actividad()
        self.assertIsNone(nrc)
        self.assertIsNone(cod)
        self.assertIsNone(desc)

    def test_formulario_llena_nrc_y_actividad(self):
        b = self._builder(
            nrc_receptor='107919-0',
            cod_actividad_receptor='10712',
            desc_actividad_receptor='Fabricación de pan, galletas y barquillos',
        )
        nrc, cod, desc = b._receptor_nrc_actividad()
        self.assertEqual(nrc, '1079190')
        self.assertEqual(cod, '10712')
        self.assertIn('pan', desc.lower())

    def test_construir_receptor_incluye_valores(self):
        b = self._builder(
            nrc_receptor='107919-0',
            cod_actividad_receptor='10712',
            desc_actividad_receptor='Fabricación de pan, galletas y barquillos',
            cliente=None,
        )
        receptor = b._construir_receptor()
        self.assertEqual(receptor['nrc'], '1079190')
        self.assertEqual(receptor['codActividad'], '10712')
        self.assertTrue(receptor['descActividad'])

    def test_dui_en_cf_no_deja_numdocumento_huerfano(self):
        """Compatibilidad MH: DUI (13) en Factura CF → tipo y número ambos null."""
        b = self._builder(
            cliente=None,
            nombre_receptor='David Cerrano',
            documento_receptor='04727688-8',
            tipo_doc_receptor='DUI',
        )
        receptor = b._construir_receptor()
        self.assertEqual(receptor['nombre'], 'David Cerrano')
        self.assertIsNone(receptor['tipoDocumento'])
        self.assertIsNone(receptor['numDocumento'])
