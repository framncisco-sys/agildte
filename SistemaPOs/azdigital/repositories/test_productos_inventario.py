# Programador: Oscar Amaya Romero
"""Búsqueda de inventario: no debe limitarse a las 500 filas ya pintadas."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from azdigital.repositories.productos_repo import (
    _sql_filtro_busqueda_inventario,
    _sql_orden_inventario,
)


class _CurSinPresentaciones:
    def __init__(self):
        self.connection = MagicMock()

    def execute(self, sql, params=None):
        self.last_sql = sql

    def fetchone(self):
        return None


class FiltroBusquedaInventarioTests(unittest.TestCase):
    def test_vacio_no_filtra(self):
        sql, params = _sql_filtro_busqueda_inventario(_CurSinPresentaciones(), "  ")
        self.assertEqual(sql, "")
        self.assertEqual(params, [])

    def test_busca_nombre_y_codigo(self):
        sql, params = _sql_filtro_busqueda_inventario(_CurSinPresentaciones(), "Café")
        self.assertIn("p.nombre", sql)
        self.assertIn("p.codigo_barra", sql)
        self.assertTrue(any("Café" in str(p) or "Cafe" in str(p) for p in params))
        self.assertIn("REPLACE", sql)

    def test_empresa_incluye_null(self):
        from azdigital.repositories.productos_repo import _alcance_empresa_inventario

        sql, params = _alcance_empresa_inventario(3)
        self.assertIn("empresa_id IS NULL", sql)
        self.assertEqual(params, [3])

    def test_pos_no_toma_catalogo_de_otra_empresa(self):
        from pathlib import Path

        src = Path(__file__).resolve().parents[1].joinpath("routes", "pos.py").read_text(encoding="utf-8")
        self.assertNotIn("ORDER BY COUNT(*) DESC", src)
        self.assertIn("Nunca toma el catálogo de otra empresa", src)

    def test_inventario_no_amplia_busqueda_a_otras_empresas(self):
        from pathlib import Path

        admin_src = Path(__file__).resolve().parents[1].joinpath("routes", "admin.py").read_text(
            encoding="utf-8"
        )
        tpl = Path(__file__).resolve().parents[2].joinpath("templates", "inventario.html").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("alcance_ampliado", admin_src)
        self.assertNotIn("todas las empresas", tpl)
        self.assertIn("Nunca toma el catálogo de otra empresa", Path(__file__).resolve().parents[1].joinpath("routes", "pos.py").read_text(encoding="utf-8"))

    def test_kardex_filtra_por_empresa(self):
        from pathlib import Path

        src = Path(__file__).resolve().parents[1].joinpath(
            "repositories", "inventario_reports_repo.py"
        ).read_text(encoding="utf-8")
        self.assertIn("k.empresa_id = %s", src)

    def test_orden_con_busqueda_es_por_nombre(self):
        self.assertIn("UPPER(p.nombre)", _sql_orden_inventario("leche"))
        self.assertIn("p.id DESC", _sql_orden_inventario(""))


if __name__ == "__main__":
    unittest.main()
