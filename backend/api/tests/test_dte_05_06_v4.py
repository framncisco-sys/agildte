"""Pruebas contractuales NC/ND contra schemas oficiales MH v4."""
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from api.models import Empresa, Venta
from api.utils.builders.dte_05_builder import DTE05Builder
from api.utils.builders.dte_06_builder import DTE06Builder
from api.utils.mh_schema_validator import validar_dte_contra_schema


EMISOR = {
    'nit': '06140101011019',
    'nrc': '1234567',
    'nombre': 'Empresa de Prueba',
    'codActividad': '62010',
    'descActividad': 'Servicios de tecnología',
    'nombreComercial': 'Empresa Prueba',
    'direccion': {
        'departamento': '06',
        'municipio': '23',
        'distrito': '14',
        'complemento': 'San Salvador',
    },
    'telefono': '50322222222',
    'correo': 'facturas@empresa.test',
}

RECEPTOR = {
    'tipoDocumento': '36',
    'numDocumento': '06140101011019',
    'nrc': '7654321',
    'nombre': 'Cliente de Prueba',
    'codActividad': '62010',
    'descActividad': 'Servicios de tecnología',
    'nombreComercial': 'Cliente Prueba',
    'direccion': {
        'departamento': '06',
        'municipio': '23',
        'distrito': '14',
        'complemento': 'San Salvador',
    },
    'telefono': '50370000000',
    'correo': 'cliente@example.com',
}

ITEM = {
    'numItem': 1,
    'tipoItem': 1,
    'numeroDocumento': None,
    'cantidad': 1.0,
    'codigo': 'ITEM-1',
    'codTributo': None,
    'uniMedida': 59,
    'descripcion': 'Ajuste de operación',
    'precioUni': 100.0,
    'montoDescu': 0.0,
    'ventaNoSuj': 0.0,
    'ventaExenta': 0.0,
    'ventaGravada': 100.0,
    'tributos': ['20'],
    'noGravado': 0.0,
    'ivaPerci': 0.0,
    'totalIva': 0.0,
    'ivaRete': 0.0,
}


def _venta(tipo):
    empresa = Empresa(
        id=1,
        nit='06140101011019',
        nrc='1234567',
        nombre='Empresa de Prueba',
        cod_actividad='62010',
        desc_actividad='Servicios de tecnología',
        cod_establecimiento='M001',
        cod_punto_venta='P001',
    )
    return Venta(
        id=10,
        empresa=empresa,
        tipo_venta=tipo,
        fecha_emision=date(2026, 7, 30),
        hora_emision='10:15:30',
        codigo_generacion='AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE',
        numero_control=f'DTE-{"05" if tipo == "NC" else "06"}-M001P001-000000000000001',
        condicion_operacion=1,
        documento_relacionado_tipo='03',
        documento_relacionado_tipo_generacion=2,
        codigo_generacion_referenciado='11111111-2222-4333-8444-555555555555',
        documento_relacionado_fecha_emision=date(2026, 7, 20),
        iva_retenido_1=0,
        iva_retenido_2=0,
    )


class NotaCreditoDebitoV4Tests(SimpleTestCase):
    def _generar(self, builder_cls, tipo):
        builder = builder_cls(_venta(tipo))
        with (
            patch.object(builder, '_construir_emisor', return_value=dict(EMISOR)),
            patch.object(builder, '_construir_receptor', return_value=dict(RECEPTOR)),
            patch.object(builder, '_generar_items', return_value=[dict(ITEM)]),
        ):
            return builder.generar_json(
                ambiente='00',
                generar_codigo=False,
                generar_numero_control=False,
            )

    def test_nc_cumple_schema_v4(self):
        dte = self._generar(DTE05Builder, 'NC')
        self.assertEqual(dte['identificacion']['version'], 4)
        self.assertEqual(dte['identificacion']['tipoDte'], '05')
        self.assertIn('fusion', dte['identificacion'])
        self.assertNotIn('otrosDocumentos', dte)
        self.assertEqual(validar_dte_contra_schema(dte, tipo_dte='05', strict=False), [])

    def test_nd_cumple_schema_v4(self):
        dte = self._generar(DTE06Builder, 'ND')
        self.assertEqual(dte['identificacion']['version'], 4)
        self.assertEqual(dte['identificacion']['tipoDte'], '06')
        self.assertIn('numPagoElectronico', dte['resumen'])
        self.assertEqual(validar_dte_contra_schema(dte, tipo_dte='06', strict=False), [])
