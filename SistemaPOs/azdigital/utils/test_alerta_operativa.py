# Programador: Oscar Amaya Romero
"""Debounce de alertas: no reenvía dentro del cooldown."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from azdigital.utils import alerta_operativa as ao


class AlertaOperativaTests(unittest.TestCase):
    def test_modo_local_asunto_y_destino(self):
        sent = {}

        def _fake(asunto, cuerpo):
            sent["asunto"] = asunto
            sent["cuerpo"] = cuerpo
            return True

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                "os.environ",
                {"ALERT_STATE_DIR": tmp, "ALERT_COOLDOWN_SEG": "1800", "ALERT_EMAIL": "framncisco@gmail.com"},
            ):
                with patch.object(ao, "_enviar_smtp", _fake):
                    ok = ao.alertar_modo_local("sync falló", "venta #12", forzar=True)
        self.assertTrue(ok)
        self.assertIn("modo local", sent["asunto"].lower())
        self.assertIn("Problema:", sent["cuerpo"])
        self.assertIn("sync falló", sent["cuerpo"])

    def test_cooldown_no_reenvia(self):
        n = {"c": 0}

        def _fake(asunto, cuerpo):
            n["c"] += 1
            return True

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(ao, "_state_dir", lambda: Path(tmp)):
                with patch.object(ao, "COOLDOWN_SEG", 1800):
                    with patch.object(ao, "_enviar_smtp", _fake):
                        self.assertTrue(ao.alertar_modo_local("a", forzar=False))
                        self.assertFalse(ao.alertar_modo_local("a", forzar=False))
        self.assertEqual(n["c"], 1)


if __name__ == "__main__":
    unittest.main()
