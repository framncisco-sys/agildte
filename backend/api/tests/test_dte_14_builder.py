"""Pruebas de generación DTE-14 (FSE) y mapeo desde Venta."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.utils.builders.director import generar_dte
from api.utils.builders.dte_14_builder import DTE14Builder


class DTE14DirectorTests(SimpleTestCase):
    def test_usa_detalles_y_ubicacion_de_venta(self):
        producto = SimpleNamespace(codigo='P-1', descripcion='Servicio prueba', tipo_item=2)
        detalle = SimpleNamespace(
            precio_unitario=Decimal('10.00'),
            cantidad=Decimal('2.00'),
            monto_descuento=Decimal('1.00'),
            codigo_libre=None,
            descripcion_libre=None,
            producto=producto,
        )
        detalles_manager = MagicMock()
        detalles_manager.select_related.return_value.all.return_value = [detalle]

        empresa = SimpleNamespace(
            id=1,
            nit='06140101011019',
            nrc='1234567',
            nombre='Empresa Test',
            cod_actividad='62010',
            desc_actividad='Servicios',
            departamento='06',
            municipio='23',
            distrito='14',
            direccion='Centro',
            telefono='22222222',
            correo='test@empresa.com',
            cod_establecimiento='M001',
            cod_punto_venta='P001',
        )
        venta = SimpleNamespace(
            codigo_generacion='AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE',
            numero_control='DTE-14-M001P001-000000000000001',
            fecha_emision=date(2026, 7, 30),
            hora_emision='10:15:30',
            documento_receptor='012345678',
            nrc_receptor=None,
            nombre_receptor='Proveedor Informal',
            departamento_receptor='06',
            municipio_receptor='23',
            distrito_receptor='14',
            direccion_receptor='Calle Principal',
            correo_receptor='prov@test.com',
            venta_gravada=Decimal('19.00'),
            venta_exenta=Decimal('0'),
            venta_no_sujeta=Decimal('0'),
            condicion_operacion=1,
            tipo_venta='FSE',
            tipo_dte=None,
            empresa=empresa,
            detalles=detalles_manager,
        )

        with patch('api.utils.builders.dte_14_builder.CorrelativoDTE.obtener_siguiente_correlativo', return_value=venta.numero_control):
            dte = generar_dte(venta, ambiente='00', generar_codigo=False, generar_numero_control=False)

        self.assertEqual(dte['identificacion']['version'], 2)
        self.assertEqual(dte['identificacion']['tipoDte'], '14')
        self.assertEqual(dte['identificacion']['fecEmi'], '2026-07-30')
        self.assertEqual(dte['identificacion']['horEmi'], '10:15:30')
        self.assertEqual(dte['receptor']['direccion']['departamento'], '06')
        self.assertEqual(dte['receptor']['direccion']['municipio'], '23')
        self.assertEqual(dte['receptor']['direccion']['distrito'], '14')
        self.assertEqual(len(dte['cuerpoDocumento']), 1)
        item = dte['cuerpoDocumento'][0]
        self.assertEqual(item['descripcion'], 'Servicio prueba')
        self.assertEqual(item['montoDescu'], 1.0)
        self.assertEqual(item['compra'], 19.0)
        # compra ya neta: no volver a restar descuentos de línea
        self.assertEqual(dte['resumen']['totalCompra'], 19.0)
        self.assertEqual(dte['resumen']['subTotal'], 19.0)
        self.assertEqual(dte['resumen']['totalDescu'], 1.0)


class DTE14ResumenTests(SimpleTestCase):
    def test_no_doble_descuento(self):
        empresa = SimpleNamespace(
            id=1, nit='06140101011019', nrc='123456-7', nombre='E',
            cod_actividad='62010', desc_actividad='S', departamento='06', municipio='23',
            distrito='14', direccion='X', telefono='22222222', correo='a@b.com',
            cod_establecimiento='M001', cod_punto_venta='P001',
        )
        doc = {
            'nit_proveedor': '012345678',
            'nombre_proveedor': 'Prov',
            'departamento_proveedor': '06',
            'municipio_proveedor': '23',
            'distrito_proveedor': '14',
            'direccion_proveedor': 'SS',
            'items': [{
                'numItem': 1, 'tipoItem': 1, 'cantidad': 1, 'codigo': 'A',
                'uniMedida': 59, 'descripcion': 'Item', 'precioUni': 100,
                'montoDescu': 10, 'compra': 90,
            }],
            'condicion_operacion': 1,
        }
        builder = DTE14Builder(doc, empresa)
        cuerpo = builder._construir_cuerpo_documento()
        resumen = builder._construir_resumen(cuerpo)
        self.assertEqual(resumen['totalCompra'], 90.0)
        self.assertEqual(resumen['descu'], 0.0)
        self.assertEqual(resumen['subTotal'], 90.0)
        self.assertEqual(resumen['totalDescu'], 10.0)
