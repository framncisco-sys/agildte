"""IP de cliente y eventos de auditoría (sin persistir contraseñas)."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from api.models import RegistroAuditoria
from api.utils.auditoria import client_ip, registrar_evento


class ClientIpTests(SimpleTestCase):
    def test_prioriza_x_forwarded_for(self):
        req = SimpleNamespace(
            META={
                "HTTP_X_FORWARDED_FOR": "201.54.1.10, 10.0.0.1",
                "HTTP_X_REAL_IP": "10.0.0.1",
                "REMOTE_ADDR": "127.0.0.1",
            }
        )
        self.assertEqual(client_ip(req), "201.54.1.10")

    def test_sin_request_vacio(self):
        self.assertEqual(client_ip(None), "")


class RegistrarEventoTests(SimpleTestCase):
    def test_login_fallo_guarda_usuario_e_ip_no_password(self):
        created = {}

        class _QS:
            @staticmethod
            def create(**kwargs):
                created.update(kwargs)
                return SimpleNamespace(**kwargs)

        req = SimpleNamespace(
            META={
                "HTTP_X_FORWARDED_FOR": "190.86.20.5",
                "HTTP_USER_AGENT": "Mozilla/5.0",
            }
        )
        with patch.object(RegistroAuditoria.objects, "create", _QS.create):
            registrar_evento(
                evento=RegistroAuditoria.EVENTO_LOGIN_FALLO,
                username="cajero1",
                detalle="Credenciales inválidas",
                request=req,
            )
        self.assertEqual(created["evento"], "LOGIN_FALLO")
        self.assertEqual(created["username"], "cajero1")
        self.assertEqual(created["ip_address"], "190.86.20.5")
        self.assertNotIn("password", created)
        self.assertNotIn("clave", (created.get("detalle") or "").lower())
