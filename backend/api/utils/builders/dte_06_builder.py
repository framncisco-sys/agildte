"""
Builder para DTE-06 (Nota de Débito Electrónica).
Esquema fe-nd-v3. Requiere documentoRelacionado.

Reglas MH para fe-nd-v3 (resumen):
  REQUERIDO:  numPagoElectronico
  PROHIBIDOS: pagos, porcentajeDescuento, totalNoGravado, saldoFavor, totalPagar

Reglas MH para fe-nd-v3 (cuerpoDocumento):
  PROHIBIDOS: noGravado, psv
"""
from .dte_05_builder import DTE05Builder
from .dte_03_builder import DTE03Builder


class DTE06Builder(DTE05Builder):
    """Builder para Nota de Débito (DTE-06). Requiere documentoRelacionado.
    Esquema fe-nd-v3: numPagoElectronico requerido; pagos, porcentajeDescuento,
    totalNoGravado, saldoFavor, totalPagar, noGravado y psv están prohibidos.
    """

    TIPO_DTE = '06'
    VERSION_DTE = 3

    def _campos_requeridos_mh(self):
        """Campos requeridos para fe-nd-v3. Igual que NC pero agregando resumen.numPagoElectronico."""
        campos = super()._campos_requeridos_mh()
        # MH exige numPagoElectronico en resumen de ND aunque su valor sea null
        if "resumen.numPagoElectronico" not in campos:
            campos = list(campos) + ["resumen.numPagoElectronico"]
        return campos

    def _construir_resumen(self, cuerpo_documento):
        """Resumen para ND según fe-nd-v3:
        - Parte del resumen de NC (que ya elimina pagos, porcentajeDescuento, etc.)
        - Agrega numPagoElectronico=None (requerido por MH, preservado por _campos_requeridos_mh)
        """
        resumen = super()._construir_resumen(cuerpo_documento)
        resumen["numPagoElectronico"] = None
        for k in ("pagos", "porcentajeDescuento", "totalNoGravado", "saldoFavor", "totalPagar"):
            resumen.pop(k, None)
        return resumen

    def _generar_items(self, tipo_dte, incluir_iva_item=False):
        """Items para ND: igual que NC (sin noGravado ni psv, con numeroDocumento del docRelacionado)."""
        items = super()._generar_items(tipo_dte=tipo_dte, incluir_iva_item=incluir_iva_item)
        for item in items:
            item.pop("noGravado", None)
            item.pop("psv", None)
        return items
