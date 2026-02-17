"""
Builder para DTE-08 (Comprobante de Liquidación Electrónica).
Esquema fe-cl-v1. Cuerpo: items con ventaNoSuj, ventaExenta, ventaGravada, exportaciones, tributos, ivaItem.
"""
import uuid
from datetime import datetime, timezone, timedelta

TZ_EL_SALVADOR = timezone(timedelta(hours=-6))

from .documento_base import BaseDocumentoDTEBuilder, _val, _numero_a_letras
from api.dte_generator import CorrelativoDTE, formatear_decimal, limpiar_nulos


class DTE08Builder(BaseDocumentoDTEBuilder):
    """
    Builder para Comprobante de Liquidación (DTE-08).
    documento: Liquidacion o dict con items (tipoDte, tipoGeneracion, numeroDocumento, fechaGeneracion,
               ventaNoSuj, ventaExenta, ventaGravada, exportaciones, tributos, ivaItem, obsItem)
    """

    TIPO_DTE = '08'
    VERSION_DTE = 1

    def _construir_emisor(self):
        """Emisor = agente liquidador o nuestra empresa según contexto."""
        return self._emisor_desde_empresa()

    def _construir_receptor(self):
        """Receptor estándar NIT/NRC."""
        nit = (_val(self.documento, 'nit_receptor', None) or _val(self.empresa, 'nit', None) or _val(self.empresa, 'nrc', None) or "").replace('-', '').replace(' ', '')
        nrc = _val(self.documento, 'nrc_receptor', None) or _val(self.empresa, 'nrc', None)
        nombre = _val(self.documento, 'nombre_receptor', None) or _val(self.empresa, 'nombre', "Empresa")
        dept = str(_val(self.documento, 'departamento_receptor', None) or _val(self.empresa, 'departamento', '06')).strip().zfill(2)
        mun = str(_val(self.documento, 'municipio_receptor', None) or _val(self.empresa, 'municipio', '14')).strip().zfill(2)
        return {
            "nit": nit or "000000000",
            "nrc": nrc or "1",
            "nombre": nombre,
            "codActividad": _val(self.documento, 'cod_actividad_receptor', None) or "62010",
            "descActividad": _val(self.documento, 'desc_actividad_receptor', None) or "Servicios",
            "nombreComercial": _val(self.documento, 'nombre_comercial_receptor', None) or nombre,
            "direccion": {"departamento": dept, "municipio": mun, "complemento": (_val(self.documento, 'direccion_receptor', None) or "San Salvador")[:200]},
            "telefono": _val(self.documento, 'telefono_receptor', None) or "22222222",
            "correo": _val(self.documento, 'correo_receptor', None) or "info@empresa.com",
        }

    def _construir_cuerpo_documento(self):
        """fe-cl-v1: numItem, tipoDte, tipoGeneracion, numeroDocumento, fechaGeneracion, ventaNoSuj, ventaExenta, ventaGravada, exportaciones, tributos, ivaItem, obsItem."""
        items = _val(self.documento, 'items', None)
        if items is None:
            venta_grav = float(formatear_decimal(_val(self.documento, 'monto_operacion', 0)))
            venta_exenta = float(formatear_decimal(_val(self.documento, 'venta_exenta', 0)))
            venta_nosuj = float(formatear_decimal(_val(self.documento, 'venta_no_sujeta', 0)))
            export = float(formatear_decimal(_val(self.documento, 'exportaciones', 0)))
            iva = float(formatear_decimal(_val(self.documento, 'iva_percibido_2', 0)))
            num_doc = _val(self.documento, 'codigo_generacion', None) or str(uuid.uuid4()).upper()
            fecha = _val(self.documento, 'fecha_documento', None) or datetime.now(TZ_EL_SALVADOR).date()
            fecha_str = fecha.strftime('%Y-%m-%d') if hasattr(fecha, 'strftime') else str(fecha)[:10]
            items = [{
                "numItem": 1,
                "tipoDte": "03",
                "tipoGeneracion": 2,
                "numeroDocumento": str(num_doc),
                "fechaGeneracion": fecha_str,
                "ventaNoSuj": round(venta_nosuj, 2),
                "ventaExenta": round(venta_exenta, 2),
                "ventaGravada": round(venta_grav, 2),
                "exportaciones": round(export, 2),
                "tributos": ["20"] if iva > 0 else [],
                "ivaItem": round(iva, 2),
                "obsItem": _val(self.documento, 'observaciones', "Liquidación")[:3000] or "Liquidación",
            }]
        resultado = []
        for i, it in enumerate(items if isinstance(items, list) else [items], 1):
            m = it if isinstance(it, dict) else {}
            resultado.append({
                "numItem": m.get('numItem', i),
                "tipoDte": str(m.get('tipoDte', '03')),
                "tipoGeneracion": int(m.get('tipoGeneracion', 2)),
                "numeroDocumento": str(m.get('numeroDocumento', str(uuid.uuid4()))).strip(),
                "fechaGeneracion": (m.get('fechaGeneracion', '') or datetime.now(TZ_EL_SALVADOR).strftime('%Y-%m-%d'))[:10],
                "ventaNoSuj": round(float(m.get('ventaNoSuj', 0)), 2),
                "ventaExenta": round(float(m.get('ventaExenta', 0)), 2),
                "ventaGravada": round(float(m.get('ventaGravada', 0)), 2),
                "exportaciones": round(float(m.get('exportaciones', 0)), 2),
                "tributos": m.get('tributos') if isinstance(m.get('tributos'), list) else (["20"] if float(m.get('ivaItem', 0)) > 0 else []),
                "ivaItem": round(float(m.get('ivaItem', 0)), 2),
                "obsItem": (m.get('obsItem', '') or 'Item')[:3000],
            })
        return resultado

    def _construir_resumen(self, cuerpo):
        total_no = sum(i.get("ventaNoSuj", 0) for i in cuerpo)
        total_ex = sum(i.get("ventaExenta", 0) for i in cuerpo)
        total_grav = sum(i.get("ventaGravada", 0) for i in cuerpo)
        total_exp = sum(i.get("exportaciones", 0) for i in cuerpo)
        sub_total = total_no + total_ex + total_grav + total_exp
        iva_perci = sum(i.get("ivaItem", 0) for i in cuerpo)
        total = round(sub_total + iva_perci, 2)
        tributos = [{"codigo": "20", "descripcion": "IVA 13%", "valor": round(iva_perci, 2)}] if iva_perci > 0 else []
        return {
            "totalNoSuj": round(total_no, 2),
            "totalExenta": round(total_ex, 2),
            "totalGravada": round(total_grav, 2),
            "totalExportacion": round(total_exp, 2),
            "subTotalVentas": round(sub_total, 2),
            "tributos": tributos,
            "montoTotalOperacion": round(sub_total, 2),
            "ivaPerci": round(iva_perci, 2),
            "total": total,
            "totalLetras": _numero_a_letras(total),
            "condicionOperacion": 1,
        }

    def _construir_extension(self):
        ext = _val(self.documento, 'extension', None)
        if isinstance(ext, dict):
            return ext
        return {"nombEntrega": None, "docuEntrega": None, "nombRecibe": None, "docuRecibe": None, "observaciones": None}

    def _construir_apendice(self):
        ap = _val(self.documento, 'apendice', None)
        return ap if isinstance(ap, list) and ap else [{"campo": "INFO", "etiqueta": "Comprobante", "valor": "Liquidación"}]

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
            "resumen": self._construir_resumen(cuerpo),
            "extension": self._construir_extension(),
            "apendice": self._construir_apendice(),
        }
        cod_est, cod_pv = self._obtener_codigos_establecimiento()
        if generar_numero_control and (not numero_ctrl or len(str(numero_ctrl)) != 31):
            dte["identificacion"]["numeroControl"] = CorrelativoDTE.obtener_siguiente_correlativo(
                empresa_id=_val(self.empresa, 'id'), tipo_dte=self.TIPO_DTE, sucursal=cod_est, punto=cod_pv
            )
        emisor = dte["emisor"]
        for k in ("codEstableMH", "codEstable", "codPuntoVentaMH", "codPuntoVenta"):
            if k not in emisor:
                emisor[k] = cod_est if "Estable" in k else cod_pv
        return self._limpiar_dte(dte)
