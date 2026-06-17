from django.test import SimpleTestCase

from api.utils.mh_documento import (
    documento_cliente_para_mh,
    documento_receptor_desde_payload,
    es_nrc_placeholder_mh,
    mensaje_ayuda_receptor_nrc_mh,
    normalizar_nrc_mh,
    normalizar_tipo_y_numero_mh,
)


class _ClienteStub:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MhDocumentoTests(SimpleTestCase):
    def test_dui_visual_sin_guion(self):
        t, n = normalizar_tipo_y_numero_mh("DUI", "04727688-8")
        self.assertEqual(t, "13")
        self.assertEqual(n, "047276888")

    def test_dui_en_campo_nit(self):
        c = _ClienteStub(tipo_documento="NIT", nit="04727688-8", dui=None)
        self.assertEqual(documento_cliente_para_mh(c), ("13", "047276888"))

    def test_payload_pos_dui(self):
        tipo, nit, dui, doc_id = documento_receptor_desde_payload("DUI", "04727688-8")
        self.assertEqual(tipo, "DUI")
        self.assertIsNone(nit)
        self.assertEqual(dui, "047276888")
        self.assertEqual(doc_id, "047276888")

    def test_nit_9_digitos_no_forzar_14_con_ceros(self):
        """Evita el antiguo zfill(14) que MH rechazaba como formato inválido."""
        t, n = normalizar_tipo_y_numero_mh("NIT", "04727688-8")
        self.assertEqual(t, "13")
        self.assertEqual(len(n), 9)

    def test_normalizar_nrc_con_guion(self):
        self.assertEqual(normalizar_nrc_mh("298441-4"), "2984414")

    def test_normalizar_nrc_corto_vidri(self):
        self.assertEqual(normalizar_nrc_mh("27"), "27")

    def test_nrc_placeholder(self):
        self.assertTrue(es_nrc_placeholder_mh("0000000"))

    def test_mensaje_ayuda_codigo_008(self):
        msg = mensaje_ayuda_receptor_nrc_mh("008", "[receptor.nrc] NO CORRESPONDE A CONTRIBUYENTE")
        self.assertIsNotNone(msg)
        self.assertIn("NRC", msg)
