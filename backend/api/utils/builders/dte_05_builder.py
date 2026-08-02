"""
Builder para DTE-05 (Nota de Crédito Electrónica), esquema fe-nc-v4.
Requiere documentoRelacionado y genera exclusivamente los campos admitidos por v4.
"""
import copy
import logging
from decimal import Decimal, ROUND_HALF_UP

from .dte_03_builder import DTE03Builder
from api.dte_generator import formatear_decimal
from api.dte_constants import codigo_documento_mh_por_tipo_venta
from api.utils.mh_documento import normalizar_tipo_y_numero_mh

logger = logging.getLogger(__name__)


def _val(doc, attr, default=None):
    """Obtiene valor de objeto o dict."""
    if doc is None:
        return default
    if isinstance(doc, dict):
        return doc.get(attr, default)
    return getattr(doc, attr, default)


def _money2(valor) -> float:
    """Redondeo monetario HALF_UP a 2 decimales (regla típica MH)."""
    return float(Decimal(str(valor or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def _normalizar_tipo_documento_relacionado_mh(tipo_doc) -> str:
    """
    MH exige códigos de catálogo con 2 dígitos ('01', '03', …). Evita '3' u otros formatos inválidos.
    """
    if tipo_doc is None:
        return '03'
    s = str(tipo_doc).strip()
    if not s:
        return '03'
    if s.isdigit():
        return s.zfill(2)[-2:] if len(s) > 2 else s.zfill(2)
    return s[:2] if len(s) >= 2 else s.zfill(2) if s.isdigit() else '03'


class DTE05Builder(DTE03Builder):
    """Builder para Nota de Crédito (DTE-05). Requiere documentoRelacionado.
    Esquema fe-nc-v4: estructura distinta a CCF.
    """

    TIPO_DTE = '05'
    VERSION_DTE = 4

    def _generar_identificacion(self, ambiente, fecha_str, hora_actual):
        identificacion = super()._generar_identificacion(ambiente, fecha_str, hora_actual)
        identificacion['fusion'] = None
        return identificacion

    def _construir_emisor(self):
        """Emisor para NC: sin codEstable/codPuntoVenta. nombreComercial: base usa nombre si vacío."""
        emisor = super()._construir_emisor()
        for k in ('codEstable', 'codEstableMH', 'codPuntoVenta', 'codPuntoVentaMH'):
            emisor.pop(k, None)
        return emisor

    def _construir_receptor(self):
        """Receptor v4: tipoDocumento/numDocumento en lugar de nit."""
        receptor_ccf = super()._construir_receptor()
        doc_raw = receptor_ccf.pop('nit', None)
        tipo_raw = getattr(self.venta, 'tipo_doc_receptor', None)
        tipo_doc, num_doc = normalizar_tipo_y_numero_mh(tipo_raw, doc_raw)
        if not tipo_doc or not num_doc:
            raise ValueError('NC/ND v4 requiere DUI o NIT válido del receptor.')

        return {
            'tipoDocumento': tipo_doc,
            'numDocumento': num_doc,
            'nrc': receptor_ccf.get('nrc'),
            'nombre': receptor_ccf.get('nombre'),
            'codActividad': receptor_ccf.get('codActividad'),
            'descActividad': receptor_ccf.get('descActividad'),
            'nombreComercial': receptor_ccf.get('nombreComercial'),
            'direccion': receptor_ccf.get('direccion'),
            'telefono': receptor_ccf.get('telefono'),
            'correo': receptor_ccf.get('correo'),
        }

    def _generar_items(self, tipo_dte, incluir_iva_item=False):
        """Ítems v4; numeroDocumento se completa desde documentoRelacionado."""
        items = super()._generar_items(tipo_dte='03', incluir_iva_item=False)
        for item in items:
            item.pop('psv', None)
            item['codTributo'] = item.get('codTributo')
            item['noGravado'] = _money2(item.get('noGravado', 0) or 0)
            item['ivaPerci'] = 0.00
            item['ivaRete'] = 0.00
            # MH NC/ND v4: el IVA 13% va en resumen.tributos (código 20).
            # Si totalIva (ítem/resumen) > 0 junto con tributos, rechaza 020 CALCULO INCORRECTO.
            item['totalIva'] = 0.00
        self._distribuir_retenciones_items(items)
        return items

    def _distribuir_retenciones_items(self, items):
        """Distribuye percepción/retención para que ítems y resumen concilien."""
        if not items:
            return
        perci_total = _money2(getattr(self.venta, 'iva_retenido_2', 0) or 0)
        rete_total = _money2(getattr(self.venta, 'iva_retenido_1', 0) or 0)
        bases = [max(float(i.get('ventaGravada', 0) or 0), 0) for i in items]
        total_base = sum(bases)

        for campo, total in (('ivaPerci', perci_total), ('ivaRete', rete_total)):
            restante = total
            for indice, item in enumerate(items):
                if indice == len(items) - 1:
                    valor = restante
                elif total_base > 0:
                    valor = _money2(total * bases[indice] / total_base)
                    restante = _money2(restante - valor)
                else:
                    valor = 0.00
                item[campo] = _money2(max(valor, 0))

    def _construir_resumen(self, cuerpo_documento):
        """Resumen explícito fe-nc-v4 / fe-nd-v4."""
        total_no_suj = _money2(sum(float(i.get('ventaNoSuj', 0) or 0) for i in cuerpo_documento))
        total_exenta = _money2(sum(float(i.get('ventaExenta', 0) or 0) for i in cuerpo_documento))
        total_gravada = _money2(sum(float(i.get('ventaGravada', 0) or 0) for i in cuerpo_documento))
        total_descu = _money2(sum(float(i.get('montoDescu', 0) or 0) for i in cuerpo_documento))
        total_no_gravado = _money2(sum(float(i.get('noGravado', 0) or 0) for i in cuerpo_documento))
        iva_perci = _money2(sum(float(i.get('ivaPerci', 0) or 0) for i in cuerpo_documento))
        iva_rete = _money2(sum(float(i.get('ivaRete', 0) or 0) for i in cuerpo_documento))
        sub_total_ventas = _money2(total_no_suj + total_exenta + total_gravada)

        # IVA del documento: solo en tributos código 20 (como CCF).
        # resumen.totalIva debe ser 0; MH valida:
        #   totalIva == montoTotalOperacion - subTotalVentas - sum(tributos) - totalNoGravado ± rete/perci
        iva_tributo = _money2(Decimal(str(total_gravada)) * Decimal('0.13'))
        tributos = (
            [{'codigo': '20', 'descripcion': 'Impuesto al Valor Agregado 13%', 'valor': iva_tributo}]
            if iva_tributo > 0
            else None
        )
        # Forzar 0: MH calcula totalIva como
        # montoTotal - subTotalVentas - sum(tributos) - totalNoGravado (± rete/perci).
        for item in cuerpo_documento:
            item['totalIva'] = 0.00
        total_iva = 0.00
        monto_operacion = _money2(
            sub_total_ventas
            + (iva_tributo if tributos else 0)
            + total_no_gravado
            + iva_perci
            - iva_rete
        )
        total_pagar = _money2(max(monto_operacion, 0))
        observaciones = (getattr(self.venta, 'observaciones', None) or '').strip() or None
        return {
            'totalNoSuj': total_no_suj,
            'totalExenta': total_exenta,
            'totalGravada': total_gravada,
            'subTotalVentas': sub_total_ventas,
            'totalDescu': total_descu,
            'tributos': tributos,
            'montoTotalOperacion': monto_operacion,
            'ivaPerci': iva_perci,
            'totalIva': total_iva,
            'ivaRete': iva_rete,
            'totalNoGravado': total_no_gravado,
            'totalPagar': total_pagar,
            'totalLetras': self._numero_a_letras(total_pagar),
            'condicionOperacion': int(getattr(self.venta, 'condicion_operacion', 1) or 1),
            'observaciones': observaciones,
            'codigoRetencionMH': None,
        }

    def _enriquecer_documento_relacionado_desde_referencia(self):
        """
        Tras recargar Venta desde BD (Celery / emitir-factura), los atributos solo-en-memoria se pierden.
        Si falta tipo pero existe codigo_generacion_referenciado, rellenar desde la venta origen.
        """
        venta = self.venta
        if _val(venta, 'documento_relacionado_tipo', None):
            return
        ref = _val(venta, 'codigo_generacion_referenciado', None)
        if not ref or not str(ref).strip():
            return
        from api.models import Venta as VentaModel

        orig = VentaModel.objects.filter(codigo_generacion__iexact=str(ref).strip()).first()
        if not orig:
            return
        venta.documento_relacionado_codigo = orig.codigo_generacion
        venta.documento_relacionado_numero_control = orig.numero_control
        venta.documento_relacionado_fecha_emision = orig.fecha_emision
        venta.documento_relacionado_tipo = codigo_documento_mh_por_tipo_venta(orig.tipo_venta, '03')
        venta.documento_relacionado_tipo_generacion = 2

    def _construir_documento_relacionado(self):
        """documentoRelacionado: documento(s) que se está(n) anulando/corrigiendo."""
        docs = _val(self.venta, 'documento_relacionado', None)
        if docs is None:
            self._enriquecer_documento_relacionado_desde_referencia()
            tipo_doc = _val(self.venta, 'documento_relacionado_tipo', '03')
            tipo_gen = _val(self.venta, 'documento_relacionado_tipo_generacion', None)
            if tipo_gen is None:
                tipo_gen = 2
            codigo = (
                _val(self.venta, 'documento_relacionado_codigo', None)
                or _val(self.venta, 'codigo_generacion_referenciado', None)
                or ''
            )
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
                raise ValueError(
                    "NC/ND: No se encontró la fecha de emisión del documento relacionado. "
                    "Verifica que la venta referenciada tenga 'fecha_emision' guardada correctamente "
                    "(debe corresponder a la fecha que MH registró al aceptar el DTE original)."
                )
            if not num_doc:
                raise ValueError(
                    "NC/ND: No se encontró el número de documento relacionado (codigoGeneracion o numeroControl). "
                    "Verifica que la venta referenciada esté correctamente enlazada."
                )
            tipo_mh = _normalizar_tipo_documento_relacionado_mh(tipo_doc)
            docs = [{
                "tipoDocumento": tipo_mh,
                "tipoGeneracion": int(tipo_gen),
                "numeroDocumento": str(num_doc).strip().upper(),
                "fechaEmision": fec_emi
            }]
            logger.warning(
                f"📎 NC/ND documentoRelacionado → tipoDocumento={tipo_mh} (raw={tipo_doc}) gen={tipo_gen} "
                f"numDoc={str(num_doc)[:20]}... fechaEmision={fec_emi}"
            )
        if not isinstance(docs, list):
            docs = [docs]
        if not 1 <= len(docs) <= 50:
            raise ValueError('NC/ND v4 requiere entre 1 y 50 documentos relacionados.')

        normalizados = []
        for doc in docs:
            if not isinstance(doc, dict):
                raise ValueError('Cada documento relacionado debe ser un objeto.')
            fecha = doc.get('fechaEmision')
            if hasattr(fecha, 'strftime'):
                fecha = fecha.strftime('%Y-%m-%d')
            tipo_generacion = doc.get('tipoGeneracion', 2)
            if isinstance(tipo_generacion, bool):
                raise ValueError('documentoRelacionado.tipoGeneracion debe ser entero.')
            try:
                tipo_generacion = int(tipo_generacion)
            except (TypeError, ValueError) as exc:
                raise ValueError('documentoRelacionado.tipoGeneracion debe ser entero.') from exc
            numero = str(doc.get('numeroDocumento') or '').strip().upper()
            if not 1 <= len(numero) <= 36:
                raise ValueError('documentoRelacionado.numeroDocumento debe tener 1–36 caracteres.')
            if not fecha:
                raise ValueError('documentoRelacionado.fechaEmision es requerida.')
            normalizados.append({
                'tipoDocumento': _normalizar_tipo_documento_relacionado_mh(doc.get('tipoDocumento')),
                'tipoGeneracion': tipo_generacion,
                'numeroDocumento': numero,
                'fechaEmision': str(fecha)[:10],
            })
        return normalizados

    def _campos_requeridos_mh(self):
        """Campos requeridos/nullable de fe-nc-v4."""
        return [
            "identificacion.tipoContingencia", "identificacion.motivoContin",
            "identificacion.fusion",
            "documentoRelacionado", "ventaTercero", "apendice",
            "emisor.nombreComercial",
            "receptor.nrc", "receptor.nombreComercial", "receptor.telefono", "receptor.correo",
            "cuerpoDocumento.numeroDocumento", "cuerpoDocumento.codigo",
            "cuerpoDocumento.codTributo", "cuerpoDocumento.tributos",
            "resumen.tributos", "resumen.totalLetras", "resumen.observaciones",
            "resumen.codigoRetencionMH",
        ]

    def generar_json(self, ambiente='00', generar_codigo=True, generar_numero_control=True):
        """Genera JSON fe-nc-v4 y elimina propiedades no admitidas.
        MH exige que cuerpoDocumento.numeroDocumento sea IDÉNTICO en todos los ítems
        y coincida exactamente con documentoRelacionado.numeroDocumento.
        """
        dte = super().generar_json(ambiente=ambiente, generar_codigo=generar_codigo, generar_numero_control=generar_numero_control)

        # Construir documentoRelacionado y extraer su numeroDocumento
        docs_rel = self._construir_documento_relacionado()
        dte["documentoRelacionado"] = docs_rel

        # Copiar el mismo numeroDocumento a TODOS los ítems (MH rechaza si difieren)
        if docs_rel:
            primer_doc = docs_rel[0] if isinstance(docs_rel, list) else docs_rel
            num_doc_ref = str(primer_doc.get("numeroDocumento") or "").strip().upper()
            for item in (dte.get("cuerpoDocumento") or []):
                item["numeroDocumento"] = num_doc_ref

        dte.pop("otrosDocumentos", None)
        dte["ventaTercero"] = None
        return self._limpiar_diccionario_dte(dte)
