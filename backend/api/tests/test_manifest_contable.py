"""Manifest contable: facturas registradas tarde, anulaciones tardías y datos del evento de anulación."""
import uuid
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from api.models import Empresa, PerfilUsuario, Venta
from api.services.facturacion_service import FacturacionService

SV = ZoneInfo('America/El_Salvador')
URL_MANIFEST = '/api/integraciones/contable/dte/manifest/'


def _sv(y, m, d, h=10):
    return datetime(y, m, d, h, 0, tzinfo=SV)


class ManifestContableFechasTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre='Empresa Prueba Manifest',
            nrc='9990001',
            ambiente='01',
            sync_contable_habilitado=True,
            sistema_contable_empresa_id=uuid.uuid4(),
        )
        user = get_user_model().objects.create_user(username='motor-test')
        PerfilUsuario.objects.create(user=user, empresa=self.empresa)
        self.client = APIClient()
        self.client.force_authenticate(user)

    def _venta(self, *, emision, registro, estado='AceptadoMH', anulacion=None):
        v = Venta.objects.create(
            empresa=self.empresa,
            fecha_emision=emision,
            periodo_aplicado=emision.strftime('%Y-%m'),
            tipo_venta='CF',
            ambiente_emision='01',
            estado_dte=estado,
            codigo_generacion=str(uuid.uuid4()).upper(),
        )
        Venta.objects.filter(id=v.id).update(fecha_registro=registro, fecha_anulacion=anulacion)
        return v.codigo_generacion

    def _manifest(self):
        r = self.client.get(URL_MANIFEST, {
            'empresa_id': self.empresa.id, 'desde': '2026-09-01', 'hasta': '2026-09-30',
        })
        self.assertEqual(r.status_code, 200, r.content)
        return {i['codigo_generacion']: i for i in r.json()['items']}

    def test_emision_en_rango_aparece(self):
        cod = self._venta(emision=date(2026, 9, 10), registro=_sv(2026, 9, 10))
        self.assertIn(cod, self._manifest())

    def test_registro_tardio_con_emision_anterior_aparece(self):
        cod = self._venta(emision=date(2026, 8, 20), registro=_sv(2026, 9, 15))
        item = self._manifest()[cod]
        self.assertEqual(item['fecha_emision'], '2026-08-20')
        self.assertEqual(item['fecha_registro'], '2026-09-15')
        self.assertIsNone(item['fecha_anulacion'])

    def test_anulacion_tardia_de_emision_antigua_aparece(self):
        cod = self._venta(
            emision=date(2026, 6, 5), registro=_sv(2026, 6, 5),
            estado='Anulado', anulacion=_sv(2026, 9, 20),
        )
        item = self._manifest()[cod]
        self.assertEqual(item['estado'], 'Anulado')
        self.assertEqual(item['fecha_anulacion'], '2026-09-20')

    def test_sin_coincidencia_no_aparece(self):
        fuera = self._venta(emision=date(2026, 7, 1), registro=_sv(2026, 7, 1))
        anulado_historico = self._venta(
            emision=date(2026, 6, 1), registro=_sv(2026, 6, 1), estado='Anulado',
        )
        items = self._manifest()
        self.assertNotIn(fuera, items)
        self.assertNotIn(anulado_historico, items)

    def test_fecha_registro_se_evalua_en_hora_de_el_salvador(self):
        # 2026-09-01 03:00 UTC = 2026-08-31 21:00 en El Salvador: fuera del rango.
        cod = self._venta(
            emision=date(2026, 8, 31),
            registro=datetime(2026, 9, 1, 3, 0, tzinfo=ZoneInfo('UTC')),
        )
        self.assertNotIn(cod, self._manifest())


class InvalidacionProcesadoTests(TestCase):
    def test_procesado_guarda_datos_de_anulacion(self):
        empresa = Empresa.objects.create(
            nombre='Empresa Prueba Anulacion', nrc='9990002', ambiente='01',
            user_api_mh='06140101011011', clave_api_mh='clave-prueba',
        )
        venta = Venta.objects.create(
            empresa=empresa, fecha_emision=date(2026, 6, 5), periodo_aplicado='2026-06',
            tipo_venta='CF', ambiente_emision='01', estado_dte='AceptadoMH',
            codigo_generacion=str(uuid.uuid4()).upper(), sello_recepcion='A' * 40,
            numero_control='DTE-01-M001P001-000000000000001',
        )
        resp_mh = SimpleNamespace(
            status_code=200,
            json=lambda: {'estado': 'PROCESADO', 'selloRecibido': 'SELLO-ANULACION-MH'},
            text='',
        )
        servicio = FacturacionService(empresa)
        with patch.object(servicio, 'firmar_dte', return_value='jws-evento'), \
                patch.object(servicio, 'obtener_token', return_value='Bearer x'), \
                patch('api.services.facturacion_service._receptor_anulacion_desde_venta',
                      return_value=(None, '012345678', True)), \
                patch('api.services.facturacion_service.requests.post', return_value=resp_mh) as post:
            resultado = servicio.invalidar_dte(venta, {'tipoInvalidacion': 'Rescisión'})

        self.assertTrue(resultado['exito'])
        venta.refresh_from_db()
        enviado = post.call_args.kwargs['json']
        self.assertEqual(venta.estado_dte, 'Anulado')
        self.assertIsNotNone(venta.fecha_anulacion)
        self.assertEqual(venta.codigo_generacion_anulacion, enviado['codigoGeneracion'])
        self.assertEqual(venta.sello_anulacion, 'SELLO-ANULACION-MH')
