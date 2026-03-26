"""
Builder para DTE-06 (Nota de Débito Electrónica).
Esquema fe-nd-v3. Requiere documentoRelacionado.

Reglas MH para fe-nd-v3 (resumen):
  REQUERIDO:  numPagoElectronico
  PROHIBIDOS: pagos, porcentajeDescuento, totalNoGravado, saldoFavor, totalPagar

Reglas MH para fe-nd-v3 (cuerpoDocumento):
  PROHIBIDOS: noGravado, psv

Según esquema oficial MH fe-nd-v3 (documentoRelacionado.items.tipoDocumento):
  type: string, enum: ["03", "07"] únicamente.
  - "03" = Comprobante de Crédito Fiscal (y equivalentes admitidos por MH)
  - "07" = Comprobante de Retención
  No usar "3", 3, "01", etc.
"""
import logging

from .dte_05_builder import DTE05Builder
from .dte_03_builder import DTE03Builder

logger = logging.getLogger(__name__)

# Valores exactos del JSON Schema fe-nd-v3.json (MH)
_FE_ND_TIPO_DOC_REL_ENUM = frozenset({"03", "07"})


def _tipo_documento_relacionado_fe_nd_v3(valor) -> str:
    """
    Normaliza a un valor permitido por fe-nd-v3: solo '03' o '07' (strings de 2 caracteres).
    """
    if isinstance(valor, bool):
        raise ValueError("tipoDocumento inválido en documentoRelacionado (fe-nd-v3).")
    if valor is None:
        return "03"
    if isinstance(valor, (int, float)):
        n = int(valor)
        z = f"{n:02d}"
        if z in _FE_ND_TIPO_DOC_REL_ENUM:
            return z
        raise ValueError(
            "Nota de Débito (fe-nd-v3): documentoRelacionado.tipoDocumento solo permite "
            f"'03' o '07' según MH. Valor numérico recibido: {valor!r}."
        )
    raw = str(valor).strip()
    if not raw:
        return "03"
    if raw in _FE_ND_TIPO_DOC_REL_ENUM:
        return raw
    if raw.isdigit():
        z = raw.zfill(2)
        if z in _FE_ND_TIPO_DOC_REL_ENUM:
            return z
    raise ValueError(
        "Nota de Débito (fe-nd-v3): documentoRelacionado.tipoDocumento solo permite "
        f"'03' o '07' según MH (fe-nd-v3.json). Valor recibido: {valor!r}. "
        "Use un CCF (DTE-03) o comprobante de retención (07) como documento relacionado."
    )


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

    def generar_json(self, ambiente='00', generar_codigo=True, generar_numero_control=True):
        """
        Ajusta documentoRelacionado.tipoDocumento al enum exacto fe-nd-v3: "03" | "07" (strings).
        """
        dte = super().generar_json(
            ambiente=ambiente,
            generar_codigo=generar_codigo,
            generar_numero_control=generar_numero_control,
        )
        rels = dte.get("documentoRelacionado") or []
        for rel in rels:
            if not isinstance(rel, dict):
                continue
            td = rel.get("tipoDocumento")
            rel["tipoDocumento"] = _tipo_documento_relacionado_fe_nd_v3(td)
        if rels:
            logger.info("DTE-06 documentoRelacionado (fe-nd-v3): %s", rels)
        return dte
