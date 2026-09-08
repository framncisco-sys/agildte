"""Identidad MH de ítems DTE-01 (código 003: cálculo de total por ítem)."""
from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from api.utils.builders.dte_01_builder import DTE01Builder
from api.utils.mh_item_totales import (
    alinear_detalles_cf_al_cobro,
    alinear_precio_a_total,
    cobro_con_iva_detalle,
    forzar_identidad_mh_item,
    iva_item_cf,
    linea_mh_coherente,
    montos_item_dte01_gravado,
    total_con_iva_linea_cf,
    total_linea_mh,
)


def _qs(items):
    class _Detalles:
        def all(self):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def exists(self):
            return True

        def __iter__(self):
            return iter(items)

    return _Detalles()


class MhItemTotalesTests(SimpleTestCase):
    def test_produccion_3_30_tres_unidades(self):
        """DTE ...338 RECHAZADO: 3 × $1.10 = $3.30 cobrado en POS."""
        m = montos_item_dte01_gravado(
            cantidad=3,
            precio_unitario_bd=Decimal('0.97'),
            venta_gravada_bd=Decimal('2.92'),
            iva_item_bd=Decimal('0.38'),
            monto_descuento=0,
        )
        self.assertEqual(m['ventaGravada'], 3.30)
        self.assertTrue(linea_mh_coherente(m))
        self.assertEqual(m['ivaItem'], iva_item_cf(3.30))
        self.assertEqual(total_linea_mh(m['precioUni'], m['cantidad']), 3.30)

    def test_produccion_13_20_doce_unidades(self):
        m = montos_item_dte01_gravado(
            cantidad=12,
            precio_unitario_bd=Decimal('0.97'),
            venta_gravada_bd=Decimal('11.68'),
            iva_item_bd=Decimal('1.52'),
            monto_descuento=0,
        )
        self.assertEqual(m['ventaGravada'], 13.20)
        self.assertTrue(linea_mh_coherente(m))

    def test_cantidad_que_no_divide_en_2_decimales(self):
        m = montos_item_dte01_gravado(
            cantidad=7,
            precio_unitario_bd=Decimal('0.41'),
            venta_gravada_bd=Decimal('2.92'),
            iva_item_bd=Decimal('0.38'),
            monto_descuento=0,
        )
        self.assertEqual(m['ventaGravada'], 3.30)
        self.assertTrue(linea_mh_coherente(m))
        self.assertNotEqual(round(m['precioUni'], 2), m['precioUni'])

    def test_payload_pos_sin_desglose_usa_subtotal(self):
        total = total_con_iva_linea_cf(3, 1.10, subtotal=3.30, venta_gravada=0, iva_item=0)
        self.assertEqual(total, Decimal('3.30'))

    def test_payload_portal_cf_usa_desglose(self):
        # Portal: precio SIN IVA, venta_gravada + iva = cobro
        total = total_con_iva_linea_cf(
            3, 0.97, subtotal=None, venta_gravada=2.92, iva_item=0.38,
        )
        self.assertEqual(total, Decimal('3.30'))


class DTE01BuilderItemTests(SimpleTestCase):
    def _builder_con_detalle(self, **detalle_fields):
        producto = SimpleNamespace(codigo='P1', descripcion='Producto POS', tipo_item=1)
        detalle = SimpleNamespace(
            numero_item=1,
            producto=producto,
            codigo_libre=None,
            descripcion_libre=None,
            monto_descuento=Decimal('0.00'),
            venta_exenta=Decimal('0.00'),
            venta_no_sujeta=Decimal('0.00'),
            **detalle_fields,
        )
        venta = SimpleNamespace(
            cliente=None,
            nombre_receptor='Cliente de contado',
            iva_retenido_1=0,
            observaciones='',
            condicion_operacion=1,
            plazo_pago='',
            periodo_pago='',
            venta_gravada=detalle.venta_gravada,
            detalles=_qs([detalle]),
        )
        b = DTE01Builder.__new__(DTE01Builder)
        b.venta = venta
        return b

    def test_item_3x1_10_no_rompe_identidad_mh(self):
        b = self._builder_con_detalle(
            cantidad=Decimal('3.00'),
            precio_unitario=Decimal('0.97333333'),
            venta_gravada=Decimal('2.92'),
            iva_item=Decimal('0.38'),
        )
        cuerpo = b._construir_cuerpo_documento()
        self.assertEqual(len(cuerpo), 1)
        item = cuerpo[0]
        self.assertTrue(linea_mh_coherente(item), item)
        self.assertEqual(item['ventaGravada'], 3.30)
        self.assertEqual(item['ivaItem'], iva_item_cf(3.30))
        resumen = b._construir_resumen(cuerpo)
        self.assertEqual(resumen['totalPagar'], 3.30)

    def test_bug_legacy_precio_2_decimales_ya_no_descuadra(self):
        """El round-trip antiguo 0.97×3×1.13 daba ventaGravada 3.29 y precioUni 1.10."""
        b = self._builder_con_detalle(
            cantidad=Decimal('3.00'),
            precio_unitario=Decimal('0.97'),
            venta_gravada=Decimal('2.92'),
            iva_item=Decimal('0.38'),
        )
        item = b._construir_cuerpo_documento()[0]
        calc = round(item['precioUni'] * item['cantidad'] - item['montoDescu'], 2)
        self.assertEqual(calc, item['ventaGravada'])
        self.assertEqual(item['ventaGravada'], 3.30)


