"""
Builder para DTE-09 (Documento Contable de Liquidación Electrónica).
Esquema fe-dcl-v1. cuerpoDocumento es un OBJETO único (no array).
"""
import uuid
from datetime import datetime, timezone, timedelta

TZ_EL_SALVADOR = timezone(timedelta(hours=-6))

from .documento_base import BaseDocumentoDTEBuilder, _val, _numero_a_letras
from api.dte_generator import CorrelativoDTE, formatear_decimal, limpiar_nulos


class DTE09Builder(BaseDocumentoDTEBuilder):
    """
    Builder para Documento Contable de Liquidación (DTE-09).
    documento: Liquidacion o dict con periodoLiquidacionFechaInicio/Fin, valorOperaciones,
               subTotal, iva, montoSujetoPercepcion, ivaPercibido, comision, porcentComision,
               ivaComision, liquidoApagar, codLiquidacion, cantidadDoc, etc.
    """

    TIPO_DTE = '09'
    VERSION_DTE = 1

    def _construir_emisor(self):
        return self._emisor_desde_empresa()

    def _construir_receptor(self):
        nit = (_val(self.documento, 'nit_receptor', None) or _val(self.empresa, 'nit', None) or _val(self.empresa, 'nrc', None) or "").replace('-', '').replace(' ', '')
        nombre = _val(self.documento, 'nombre_receptor', None) or _val(self.empresa, 'nombre', "Empresa")
        dept = str(_val(self.documento, 'departamento_receptor', None) or "06").zfill(2)
        mun = str(_val(self.documento, 'municipio_receptor', None) or "14").zfill(2)
        return {
            "nit": nit or "000000000",
            "nrc": _val(self.documento, 'nrc_receptor', None) or _val(self.empresa, 'nrc', None),
            "nombre": nombre,
            "codActividad": _val(self.documento, 'cod_actividad_receptor', None) or "62010",
            "descActividad": _val(self.documento, 'desc_actividad_receptor', None) or "Servicios",
            "nombreComercial": _val(self.documento, 'nombre_comercial_receptor', None) or nombre,
            "tipoEstablecimiento": "01",
            "direccion": {"departamento": dept, "municipio": mun, "complemento": (_val(self.documento, 'direccion_receptor', None) or "San Salvador")[:200]},
            "telefono": _val(self.documento, 'telefono_receptor', None) or "22222222",
            "correo": _val(self.documento, 'correo_receptor', None) or "info@empresa.com",
            "codigoMH": _val(self.empresa, 'cod_establecimiento', None) or "M001",
            "puntoVentaMH": _val(self.empresa, 'cod_punto_venta', None) or "P001",
        }

    def _construir_cuerpo_documento(self):
        """fe-dcl-v1: cuerpoDocumento es un único objeto con periodoLiquidacionFechaInicio/Fin, valorOperaciones, subTotal, iva, montoSujetoPercepcion, ivaPercibido, comision, porcentComision, ivaComision, liquidoApagar, totalLetras, etc."""
        fecha = _val(self.documento, 'fecha_documento', None) or datetime.now(TZ_EL_SALVADOR).date()
        fecha_str = fecha.strftime('%Y-%m-%d') if hasattr(fecha, 'strftime') else str(fecha)[:10]
        per_ini = _val(self.documento, 'periodo_fecha_inicio', None) or fecha_str
        per_fin = _val(self.documento, 'periodo_fecha_fin', None) or fecha_str
        valor_op = float(formatear_decimal(_val(self.documento, 'valor_operaciones', None) or _val(self.documento, 'monto_operacion', 0)))
        monto_sin_perc = float(formatear_decimal(_val(self.documento, 'monto_sin_percepcion', 0)))
        sub_total = float(formatear_decimal(_val(self.documento, 'sub_total', None) or valor_op))
        iva = float(formatear_decimal(_val(self.documento, 'iva', None) or _val(self.documento, 'iva_percibido_2', 0)))
        monto_sujeto_perc = float(formatear_decimal(_val(self.documento, 'monto_sujeto_percepcion', None) or valor_op))
        iva_percibido = float(formatear_decimal(_val(self.documento, 'iva_percibido', None) or _val(self.documento, 'iva_percibido_2', 0)))
        comision = float(formatear_decimal(_val(self.documento, 'comision', 0)))
        porcent_comision = _val(self.documento, 'porcent_comision', None) or "0"
        iva_comision = float(formatear_decimal(_val(self.documento, 'iva_comision', 0)))
        liquido = float(formatear_decimal(_val(self.documento, 'liquido_pagar', None) or _val(self.documento, 'liquidoApagar', 0)))
        cod_liq = _val(self.documento, 'codigo_liquidacion', None) or _val(self.documento, 'codigo_generacion', "")[:30]
        cant_doc = int(_val(self.documento, 'cantidad_documentos', 1))
        desc_sin_perc = _val(self.documento, 'descripcion_sin_percepcion', None) or ""
        obs = _val(self.documento, 'observaciones', None) or ""

        cuerpo = {
            "periodoLiquidacionFechaInicio": str(per_ini)[:10],
            "periodoLiquidacionFechaFin": str(per_fin)[:10],
            "codLiquidacion": str(cod_liq)[:30] if cod_liq else "LIQ-001",
            "cantidadDoc": cant_doc,
            "valorOperaciones": round(valor_op, 2),
            "montoSinPercepcion": round(monto_sin_perc, 2),
            "descripSinPercepcion": str(desc_sin_perc)[:100] if desc_sin_perc else "N/A",
            "subTotal": round(sub_total, 2),
            "iva": round(iva, 2),
            "montoSujetoPercepcion": round(monto_sujeto_perc, 2),
            "ivaPercibido": round(iva_percibido, 2),
            "comision": round(comision, 2),
            "porcentComision": str(porcent_comision)[:100],
            "ivaComision": round(iva_comision, 2),
            "liquidoApagar": round(liquido, 2),
            "totalLetras": _numero_a_letras(liquido),
            "observaciones": str(obs)[:200] if obs else None,
        }
        return cuerpo

    def _construir_extension(self):
        return {
            "nombEntrega": _val(self.documento, 'nomb_entrega', None) or "Sistema",
            "docuEntrega": _val(self.documento, 'docu_entrega', None) or "00000000",
            "codEmpleado": _val(self.documento, 'cod_empleado', None) or "001",
        }

    def _construir_apendice(self):
        ap = _val(self.documento, 'apendice', None)
        return ap if isinstance(ap, list) and ap else [{"campo": "INFO", "etiqueta": "Documento", "valor": "Contable Liquidación"}]

    def generar_json(self, ambiente='00', generar_codigo=True, generar_numero_control=True):
        codigo_gen = _val(self.documento, 'codigo_generacion', None)
        if generar_codigo and not codigo_gen:
            codigo_gen = str(uuid.uuid4()).upper()
        numero_ctrl = _val(self.documento, 'numero_control', None)
        fecha = _val(self.documento, 'fecha_documento', None) or datetime.now(TZ_EL_SALVADOR).date()
        fecha_str = fecha.strftime('%Y-%m-%d') if hasattr(fecha, 'strftime') else str(fecha)[:10]
        hora = datetime.now(TZ_EL_SALVADOR).strftime('%H:%M:%S')

        cuerpo = self._construir_cuerpo_documento()
        dte = {
            "identificacion": self._generar_identificacion(ambiente, codigo_gen, numero_ctrl, fecha_str, hora),
            "emisor": self._construir_emisor(),
            "receptor": self._construir_receptor(),
            "cuerpoDocumento": cuerpo,
            "extension": self._construir_extension(),
            "apendice": self._construir_apendice(),
        }
        cod_est, cod_pv = self._obtener_codigos_establecimiento()
        if generar_numero_control and (not numero_ctrl or len(str(numero_ctrl)) != 31):
            dte["identificacion"]["numeroControl"] = CorrelativoDTE.obtener_siguiente_correlativo(
                empresa_id=_val(self.empresa, 'id'), tipo_dte=self.TIPO_DTE, sucursal=cod_est, punto=cod_pv
            )
        emisor = dte["emisor"]
        for k, v in [("codigoMH", cod_est), ("codigo", cod_est), ("puntoVentaMH", cod_pv), ("puntoVentaContri", cod_pv)]:
            if k not in emisor:
                emisor[k] = v
        return self._limpiar_dte(dte)
