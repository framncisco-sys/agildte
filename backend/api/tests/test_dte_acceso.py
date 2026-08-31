"""Aislamiento PDF/JSON DTE: no se abre factura de otra empresa por ID numérico."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from api.utils.dte_acceso import (
    coincidencia_documento_dte,
    evaluar_acceso_dte_venta,
)


def _venta(**kwargs):
    defaults = dict(
        pk=819,
        id=819,
        codigo_generacion="170EA36A-3508-4724-A094-844B4DB41555",
        numero_control="DTE-01-M001P001-0000000000000435",
        empresa_id=20,
        empresa=SimpleNamespace(id=20),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _request(*, authenticated=True, get=None, company_header=None):
    user = SimpleNamespace(is_authenticated=authenticated, pk=3, username="cajero")
    headers = {}
    if company_header is not None:
        headers["X-Company-ID"] = str(company_header)
    return SimpleNamespace(
        user=user,
        GET=get or {},
        META={},
        query_params=get or {},
        headers=headers,
    )


class CoincidenciaDocumentoTests(SimpleTestCase):
    def test_sin_codigo_ni_control_no_abre(self):
        self.assertFalse(coincidencia_documento_dte(_venta(), "", ""))

    def test_codigo_exacto(self):
        v = _venta()
        self.assertTrue(coincidencia_documento_dte(v, v.codigo_generacion, None))

    def test_numero_control_exacto(self):
        v = _venta()
        self.assertTrue(coincidencia_documento_dte(v, None, v.numero_control))

    def test_id_numerico_no_cuenta(self):
        v = _venta()
        self.assertFalse(coincidencia_documento_dte(v, "819", "819"))

    def test_codigo_de_otra_factura(self):
        v = _venta()
        self.assertFalse(coincidencia_documento_dte(v, "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE", None))


class EvaluarAccesoDteTests(SimpleTestCase):
    @patch("api.utils.dte_acceso.get_empresa_ids_allowlist", return_value=[10])
    def test_empresa_ajena_404(self, _allow):
        req = _request(get={"codigo_generacion": _venta().codigo_generacion, "empresa_id": "10"})
        resultado, code, body = evaluar_acceso_dte_venta(req, _venta(), recurso="pdf")
        self.assertEqual(resultado, "denegado_tenant")
        self.assertEqual(code, 404)
        self.assertEqual(body.get("error"), "No encontrado")

    @patch("api.utils.dte_acceso.get_empresa_ids_allowlist", return_value=[20])
    def test_sin_documento_404_aunque_sea_su_empresa(self, _allow):
        req = _request(get={"empresa_id": "20"})
        resultado, code, _body = evaluar_acceso_dte_venta(req, _venta(), recurso="pdf")
        self.assertEqual(resultado, "denegado_documento")
        self.assertEqual(code, 404)

    @patch("api.utils.dte_acceso.get_empresa_ids_allowlist", return_value=[20])
    def test_empresa_id_de_la_sesion_distinta_a_la_venta(self, _allow):
        v = _venta()
        req = _request(get={"codigo_generacion": v.codigo_generacion, "empresa_id": "99"})
        resultado, code, _body = evaluar_acceso_dte_venta(req, v, recurso="json")
        self.assertEqual(resultado, "denegado_empresa")
        self.assertEqual(code, 404)

    @patch("api.utils.dte_acceso.get_empresa_ids_allowlist", return_value=[20])
    def test_propia_empresa_con_codigo_ok(self, _allow):
        v = _venta()
        req = _request(get={"codigo_generacion": v.codigo_generacion, "empresa_id": "20"})
        resultado, code, body = evaluar_acceso_dte_venta(req, v, recurso="pdf")
        self.assertEqual(resultado, "ok")
        self.assertEqual(code, 200)
        self.assertEqual(body, {})

    def test_sin_login_401(self):
        v = _venta()
        req = _request(authenticated=False, get={"codigo_generacion": v.codigo_generacion})
        resultado, code, body = evaluar_acceso_dte_venta(req, v, recurso="pdf")
        self.assertEqual(resultado, "denegado_auth")
        self.assertEqual(code, 401)
        self.assertIn("Autenticación", body.get("error", ""))
