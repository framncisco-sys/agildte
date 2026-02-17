"""
Builder para DTE-05 (Nota de Crédito Electrónica).
Esquema fe-nc-v3. Requiere documentoRelacionado (documento que se está anulando/corrigiendo).
El esquema NC difiere de CCF: NO permite otrosDocumentos, emisor.codEstable/codPuntoVenta,
extension.placaVehiculo, resumen.pagos/numPagoElectronico/etc, cuerpoDocumento.noGravado/psv/numeroDocumento.
"""
import copy
from .dte_03_builder import DTE03Builder
from api.dte_generator import formatear_decimal


def _val(doc, attr, default=None):
    """Obtiene valor de objeto o dict."""
    if doc is None:
        return default
    if isinstance(doc, dict):
        return doc.get(attr, default)
    return getattr(doc, attr, default)


class DTE05Builder(DTE03Builder):
    """Builder para Nota de Crédito (DTE-05). Requiere documentoRelacionado.
    Esquema fe-nc-v3: estructura distinta a CCF (varios campos no permitidos).
    """

    TIPO_DTE = '05'
    VERSION_DTE = 3

    def _construir_emisor(self):
        """Emisor para NC: sin codEstable/codPuntoVenta. nombreComercial: base usa nombre si vacío."""
        emisor = super()._construir_emisor()
        for k in ('codEstable', 'codEstableMH', 'codPuntoVenta', 'codPuntoVentaMH'):
            emisor.pop(k, None)
        return emisor

    def _generar_extension(self):
        """Extension para NC: sin placaVehiculo (no permitido en fe-nc-v3)."""
        ext = super()._generar_extension()
        ext.pop('placaVehiculo', None)
        return ext

    def _generar_items(self, tipo_dte, incluir_iva_item=False):
        """Items para NC: sin noGravado, psv. tipoItem=1. codTributo requerido (null si no aplica). numeroDocumento requerido."""
        items = super()._generar_items(tipo_dte='03', incluir_iva_item=False)
        for item in items:
            item.pop('noGravado', None)
            item.pop('psv', None)
            item['tipoItem'] = 1
            if 'codTributo' not in item or item.get('codTributo') is None:
                item['codTributo'] = None
            if item.get('numeroDocumento') is None:
                item['numeroDocumento'] = (self.venta.numero_control or self.venta.codigo_generacion or '')[:50]
        return items

    def _construir_resumen(self, cuerpo_documento):
        """Resumen para NC: sin pagos, numPagoElectronico, porcentajeDescuento, totalNoGravado, saldoFavor, totalPagar."""
        resumen = super()._construir_resumen(cuerpo_documento)
        for k in ('pagos', 'numPagoElectronico', 'porcentajeDescuento', 'totalNoGravado', 'saldoFavor', 'totalPagar'):
            resumen.pop(k, None)
        return resumen

    def _construir_documento_relacionado(self):
        """documentoRelacionado: documento(s) que se está(n) anulando/corrigiendo."""
        docs = _val(self.venta, 'documento_relacionado', None)
        if docs is None:
            tipo_doc = _val(self.venta, 'documento_relacionado_tipo', '03')
            tipo_gen = _val(self.venta, 'documento_relacionado_tipo_generacion', 2)
            codigo = _val(self.venta, 'documento_relacionado_codigo', None) or ''
            if not codigo and hasattr(self.venta, 'venta_relacionada') and self.venta.venta_relacionada:
                codigo = self.venta.venta_relacionada.codigo_generacion or ''
            num_ctrl = _val(self.venta, 'documento_relacionado_numero_control', None) or ''
            if not num_ctrl and hasattr(self.venta, 'venta_relacionada') and self.venta.venta_relacionada:
                num_ctrl = self.venta.venta_relacionada.numero_control or ''
            codigo_str = str(codigo).strip().upper()
            num_ctrl_str = str(num_ctrl).strip()
            # tipoGeneracion=2 (sistema) → MH exige codigo_generacion (UUID). tipoGen=1 → numero_control (31 chars)
            if tipo_gen == 2 and codigo_str and len(codigo_str) >= 32:
                num_doc = codigo_str
            elif num_ctrl_str and len(num_ctrl_str) == 31:
                num_doc = num_ctrl_str
            else:
                num_doc = codigo_str or num_ctrl_str
            fec_emi = _val(self.venta, 'documento_relacionado_fecha_emision', None)
            if fec_emi and hasattr(fec_emi, 'strftime'):
                fec_emi = fec_emi.strftime('%Y-%m-%d')
            elif hasattr(self.venta, 'venta_relacionada') and self.venta.venta_relacionada:
                vrel = self.venta.venta_relacionada
                fec_emi = vrel.fecha_emision.strftime('%Y-%m-%d') if vrel.fecha_emision else ''
            if not fec_emi:
                fec_emi = self.venta.fecha_emision.strftime('%Y-%m-%d') if self.venta.fecha_emision else '2020-01-01'
            if not num_doc:
                num_doc = (self.venta.codigo_generacion or '').upper()
            docs = [{
                "tipoDocumento": str(tipo_doc),
                "tipoGeneracion": int(tipo_gen),
                "numeroDocumento": str(num_doc).strip().upper(),
                "fechaEmision": fec_emi or "2020-01-01"
            }]
        if not isinstance(docs, list):
            docs = [docs]
        return docs

    def _campos_requeridos_mh(self):
        """Campos requeridos para fe-nc-v3."""
        return [
            "identificacion.tipoContingencia", "identificacion.motivoContin",
            "documentoRelacionado", "ventaTercero", "extension", "apendice",
            "extension.nombEntrega", "extension.docuEntrega", "extension.nombRecibe",
            "extension.docuRecibe", "extension.observaciones",
            "emisor.nombreComercial",
            "cuerpoDocumento.numeroDocumento", "cuerpoDocumento.codTributo",
        ]

    def generar_json(self, ambiente='00', generar_codigo=True, generar_numero_control=True):
        """Genera JSON fe-nc-v3 y elimina otrosDocumentos (no permitido)."""
        dte = super().generar_json(ambiente=ambiente, generar_codigo=generar_codigo, generar_numero_control=generar_numero_control)
        dte["documentoRelacionado"] = self._construir_documento_relacionado()
        dte.pop("otrosDocumentos", None)
        dte["ventaTercero"] = None
        return dte
