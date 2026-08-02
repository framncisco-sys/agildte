"""
Builder para DTE-06 (Nota de Débito Electrónica), esquema fe-nd-v4.
Hereda la estructura v4 de NC y agrega numPagoElectronico.
"""
from .dte_05_builder import DTE05Builder


class DTE06Builder(DTE05Builder):
    """Builder para Nota de Débito (DTE-06). Requiere documentoRelacionado.
    Esquema fe-nd-v4: numPagoElectronico requerido y nullable.
    """

    TIPO_DTE = '06'
    VERSION_DTE = 4

    def _campos_requeridos_mh(self):
        """Campos requeridos para fe-nd-v4."""
        campos = super()._campos_requeridos_mh()
        # MH exige numPagoElectronico en resumen de ND aunque su valor sea null
        if "resumen.numPagoElectronico" not in campos:
            campos = list(campos) + ["resumen.numPagoElectronico"]
        return campos

    def _construir_resumen(self, cuerpo_documento):
        """Resumen ND v4 = resumen NC v4 + numPagoElectronico."""
        resumen = super()._construir_resumen(cuerpo_documento)
        resumen["numPagoElectronico"] = (
            getattr(self.venta, 'num_pago_electronico', None) or None
        )
        return resumen

    def _generar_items(self, tipo_dte, incluir_iva_item=False):
        """Ítems ND v4, idénticos estructuralmente a NC v4."""
        return super()._generar_items(tipo_dte=tipo_dte, incluir_iva_item=incluir_iva_item)
