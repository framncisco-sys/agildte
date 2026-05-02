# Programador: Oscar Amaya Romero
"""
Contrato POS → AgilDTE (payload hacia VentaConDetallesSerializer).

Ejecutar desde la carpeta SistemaPOs:
  python -m unittest azdigital.integration.test_agildte_payload_contract -v

Prueba en vivo contra staging (opcional): define AGILDTE_CONTRACT_LIVE=1 y credenciales;
si falla la red o el serializer, el test se marca skipped o falla con el cuerpo de error.
"""
from __future__ import annotations

import os
import unittest

from azdigital.integration.agildte_client import (
    AgilDTEAPIError,
    AgilDTEAuthError,
    AgilDTEClient,
    build_crear_venta_con_detalles_payload,
    map_tipo_comprobante_pos_a_tipo_dte,
    map_tipo_comprobante_pos_a_tipo_venta,
    receptor_anidado_a_campos_serializer,
)


def _linea(pid: int, cant: float = 1.0, pu: float = 1.15, st: float | None = None):
    st = st if st is not None else round(cant * pu, 2)
    return {"producto_id": pid, "cantidad": cant, "precio_unitario": pu, "subtotal": st}


class BuildPayloadContractTests(unittest.TestCase):
    """Casos: CF sin cliente, CF con receptor anidado, CCF con cliente_id."""

    def test_cf_sin_cliente_coherente_tipo_dte_y_sin_receptor_anidado(self):
        p = build_crear_venta_con_detalles_payload(
            empresa_id=1,
            tipo_comprobante_pos="FACTURA",
            tipo_pago="EFECTIVO",
            lineas=[_linea(101)],
            total_neto=1.15,
            total_bruto=1.15,
            descuento=0.0,
            cliente_id=None,
            cliente_nombre_ticket="Consumidor Final",
            receptor=None,
            venta_local_id=999,
        )
        self.assertEqual(p.get("tipo_dte"), "01")
        self.assertEqual(p.get("tipo_venta"), "CF")
        self.assertNotIn("receptor", p)
        self.assertNotIn("receptor_nombre", p)
        self.assertEqual(p.get("nombre_receptor"), "Consumidor Final")
        self.assertIsNone(p.get("cliente_id"))
        d0 = p["detalles"][0]
        self.assertIn("producto_id", d0)
        self.assertNotIn("producto", d0)

    def test_ticket_es_cf(self):
        p = build_crear_venta_con_detalles_payload(
            empresa_id=1,
            tipo_comprobante_pos="TICKET",
            tipo_pago="EFECTIVO",
            lineas=[_linea(10)],
            total_neto=5.0,
            total_bruto=5.0,
            descuento=0.0,
            cliente_id=None,
            cliente_nombre_ticket="Cliente mostrador",
            receptor=None,
        )
        self.assertEqual(map_tipo_comprobante_pos_a_tipo_dte("TICKET"), "01")
        self.assertEqual(p["tipo_venta"], "CF")

    def test_cf_con_datos_receptor_planos(self):
        rec = {
            "nombre": "Juan Pérez",
            "tipo_documento": "DUI",
            "numero_documento": "123456789",
            "correo": "juan@test.sv",
            "direccion": "San Salvador",
            "telefono": "70001234",
        }
        p = build_crear_venta_con_detalles_payload(
            empresa_id=1,
            tipo_comprobante_pos="FACTURA",
            tipo_pago="EFECTIVO",
            lineas=[_linea(55)],
            total_neto=10.0,
            total_bruto=10.0,
            descuento=0.0,
            cliente_id=None,
            cliente_nombre_ticket="Temporal",
            receptor=rec,
        )
        self.assertNotIn("receptor", p)
        self.assertEqual(p["nombre_receptor"], "Juan Pérez")
        self.assertEqual(p["tipo_doc_receptor"], "DUI")
        self.assertEqual(p["documento_receptor"], "123456789")
        self.assertEqual(p["receptor_correo"], "juan@test.sv")
        self.assertEqual(p["receptor_direccion"], "San Salvador")
        self.assertEqual(p["receptor_telefono"], "70001234")

    def test_ccf_con_cliente_id(self):
        p = build_crear_venta_con_detalles_payload(
            empresa_id=2,
            tipo_comprobante_pos="CREDITO_FISCAL",
            tipo_pago="TRANSFERENCIA",
            lineas=[_linea(200, cant=2.0, pu=50.0, st=100.0)],
            total_neto=100.0,
            total_bruto=100.0,
            descuento=0.0,
            cliente_id=42,
            cliente_nombre_ticket="ACME SA",
            receptor={"nombre": "ACME", "numero_documento": "0614-123456-101-1"},
        )
        self.assertEqual(p.get("tipo_dte"), "03")
        self.assertEqual(p.get("tipo_venta"), "CCF")
        self.assertEqual(map_tipo_comprobante_pos_a_tipo_venta("CREDITO_FISCAL"), "CCF")
        self.assertEqual(p.get("cliente_id"), 42)
        self.assertEqual(p.get("cliente"), 42)


