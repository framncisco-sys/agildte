# Contrato de seguridad AgilDTE ↔ PosAgil (TDD).
# Ejecutar: cd SistemaPOs && python -m unittest azdigital.integration.test_agildte_security -v
from __future__ import annotations

import importlib.util
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("AZ_DEBUG", "1")

_FLASK_AVAILABLE = importlib.util.find_spec("flask") is not None


@unittest.skipUnless(_FLASK_AVAILABLE, "Requiere flask instalado (entorno SistemaPOs)")
class LoginClientBearerBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import create_app

        cls.app = create_app()

    def test_no_usa_authorization_header_si_trust_request_bearer_false(self):
        from azdigital.integration import agildte_client as m

        with self.app.test_request_context():
            from flask import session

            session["agildte_access_token"] = "sess-tok"
            session["empresa_id"] = 1
            with patch.object(m, "_bearer_desde_cabecera_authorization", return_value="evil-tok"), patch.object(
                m, "client_with_bearer_and_empresa", side_effect=lambda t, e, **kw: MagicMock(_access=t)
            ) as cwb:
                m.login_client_from_request_or_env(trust_request_bearer=False)
            cwb.assert_called_once()
            self.assertEqual(cwb.call_args[0][0], "sess-tok")

    def test_usa_header_solo_si_trust_request_bearer_true_y_sin_sesion(self):
        from azdigital.integration import agildte_client as m

        with self.app.test_request_context():
            from flask import session

            session.clear()
            session["empresa_id"] = 1
            with patch.object(m, "_bearer_desde_cabecera_authorization", return_value="header-tok"), patch.object(
                m, "client_with_bearer_and_empresa", side_effect=lambda t, e, **kw: MagicMock(_access=t)
            ) as cwb:
                m.login_client_from_request_or_env(trust_request_bearer=True)
            self.assertEqual(cwb.call_args[0][0], "header-tok")


class PublicSyncResultTests(unittest.TestCase):
    def test_elimina_detalle_y_crear_respuesta(self):
        from azdigital.integration.agildte_client import public_sync_result

        raw = {
            "ok": False,
            "error": "api",
            "mensaje": "Error API (400): campo inválido",
            "mensaje_usuario": "campo inválido",
            "detalle": {"secret": "internal", "password": "x"},
            "crear_respuesta": {"venta": {"id": 1}},
            "status": 400,
        }
        pub = public_sync_result(raw)
        self.assertNotIn("detalle", pub)
        self.assertNotIn("crear_respuesta", pub)
        self.assertNotIn("status", pub)
        self.assertEqual(pub["mensaje_usuario"], "campo inválido")
        self.assertFalse(pub["ok"])


class SyncVentaLeakTests(unittest.TestCase):
    def test_respuesta_api_error_no_incluye_detalle(self):
        from azdigital.integration.agildte_client import (
            AgilDTEAPIError,
            _format_api_error_body,
            public_sync_result,
        )

        err = AgilDTEAPIError("fail", status_code=400, body={"internal_field": "secret"})
        mu = (_format_api_error_body(err.body) or "").strip() or "No se pudo sincronizar la venta con AgilDTE."
        out = public_sync_result({"ok": False, "error": "api", "mensaje_usuario": mu[:500], "detalle": err.body})
        self.assertNotIn("detalle", out)
        self.assertIn("mensaje_usuario", out)


@unittest.skipUnless(_FLASK_AVAILABLE, "Requiere flask instalado (entorno SistemaPOs)")
class AuthAgildteRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import create_app

        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_get_con_token_en_query_no_guarda_sesion(self):
        r = self.client.get("/auth/agildte?access_token=leaked-jwt")
        self.assertIn(r.status_code, (302, 303))
        with self.client.session_transaction() as sess:
            self.assertNotEqual(sess.get("agildte_access_token"), "leaked-jwt")


@unittest.skipUnless(_FLASK_AVAILABLE, "Requiere flask instalado (entorno SistemaPOs)")
class VentasPosTemplateSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import create_app

        cls.app = create_app()
        cls.client = cls.app.test_client()

    @patch("azdigital.routes.pos.render_template")
    @patch("azdigital.decorators._rol_desde_bd", return_value="CAJERO")
    def test_no_pasa_jwt_al_template(self, _rol, render_tpl):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "u1"
            sess["rol"] = "CAJERO"
            sess["empresa_id"] = 1
            sess["agildte_access_token"] = "eyJ.must.not.appear"
        self.client.get("/ventas_pos")
        render_tpl.assert_called_once()
        kwargs = render_tpl.call_args[1]
        self.assertNotIn("agildte_bearer_para_fetch", kwargs)


if __name__ == "__main__":
    unittest.main()
