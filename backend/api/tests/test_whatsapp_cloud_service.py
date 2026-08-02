"""Tests unitarios — WhatsApp Cloud (sin llamar a Meta)."""
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from api.services.whatsapp_cloud_service import (
    MSG_WHATSAPP_NO_HABILITADO,
    WhatsAppCloudError,
    construir_enlace_descarga,
    construir_mensaje_factura,
    enviar_plantilla_factura_agildte,
    normalizar_telefono_meta,
    resolver_nis_factura,
)


class NormalizarTelefonoTests(SimpleTestCase):
    def test_ocho_digitos_sv(self):
        self.assertEqual(normalizar_telefono_meta('71234567'), '50371234567')

    def test_con_prefijo_503(self):
        self.assertEqual(normalizar_telefono_meta('+503 7123-4567'), '50371234567')


class MensajeFacturaTests(SimpleTestCase):
    def test_incluye_nombre_y_enlace(self):
        msg = construir_mensaje_factura(nombre_cliente='Juan', nis='ABC-123')
        self.assertIn('Juan', msg)
        self.assertIn('ABC-123', msg)
        self.assertIn('agildte.com', msg)

    def test_enlace_descarga(self):
        url = construir_enlace_descarga('UUID-99')
        self.assertIn('UUID-99', url)


class ResolverNisTests(SimpleTestCase):
    def test_usa_codigo_generacion(self):
        class V:
            pk = 9
            codigo_generacion = 'UUID-1'

        self.assertEqual(resolver_nis_factura(V()), 'UUID-1')

    def test_fallback_id(self):
        class V:
            pk = 9
            codigo_generacion = ''

        self.assertEqual(resolver_nis_factura(V()), '9')


class CredencialesCentralizadasTests(SimpleTestCase):
    def test_mensaje_modulo_no_habilitado(self):
        self.assertEqual(MSG_WHATSAPP_NO_HABILITADO, 'Módulo de WhatsApp no habilitado')

    @override_settings(WHATSAPP_PHONE_NUMBER_ID='', WHATSAPP_ACCESS_TOKEN='')
    def test_sin_credenciales_servidor(self):
        with self.assertRaises(WhatsAppCloudError) as ctx:
            enviar_plantilla_factura_agildte(
                telefono='71234567',
                nombre_cliente='Ana',
                codigo_generacion='CG-1',
            )
        self.assertEqual(ctx.exception.status_code, 503)

    @override_settings(
        WHATSAPP_PHONE_NUMBER_ID='123456',
        WHATSAPP_ACCESS_TOKEN='token-test',
        WHATSAPP_TEMPLATE_NAME='agildte_factura',
        WHATSAPP_TEMPLATE_LANGUAGE='es',
        WHATSAPP_TEMPLATE_BODY_PARAMS=2,
        WHATSAPP_GRAPH_API_VERSION='v18.0',
        WHATSAPP_FACTURA_DOWNLOAD_URL='https://example.com/d?nis={nis}',
    )
    @patch('api.services.whatsapp_cloud_service._post_meta_messages')
    def test_plantilla_con_nombre_y_enlace(self, mock_post):
        mock_post.return_value = {'messages': [{'id': 'wamid.TEST'}]}
        out = enviar_plantilla_factura_agildte(
            telefono='71234567',
            nombre_cliente='Ana',
            codigo_generacion='CG-99',
        )
        self.assertTrue(out['ok'])
        self.assertEqual(out['whatsapp_message_id'], 'wamid.TEST')
        self.assertIn('CG-99', out['enlace'])

        _phone_id, _token, payload = mock_post.call_args[0]
        self.assertEqual(payload['type'], 'template')
        self.assertEqual(payload['to'], '50371234567')
        self.assertEqual(payload['template']['name'], 'agildte_factura')
        params = payload['template']['components'][0]['parameters']
        self.assertEqual(params[0]['text'], 'Ana')
        self.assertIn('CG-99', params[1]['text'])

    @override_settings(
        WHATSAPP_PHONE_NUMBER_ID='123456',
        WHATSAPP_ACCESS_TOKEN='token-test',
        WHATSAPP_TEMPLATE_NAME='agildte_factura',
        WHATSAPP_TEMPLATE_LANGUAGE='en',
        WHATSAPP_TEMPLATE_BODY_PARAMS=3,
        WHATSAPP_GRAPH_API_VERSION='v18.0',
        WHATSAPP_FACTURA_DOWNLOAD_URL='https://example.com/d?nis={nis}',
    )
    @patch('api.services.whatsapp_cloud_service._post_meta_messages')
    def test_plantilla_tres_params_nombre_empresa_enlace(self, mock_post):
        mock_post.return_value = {'messages': [{'id': 'wamid.T3'}]}
        out = enviar_plantilla_factura_agildte(
            telefono='71234567',
            nombre_cliente='Juan Perez',
            codigo_generacion='CG-100',
            nombre_empresa='Termim SA',
        )
        self.assertTrue(out['ok'])
        params = mock_post.call_args[0][2]['template']['components'][0]['parameters']
        self.assertEqual(params[0]['text'], 'Juan Perez')
        self.assertEqual(params[1]['text'], 'Termim SA')
        self.assertIn('CG-100', params[2]['text'])
