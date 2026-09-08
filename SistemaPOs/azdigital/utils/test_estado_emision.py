# Programador: Oscar Amaya Romero
"""Estado de emisión y bloqueo de re-remisión (Gestión de ventas)."""
from __future__ import annotations

import unittest

from azdigital.utils.estado_emision import clasificar_estado_emision, fila_gestion_venta


class ClasificarEstadoEmisionTests(unittest.TestCase):
    def test_sin_codigo_es_pendiente(self):
        st = clasificar_estado_emision("", "RESPALDO")
        self.assertEqual(st["clave"], "pendiente")
        self.assertEqual(st["etiqueta"], "Pendiente")

    def test_codigo_corto_sigue_pendiente(self):
        st = clasificar_estado_emision("ABC", None)
        self.assertEqual(st["clave"], "pendiente")

    def test_codigo_y_aceptado_es_procesado(self):
        st = clasificar_estado_emision("ABCDEFGHIJK", "PROCESADO")
        self.assertEqual(st["clave"], "procesado")

    def test_codigo_y_rechazado(self):
        st = clasificar_estado_emision("ABCDEFGHIJK", "RECHAZADO")
        self.assertEqual(st["clave"], "rechazado")

    def test_corregido_si_hacienda_acepto_nuevo(self):
        st = clasificar_estado_emision("ABCDEFGHIJK", "CORREGIDO")
        self.assertEqual(st["clave"], "corregido")
        self.assertEqual(st["etiqueta"], "Corregido")

    def test_corregido_antes_que_aceptado(self):
        st = clasificar_estado_emision("ABCDEFGHIJK", "CORREGIDO-ACEPTADO")
        self.assertEqual(st["clave"], "corregido")

    def test_codigo_sin_estado_conocido_es_agildte(self):
        st = clasificar_estado_emision("ABCDEFGHIJK", "RESPALDO")
        self.assertEqual(st["clave"], "agildte")


class FilaGestionVentaTests(unittest.TestCase):
    def test_pendiente_puede_remitir(self):
        row = (822, "30/08/2026 10:00", 3.30, "David", "EFECTIVO", "TICKET", None, "", "RESPALDO", "cajero1")
        f = fila_gestion_venta(row)
        self.assertTrue(f["puede_remitir"])
        self.assertFalse(f["en_agildte"])
        self.assertEqual(f["cajero"], "cajero1")
        self.assertEqual(f["etiqueta"], "Pendiente")

    def test_con_codigo_no_remite(self):
        row = (827, "30/08/2026 10:00", 13.20, "CF", "EFECTIVO", "FACTURA", None, "ABCDEFGHIJK", "PROCESADO", "ana")
        f = fila_gestion_venta(row)
        self.assertFalse(f["puede_remitir"])
        self.assertFalse(f["puede_reemitir"])
        self.assertTrue(f["en_agildte"])

    def test_rechazado_se_puede_corregir_no_lote(self):
        row = (830, "30/08/2026 10:00", 3.30, "David", "EFECTIVO", "TICKET", None, "ABCDEFGHIJK", "RECHAZADO", "cajero1")
        f = fila_gestion_venta(row)
        self.assertFalse(f["puede_remitir"])
        self.assertTrue(f["puede_reemitir"])
        self.assertTrue(f["puede_emitir"])
        self.assertEqual(f["etiqueta"], "Rechazado")

    def test_corregido_no_reemite(self):
        row = (831, "30/08/2026 10:00", 3.30, "David", "EFECTIVO", "TICKET", None, "ABCDEFGHIJK", "CORREGIDO", "cajero1")
        f = fila_gestion_venta(row)
        self.assertFalse(f["puede_emitir"])
        self.assertEqual(f["etiqueta"], "Corregido")

    def test_total_invalido_no_revienta(self):
        row = (1, "01/01/2026 10:00", "no-num", "CF", "EFECTIVO", "TICKET", None, "", "RESPALDO", "cajero")
        f = fila_gestion_venta(row)
        self.assertEqual(f["total"], 0.0)
        self.assertTrue(f["puede_remitir"])

    def test_acepta_dict(self):
        f = fila_gestion_venta({"id": 9, "fecha": "01/01/2026", "total": 1.5, "cliente": "A"})
        self.assertEqual(f["id"], 9)
        self.assertEqual(f["total"], 1.5)
        self.assertEqual(f["clave"], "pendiente")


class ListarVentasRecientesFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parents[1] / "repositories" / "ventas_repo.py"
        spec = importlib.util.spec_from_file_location("ventas_repo_listar_iso", path)
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def test_degrada_si_sql_falla_y_no_relanza(self):
        class _Cur:
            def __init__(self):
                self.n = 0
                self.connection = self
                self.rows = [(1, "01/01/2026 10:00", 1.1, "CF", "EFECTIVO", "TICKET", None, "", "RESPALDO", "-")]

            def rollback(self):
                pass

            def execute(self, sql, params=None):
                self.n += 1
                if "ambiente_emision" in (sql or "") or "LEFT JOIN usuarios" in (sql or ""):
                    raise Exception("column v.ambiente_emision does not exist")
                if "c.nombre_cliente" in (sql or ""):
                    raise Exception("column c.nombre_cliente does not exist")

            def fetchall(self):
                return self.rows

        cur = _Cur()
        rows = self.mod.listar_ventas_recientes(cur, empresa_id=1, limit=10, ambiente_emision="00")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], 1)
        self.assertGreaterEqual(cur.n, 2)

    def test_si_todo_falla_devuelve_lista_vacia(self):
        class _Cur:
            def __init__(self):
                self.connection = self

            def rollback(self):
                pass

            def execute(self, sql, params=None):
                raise Exception("current transaction is aborted")

            def fetchall(self):
                return []

        rows = self.mod.listar_ventas_recientes(_Cur(), empresa_id=1, limit=10)
        self.assertEqual(rows, [])


class RemitirVentaExistenteTests(unittest.TestCase):
    """La re-emisión se bloquea con clasificar_estado_emision (sin importar sync/psycopg2)."""

    def test_codigo_dte_procesado_no_es_emitible(self):
        st = clasificar_estado_emision("ABCDEFGHIJK", "PROCESADO")
        self.assertNotIn(st["clave"], ("pendiente", "rechazado"))

    def test_sin_codigo_si_es_pendiente(self):
        st = clasificar_estado_emision("", "RESPALDO")
        self.assertEqual(st["clave"], "pendiente")


if __name__ == "__main__":
    unittest.main()
