"""
Builder para DTE-07 (Comprobante de Retención Electrónica).
Esquema fe-cr-v1. Emisor=agente retenedor, Receptor=contribuyente retenido.
Cuerpo: detalles de retención (no items de venta).
"""
import uuid
from datetime import datetime, timezone, timedelta

TZ_EL_SALVADOR = timezone(timedelta(hours=-6))

from .documento_base import BaseDocumentoDTEBuilder, _val, _numero_a_letras
from api.dte_generator import CorrelativoDTE, formatear_decimal, limpiar_nulos


class DTE07Builder(BaseDocumentoDTEBuilder):
    """
    Builder para Comprobante de Retención (DTE-07).
    documento: RetencionRecibida o dict con nit_agente, nombre_agente, monto_sujeto, monto_retenido_1,
               codigo_generacion, fecha_documento, num_documento_origen, tipo_dte_origen, etc.
    """

    TIPO_DTE = '07'
    VERSION_DTE = 1

    def _construir_emisor(self):
        """Emisor = agente retenedor (quien retuvo)."""
        nit = (_val(self.documento, 'nit_agente', None) or "").replace('-', '').replace(' ', '')
        nombre = _val(self.documento, 'nombre_agente', None) or "Agente Retenedor"
        cod_est, cod_pv = self._obtener_codigos_establecimiento()
        emisor = {
            "nit": nit or "000000000",
            "nrc": _val(self.documento, 'nrc_agente', None) or "1",
            "nombre": nombre,
            "codActividad": _val(self.documento, 'cod_actividad_agente', None) or "62010",
            "descActividad": _val(self.documento, 'desc_actividad_agente', None) or "Servicios",
            "nombreComercial": _val(self.documento, 'nombre_comercial_agente', None) or nombre,
            "tipoEstablecimiento": "01",
            "direccion": {
                "departamento": str(_val(self.documento, 'departamento_agente', None) or "06").zfill(2),
                "municipio": str(_val(self.documento, 'municipio_agente', None) or "14").zfill(2),
                "complemento": (_val(self.documento, 'direccion_agente', None) or "San Salvador")[:200]
            },
            "telefono": _val(self.documento, 'telefono_agente', None) or "22222222",
            "codigoMH": cod_est,
            "codigo": cod_est,
            "puntoVentaMH": cod_pv,
            "puntoVenta": cod_pv,
            "correo": _val(self.documento, 'correo_agente', None) or "agente@ejemplo.com",
        }
        return emisor

    def _construir_receptor(self):
        """Receptor = contribuyente retenido (nuestra empresa)."""
        nit = (_val(self.empresa, 'nit', None) or _val(self.empresa, 'nrc', None) or "").replace('-', '').replace(' ', '')
        dept = str(_val(self.empresa, 'departamento', None) or "06").strip().zfill(2)
        mun = str(_val(self.empresa, 'municipio', None) or "14").strip().zfill(2)
        receptor = {
            "tipoDocumento": "36",
            "numDocumento": nit or "00000000000000",
            "nrc": _val(self.empresa, 'nrc', None),
            "nombre": _val(self.empresa, 'nombre', "Empresa"),
            "codActividad": _val(self.empresa, 'cod_actividad', None) or "62010",
            "descActividad": _val(self.empresa, 'desc_actividad', None) or "Servicios",
            "nombreComercial": _val(self.empresa, 'nombre_comercial', None) or _val(self.empresa, 'nombre', "Empresa"),
            "direccion": {"departamento": dept, "municipio": mun, "complemento": (_val(self.empresa, 'direccion', None) or "San Salvador")[:200]},
            "telefono": _val(self.empresa, 'telefono', None) or "22222222",
            "correo": _val(self.empresa, 'correo', None) or "info@empresa.com",
        }
        return receptor

    def _construir_cuerpo_documento(self):
        """Cuerpo: detalles de retención. fe-cr-v1: numItem, tipoDte, tipoDoc, numDocumento, fechaEmision, montoSujetoGrav, codigoRetencionMH, ivaRetenido, descripcion."""
        items = _val(self.documento, 'detalles', None)
        if items is None:
            monto_sujeto = float(formatear_decimal(_val(self.documento, 'monto_sujeto', 0)))
            monto_retenido = float(formatear_decimal(_val(self.documento, 'monto_retenido_1', 0)))
            num_doc = _val(self.documento, 'num_documento_origen', None) or _val(self.documento, 'codigo_generacion', None) or str(uuid.uuid4()).upper()
            fecha = _val(self.documento, 'fecha_documento', None) or datetime.now(TZ_EL_SALVADOR).date()
            fecha_str = fecha.strftime('%Y-%m-%d') if hasattr(fecha, 'strftime') else str(fecha)[:10]
            tipo_dte = _val(self.documento, 'tipo_dte_origen', '03')
            tipo_doc = 2 if len(str(num_doc)) == 36 and '-' in str(num_doc) else 1
            cod_retencion = _val(self.documento, 'codigo_retencion_mh', '22')
            desc = _val(self.documento, 'descripcion', None) or "Retención IVA"
            items = [{
                "numItem": 1,
                "tipoDte": str(tipo_dte),
                "tipoDoc": tipo_doc,
                "numDocumento": str(num_doc).strip(),
                "fechaEmision": fecha_str,
                "montoSujetoGrav": round(monto_sujeto, 2),
                "codigoRetencionMH": cod_retencion,
                "ivaRetenido": round(monto_retenido, 2),
                "descripcion": desc[:1000] if desc else "Retención",
            }]
        resultado = []
        for i, it in enumerate(items if isinstance(items, list) else [items], 1):
            m = it if isinstance(it, dict) else {}
            num_item = m.get('numItem', i)
            tipo_dte = m.get('tipoDte', '03')
            tipo_doc = m.get('tipoDoc', 2)
            num_doc = m.get('numDocumento', str(uuid.uuid4()).upper())
            fecha_emi = m.get('fechaEmision', datetime.now(TZ_EL_SALVADOR).strftime('%Y-%m-%d'))
            monto_suj = float(m.get('montoSujetoGrav', 0))
            cod_ret = m.get('codigoRetencionMH', '22')
            iva_ret = float(m.get('ivaRetenido', 0))
            desc = m.get('descripcion', 'Retención')
            resultado.append({
                "numItem": num_item,
                "tipoDte": str(tipo_dte),
                "tipoDoc": int(tipo_doc),
                "numDocumento": str(num_doc).strip(),
                "fechaEmision": fecha_emi[:10],
                "montoSujetoGrav": round(monto_suj, 2),
                "codigoRetencionMH": cod_ret,
                "ivaRetenido": round(iva_ret, 2),
                "descripcion": (desc or "Retención")[:1000],
            })
        return resultado

    def _construir_resumen(self, cuerpo):
        total_sujeto = sum(i.get("montoSujetoGrav", 0) for i in cuerpo)
        total_iva = sum(i.get("ivaRetenido", 0) for i in cuerpo)
        return {
            "totalSujetoRetencion": round(total_sujeto, 2),
            "totalIVAretenido": round(total_iva, 2),
            "totalIVAretenidoLetras": _numero_a_letras(total_iva),
        }

    def _construir_extension(self):
        return {
            "nombEntrega": _val(self.documento, 'nomb_entrega', None) or "Sistema",
            "docuEntrega": _val(self.documento, 'docu_entrega', None) or "00000000",
            "nombRecibe": _val(self.documento, 'nomb_recibe', None) or "Sistema",
            "docuRecibe": _val(self.documento, 'docu_recibe', None) or "00000000",
            "observaciones": _val(self.documento, 'observaciones', None),
        }

    def _construir_apendice(self):
        ap = _val(self.documento, 'apendice', None)
        return ap if isinstance(ap, list) and ap else [{"campo": "INFO", "etiqueta": "Información", "valor": "Comprobante de Retención"}]

    def generar_json(self, ambiente='00', generar_codigo=True, generar_numero_control=True):
        codigo_gen = _val(self.documento, 'codigo_generacion', None) if generar_codigo else _val(self.documento, 'codigo_generacion', None)
        if generar_codigo and not codigo_gen:
            codigo_gen = str(uuid.uuid4()).upper()
        numero_ctrl = _val(self.documento, 'numero_control', None)
        fecha = _val(self.documento, 'fecha_documento', None) or datetime.now(TZ_EL_SALVADOR).date()
        fecha_str = fecha.strftime('%Y-%m-%d') if hasattr(fecha, 'strftime') else str(fecha)[:10]
        hora = datetime.now(TZ_EL_SALVADOR).strftime('%H:%M:%S')

        cuerpo = self._construir_cuerpo_documento()
        dte = {
            "identificacion": self._generar_identificacion(
                ambiente, codigo_gen, numero_ctrl, fecha_str, hora,
                tipo_cont=None, motivo_cont=None
            ),
            "emisor": self._construir_emisor(),
            "receptor": self._construir_receptor(),
            "cuerpoDocumento": cuerpo,
            "resumen": self._construir_resumen(cuerpo),
            "extension": self._construir_extension(),
            "apendice": self._construir_apendice(),
        }
        ident = dte["identificacion"]
        if "tipoContingencia" not in ident:
            ident["tipoContingencia"] = None
        if "motivoContin" not in ident:
            ident["motivoContin"] = None
        if generar_numero_control and (not numero_ctrl or len(str(numero_ctrl)) != 31):
            ident["numeroControl"] = CorrelativoDTE.obtener_siguiente_correlativo(
                empresa_id=_val(self.empresa, 'id'),
                tipo_dte=self.TIPO_DTE,
                sucursal=self._obtener_codigos_establecimiento()[0],
                punto=self._obtener_codigos_establecimiento()[1]
            )
        return self._limpiar_dte(dte)