class MhCodigo003RegresionTests(SimpleTestCase):
    """Rechazos reales: DTE 0338, POS 788 (250×$0.044) y POS 807 (3×$0.35 vs $1.00)."""

    def test_788_250_bolsas_agua_mantiene_cobro_11(self):
        m = montos_item_dte01_gravado(
            cantidad=250,
            precio_unitario_bd=Decimal('0.03893805'),
            venta_gravada_bd=Decimal('9.73'),
            iva_item_bd=Decimal('1.27'),
            monto_descuento=0,
        )
        self.assertEqual(m['ventaGravada'], 11.00)
        self.assertTrue(linea_mh_coherente(m), m)
        self.assertEqual(total_linea_mh(m['precioUni'], m['cantidad']), 11.00)
        # Redondear precioUni a 2 decimales era el 003: 250×0.04=$10.00
        self.assertNotEqual(round(m['precioUni'], 2) * 250, 11.00)

    def test_alinear_precio_no_tira_el_cobro(self):
        pu, total = alinear_precio_a_total(250, 11.00, 0)
        self.assertEqual(total, 11.00)
        self.assertEqual(total_linea_mh(pu, 250), 11.00)

    def test_807_alinea_lineas_al_cobro_de_caja(self):
        linea = SimpleNamespace(
            cantidad=Decimal('3.00'),
            precio_unitario=Decimal('0.31000000'),
            venta_gravada=Decimal('0.93'),
            iva_item=Decimal('0.12'),
            venta_exenta=Decimal('0.00'),
            venta_no_sujeta=Decimal('0.00'),
        )
        self.assertEqual(cobro_con_iva_detalle(linea), Decimal('1.05'))
        self.assertTrue(alinear_detalles_cf_al_cobro([linea], Decimal('1.00')))
        self.assertEqual(cobro_con_iva_detalle(linea), Decimal('1.00'))

    def test_807_identidad_mh_con_cobro_1_00(self):
        m = montos_item_dte01_gravado(
            cantidad=3,
            precio_unitario_bd=Decimal('0.29498584'),
            venta_gravada_bd=Decimal('0.88'),
            iva_item_bd=Decimal('0.12'),
            monto_descuento=0,
        )
        self.assertEqual(m['ventaGravada'], 1.00)
        self.assertTrue(linea_mh_coherente(m), m)
        self.assertEqual(total_linea_mh(m['precioUni'], m['cantidad']), 1.00)

    def test_forzar_identidad_corrige_precio_redondeado_a_2_decimales(self):
        item = {
            'cantidad': 250,
            'precioUni': 0.04,
            'montoDescu': 0.0,
            'ventaGravada': 11.00,
            'ventaExenta': 0.0,
            'ventaNoSuj': 0.0,
            'ivaItem': iva_item_cf(11.00),
        }
        self.assertFalse(linea_mh_coherente(item))
        forzar_identidad_mh_item(item)
        self.assertTrue(linea_mh_coherente(item), item)
        self.assertEqual(item['ventaGravada'], 11.00)

    def test_builder_788_identidad_mh(self):
        producto = SimpleNamespace(codigo='AGUA', descripcion='Bolsa de Agua Jordan', tipo_item=1)
        detalle = SimpleNamespace(
            numero_item=1,
            producto=producto,
            codigo_libre=None,
            descripcion_libre=None,
            monto_descuento=Decimal('0.00'),
            venta_exenta=Decimal('0.00'),
            venta_no_sujeta=Decimal('0.00'),
            cantidad=Decimal('250.00'),
            precio_unitario=Decimal('0.03893805'),
            venta_gravada=Decimal('9.73'),
            iva_item=Decimal('1.27'),
        )
        venta = SimpleNamespace(
            cliente=None,
            nombre_receptor='Cliente de contado',
            iva_retenido_1=0,
            observaciones='',
            condicion_operacion=1,
            plazo_pago='',
            periodo_pago='',
            venta_gravada=detalle.venta_gravada,
            detalles=_qs([detalle]),
        )
        b = DTE01Builder.__new__(DTE01Builder)
        b.venta = venta
        item = b._construir_cuerpo_documento()[0]
        self.assertTrue(linea_mh_coherente(item), item)
        self.assertEqual(item['ventaGravada'], 11.00)
