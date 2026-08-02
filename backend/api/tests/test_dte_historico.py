"""Pruebas de preservación del JSON histórico aceptado por MH."""
import base64
import json
from types import SimpleNamespace

from django.test import SimpleTestCase

from api.utils.dte_historico import decodificar_payload_jws, obtener_dte_historico


def _jws_de(payload):
    header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').decode().rstrip('=')
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(',', ':')).encode()
    ).decode().rstrip('=')
    return f'{header}.{body}.firma'


class DteHistoricoTests(SimpleTestCase):
    def test_recupera_version_y_contenido_originales(self):
        original = {
            'identificacion': {'version': 1, 'tipoDte': '14'},
            'receptor': {'nombre': 'Proveedor histórico'},
        }
        jws = _jws_de(original)
        venta = SimpleNamespace(dte_firmado=jws, sello_recepcion='SELLO-MH')

        recuperado = obtener_dte_historico(venta)

        self.assertEqual(recuperado['identificacion']['version'], 1)
        self.assertEqual(recuperado['receptor']['nombre'], 'Proveedor histórico')
        self.assertEqual(recuperado['firmaElectronica'], jws)
        self.assertEqual(recuperado['selloRecibido'], 'SELLO-MH')

    def test_jws_invalido_no_inventa_documento(self):
        self.assertIsNone(decodificar_payload_jws('contenido-no-jws'))
        venta = SimpleNamespace(dte_firmado='invalido', sello_recepcion='SELLO')
        self.assertIsNone(obtener_dte_historico(venta))
