"""
Builder para DTE-15 (Comprobante de Donación Electrónica).
Esquema fe-cd-v1. Usa donante y donatario (no emisor/receptor). Requiere otrosDocumentos.
"""
import uuid
from datetime import datetime, timezone, timedelta

TZ_EL_SALVADOR = timezone(timedelta(hours=-6))

from .documento_base import BaseDocumentoDTEBuilder, _val, _numero_a_letras
from api.dte_generator import CorrelativoDTE, formatear_decimal, limpiar_nulos


class DTE15Builder(BaseDocumentoDTEBuilder):
    """
    Builder para Comprobante de Donación (DTE-15).
    documento: dict con donante, donatario, otrosDocumentos, items (tipoDonacion, depreciacion, valor, valorUni).
    """

    TIPO_DTE = '15'
    VERSION_DTE = 1

    def _construir_donatario(self):
        """Donatario = quien recibe (emisor equivalente en fe-cd)."""
        donat = _val(self.documento, 'donatario', None)
        if isinstance(donat, dict):
            return donat
        nit = (_val(donat, 'nit', None) or _val(donat, 'numDocumento', None) or _val(self.empresa, 'nit', None) or "").replace('-', '').replace(' ', '')
        dept = str(_val(donat, 'departamento', None) or "06").zfill(2)
        mun = str(_val(donat, 'municipio', None) or "14").zfill(2)
        cod_est, cod_pv = self._obtener_codigos_establecimiento()
        return {
            "tipoDocumento": "36",
            "numDocumento": nit or "00000000000000",
            "nrc": _val(donat, 'nrc', None) or _val(self.empresa, 'nrc', None),
            "nombre": _val(donat, 'nombre', None) or _val(self.empresa, 'nombre', "Donatario"),
            "codActividad": _val(donat, 'cod_actividad', None) or "62010",
            "descActividad": _val(donat, 'desc_actividad', None) or "Servicios",
            "nombreComercial": _val(donat, 'nombre_comercial', None),
            "tipoEstablecimiento": "01",
            "direccion": {"departamento": dept, "municipio": mun, "complemento": (_val(donat, 'direccion', None) or "San Salvador")[:200]},
            "telefono": _val(donat, 'telefono', None) or "22222222",
            "correo": _val(donat, 'correo', None) or "donatario@ejemplo.com",
            "codEstableMH": cod_est,
            "codEstable": cod_est,
            "codPuntoVentaMH": cod_pv,
            "codPuntoVenta": cod_pv,
        }

    def _construir_donante(self):
        """Donante = quien dona (receptor equivalente en fe-cd)."""
        don = _val(self.documento, 'donante', None)
        if isinstance(don, dict):
            return don
        nit = (_val(don, 'nit', None) or _val(don, 'numDocumento', None) or "").replace('-', '').replace(' ', '')
        dept = str(_val(don, 'departamento', None) or "06").zfill(2)
        mun = str(_val(don, 'municipio', None) or "14").zfill(2)
        return {
            "tipoDocumento": "36",
            "numDocumento": nit or "000000000",
            "nrc": _val(don, 'nrc', None),
            "nombre": _val(don, 'nombre', None) or "Donante",
            "codActividad": _val(don, 'cod_actividad', None) or "62010",
            "descActividad": _val(don, 'desc_actividad', None) or "Servicios",
            "direccion": {"departamento": dept, "municipio": mun, "complemento": (_val(don, 'direccion', None) or "San Salvador")[:200]},
            "telefono": _val(don, 'telefono', None) or "22222222",
            "correo": _val(don, 'correo', None) or "donante@ejemplo.com",
            "codDomiciliado": int(_val(don, 'cod_domiciliado', 1)),
            "codPais": _val(don, 'cod_pais', "9905"),
        }

    def _construir_otros_documentos(self):
        """otrosDocumentos: array requerido. codDocAsociado 1=Otro, 2=Resolución."""
        docs = _val(self.documento, 'otrosDocumentos', None)
        if isinstance(docs, list) and docs:
            return docs
        return [{
            "codDocAsociado": 1,
            "descDocumento": "Documento de donación",
            "detalleDocumento": "Comprobante de donación electrónica",
        }]

    def _construir_cuerpo_documento(self):
        """fe-cd-v1: numItem, tipoDonacion (1/2/3), cantidad, codigo, uniMedida, descripcion, depreciacion, valorUni, valor."""
        items = _val(self.documento, 'items', None) or _val(self.documento, 'cuerpoDocumento', None)
        if items is None:
            valor = float(formatear_decimal(_val(self.documento, 'valor_total', 0)))
            items = [{
                "numItem": 1, "tipoDonacion": 1, "cantidad": 1.0, "codigo": "DON-001",
                "uniMedida": 99, "descripcion": "Donación", "depreciacion": 0.00,
                "valorUni": round(valor, 2), "valor": round(valor, 2),
            }]
        resultado = []
        for i, it in enumerate(items if isinstance(items, list) else [items], 1):
            m = it if isinstance(it, dict) else {}
            tipo_don = int(m.get('tipoDonacion', 1))
            deprec = float(m.get('depreciacion', 0))
            valor = float(m.get('valor', 0) or m.get('valorUni', 0) * float(m.get('cantidad', 1)))
            valor_uni = float(m.get('valorUni', 0) or (valor / float(m.get('cantidad', 1)) if m.get('cantidad') else valor))
            resultado.append({
                "numItem": m.get('numItem', i),
                "tipoDonacion": tipo_don,
                "cantidad": round(float(m.get('cantidad', 1)), 2),
                "codigo": str(m.get('codigo', '') or 'DON')[:25],
                "uniMedida": 99 if tipo_don in (1, 3) else int(m.get('uniMedida', 59)),
                "descripcion": (m.get('descripcion', '') or 'Donación')[:1000],
                "depreciacion": round(deprec, 2),
                "valorUni": round(valor_uni, 2),
                "valor": round(valor, 2),
            })
        return resultado

    def _construir_resumen(self, cuerpo):
        valor_total = sum(i.get("valor", 0) for i in cuerpo)
        pagos = _val(self.documento, 'pagos', None)
        if not pagos:
            pagos = [{"codigo": "01", "montoPago": round(valor_total, 2), "referencia": None}]
        return {
            "valorTotal": round(valor_total, 2),
            "totalLetras": _numero_a_letras(valor_total),
            "pagos": pagos,
        }

    def _construir_apendice(self):
        ap = _val(self.documento, 'apendice', None)
        return ap if isinstance(ap, list) and ap else [{"campo": "INFO", "etiqueta": "Donación", "valor": "Comprobante Electrónico"}]

    def generar_json(self, ambiente='00', generar_codigo=True, generar_numero_control=True):
        codigo_gen = _val(self.documento, 'codigo_generacion', None)
        if generar_codigo and not codigo_gen:
            codigo_gen = str(uuid.uuid4()).upper()
        numero_ctrl = _val(self.documento, 'numero_control', None)
        fecha = _val(self.documento, 'fecha_emision', None) or _val(self.documento, 'fecha_documento', None) or datetime.now(TZ_EL_SALVADOR).date()
        fecha_str = fecha.strftime('%Y-%m-%d') if hasattr(fecha, 'strftime') else str(fecha)[:10]
        hora = datetime.now(TZ_EL_SALVADOR).strftime('%H:%M:%S')

        cuerpo = self._construir_cuerpo_documento()
        dte = {
            "identificacion": self._generar_identificacion(ambiente, codigo_gen, numero_ctrl, fecha_str, hora),
            "donante": self._construir_donante(),
            "donatario": self._construir_donatario(),
            "otrosDocumentos": self._construir_otros_documentos(),
            "cuerpoDocumento": cuerpo,
            "resumen": self._construir_resumen(cuerpo),
            "apendice": self._construir_apendice(),
        }
        cod_est, cod_pv = self._obtener_codigos_establecimiento()
        if generar_numero_control and (not numero_ctrl or len(str(numero_ctrl)) != 31):
            dte["identificacion"]["numeroControl"] = CorrelativoDTE.obtener_siguiente_correlativo(
                empresa_id=_val(self.empresa, 'id'), tipo_dte=self.TIPO_DTE, sucursal=cod_est, punto=cod_pv
            )
        return self._limpiar_dte(dte)