class ReceptorFlatTests(unittest.TestCase):
    def test_vacio(self):
        self.assertEqual(receptor_anidado_a_campos_serializer(None), {})
        self.assertEqual(receptor_anidado_a_campos_serializer({}), {})


class LoginEmpresaMergeTests(unittest.TestCase):
    def test_merge_root_empresa_default(self):
        from azdigital.integration.agildte_client import _merge_empresa_login_context

        data = {
            "access": "x",
            "user": {"id": 1, "username": "u"},
            "empresa_default": {"id": 7, "nombre": "Empresa Test"},
        }
        d, ids = _merge_empresa_login_context(data, data["user"])
        self.assertEqual(d, 7)
        self.assertIn(7, ids)


@unittest.skipUnless(
    os.environ.get("AGILDTE_CONTRACT_LIVE", "").strip().lower() in ("1", "true", "yes"),
    "Defina AGILDTE_CONTRACT_LIVE=1 y AGILDTE_BASE_URL, AGILDTE_USERNAME, AGILDTE_PASSWORD para probar contra API real.",
)
class AgilDTELiveSerializerContractTests(unittest.TestCase):
    """
    Envía los tres payloads a crear-con-detalles y espera HTTP != 400 por serializer.
    Puede crear ventas reales en staging: usar solo entorno de pruebas.
    """

    def test_live_crear_venta_responses(self):
        from azdigital.integration.agildte_client import login_client_from_env

        try:
            cli = login_client_from_env()
        except AgilDTEAuthError as e:
            self.skipTest(f"Login AgilDTE: {e}")

        eid = cli.empresa_id
        if eid is None:
            self.skipTest("Sin empresa_id tras login; defina AGILDTE_EMPRESA_ID o perfil con empresa.")

        cases = [
            (
                "cf_sin_cliente",
                build_crear_venta_con_detalles_payload(
                    empresa_id=int(eid),
                    tipo_comprobante_pos="FACTURA",
                    tipo_pago="EFECTIVO",
                    lineas=[_linea(1)],
                    total_neto=0.01,
                    total_bruto=0.01,
                    descuento=0.0,
                    cliente_id=None,
                    cliente_nombre_ticket="CF Prueba POS",
                    receptor=None,
                    venta_local_id=None,
                ),
            ),
            (
                "cf_con_receptor",
                build_crear_venta_con_detalles_payload(
                    empresa_id=int(eid),
                    tipo_comprobante_pos="FACTURA",
                    tipo_pago="EFECTIVO",
                    lineas=[_linea(1)],
                    total_neto=0.01,
                    total_bruto=0.01,
                    descuento=0.0,
                    cliente_id=None,
                    cliente_nombre_ticket="Ignorado",
                    receptor={
                        "nombre": "Receptor manual",
                        "tipo_documento": "NIT",
                        "numero_documento": "0614-000000-000-0",
                    },
                ),
            ),
        ]

        cliente_mh = (os.environ.get("AGILDTE_CONTRACT_CLIENTE_ID") or "").strip()
        if cliente_mh.isdigit():
            cases.append(
                (
                    "ccf_con_cliente",
                    build_crear_venta_con_detalles_payload(
                        empresa_id=int(eid),
                        tipo_comprobante_pos="CREDITO_FISCAL",
                        tipo_pago="EFECTIVO",
                        lineas=[_linea(1)],
                        total_neto=0.01,
                        total_bruto=0.01,
                        descuento=0.0,
                        cliente_id=int(cliente_mh),
                        cliente_nombre_ticket="Cliente CCF",
                        receptor=None,
                    ),
                )
            )

        for name, body in cases:
            with self.subTest(case=name):
                try:
                    cli.crear_venta_con_detalles(body)
                except AgilDTEAPIError as ex:
                    if ex.status_code == 400:
                        self.fail(f"Serializer 400 en {name}: {ex.body}")
                    self.skipTest(f"{name}: API HTTP {ex.status_code} — {ex}")
                except Exception as ex:
                    self.skipTest(f"{name}: {ex}")


class GenerarDteUsesGetTests(unittest.TestCase):
    def test_generar_dte_llama_get_json(self):
        from unittest.mock import patch

        cli = AgilDTEClient(base_url="https://example.com", empresa_id=1)
        cli._access = "token"  # noqa: SLF001
        with patch.object(AgilDTEClient, "get_json", return_value={"venta_id": 99}) as gj:
            r = cli.generar_dte_venta(99)
        self.assertEqual(r, {"venta_id": 99})
        gj.assert_called_once()
        path = gj.call_args[0][0]
        self.assertIn("generar-dte", path)
        self.assertIn("99", path)


if __name__ == "__main__":
    unittest.main()
