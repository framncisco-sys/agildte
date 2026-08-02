"""
Builder para DTE-14 (Factura de Sujeto Excluido Electrónica).
Esquema fe-fse-v2.

Estructura correcta según MH V2:
  emisor   = NUESTRA EMPRESA
  receptor = el PROVEEDOR INFORMAL (antes sujetoExcluido en v1)
"""
import uuid
from datetime import datetime, timezone, timedelta

TZ_EL_SALVADOR = timezone(timedelta(hours=-6))

from .documento_base import BaseDocumentoDTEBuilder, _val, _numero_a_letras
from api.dte_generator import CorrelativoDTE, formatear_decimal, limpiar_nulos
from api.utils.mh_direccion import armar_direccion_mh


class DTE14Builder(BaseDocumentoDTEBuilder):
    """
    Builder para Factura de Sujeto Excluido (DTE-14) — fe-fse-v2.
    - emisor   = empresa
    - receptor = proveedor informal
    """

    TIPO_DTE = '14'
    VERSION_DTE = 2

    def _construir_emisor(self):
        """Emisor = nuestra empresa (autenticada ante MH)."""
        from api.utils.mh_documento import normalizar_nrc_mh, normalizar_telefono_mh

        nit = (_val(self.empresa, 'nit', None) or _val(self.empresa, 'nrc', None) or "").replace('-', '').replace(' ', '')
        nrc = normalizar_nrc_mh(_val(self.empresa, 'nrc', None))
        cod_actividad = _val(self.empresa, 'cod_actividad', None) or "62010"
        desc_actividad = _val(self.empresa, 'desc_actividad', None) or "Servicios"
        cod_est, cod_pv = self._obtener_codigos_establecimiento()
        correo = (_val(self.empresa, 'correo', None) or "info@empresa.com")[:100]
        return {
            "nit": nit,
            "nrc": nrc,
            "nombre": _val(self.empresa, 'nombre', "Empresa"),
            "codActividad": cod_actividad,
            "descActividad": desc_actividad,
            "direccion": armar_direccion_mh(
                _val(self.empresa, 'departamento', None),
                _val(self.empresa, 'municipio', None),
                _val(self.empresa, 'direccion', None) or "San Salvador",
                distrito=_val(self.empresa, 'distrito', None),
            ),
            "telefono": normalizar_telefono_mh(_val(self.empresa, 'telefono', None) or "22222222"),
            "codEstable": cod_est,
            "codPuntoVenta": cod_pv,
            "correo": correo,
        }

    def _construir_receptor(self):
        """receptor = proveedor informal (fe-fse-v2 renombró sujetoExcluido → receptor)."""
        doc_raw = (_val(self.documento, 'nit_proveedor', None) or "")
        doc_limpio = ''.join(c for c in str(doc_raw) if c.isdigit())

        if len(doc_limpio) == 14:
            tipo_doc = "36"
            num_doc = doc_limpio
        elif len(doc_limpio) == 9:
            tipo_doc = "13"
            num_doc = doc_limpio
        elif len(doc_limpio) == 10:
            tipo_doc = "13"
            num_doc = doc_limpio[:9]
        else:
            raise ValueError(
                f"Número de documento del sujeto excluido inválido: '{doc_raw}'. "
                f"Debe ser DUI (9 dígitos) o NIT (14 dígitos). "
                f"Dígitos encontrados: {len(doc_limpio)}."
            )

        from api.utils.mh_documento import normalizar_telefono_mh

        nombre_prov = _val(self.documento, 'nombre_proveedor', None) or "Proveedor Sujeto Excluido"
        correo_raw = (_val(self.documento, 'correo_proveedor', None) or '').strip()
        correo = correo_raw[:100] if correo_raw and '@' in correo_raw else None
        tel = normalizar_telefono_mh(_val(self.documento, 'telefono_proveedor', None))
        return {
            "tipoDocumento": tipo_doc,
            "numDocumento": num_doc,
            "nombre": nombre_prov,
            "codActividad": None,
            "descActividad": None,
            "direccion": armar_direccion_mh(
                _val(self.documento, 'departamento_proveedor', None),
                _val(self.documento, 'municipio_proveedor', None),
                _val(self.documento, 'direccion_proveedor', None) or "San Salvador",
                distrito=_val(self.documento, 'distrito_proveedor', None),
            ),
            "telefono": tel,
            "correo": correo,
        }

    def _construir_cuerpo_documento(self):
        """fe-fse-v2: numItem, tipoItem, cantidad, codigo, uniMedida, descripcion, precioUni, montoDescu, compra."""
        items = _val(self.documento, 'items', None) or _val(self.documento, 'detalles', None)
        if items is None:
            monto_total = float(formatear_decimal(_val(self.documento, 'monto_total', None) or _val(self.documento, 'monto_gravado', 0)))
            items = [{
                "numItem": 1, "tipoItem": 1, "cantidad": 1.0, "codigo": "COMP-001",
                "uniMedida": 59, "descripcion": "Compra a sujeto excluido",
                "precioUni": round(monto_total, 2), "montoDescu": 0.00, "compra": round(monto_total, 2),
            }]
        resultado = []
        for i, it in enumerate(items if isinstance(items, list) else [items], 1):
            m = it if isinstance(it, dict) else {}
            precio = float(m.get('precioUni', 0) or m.get('precio_unitario', 0))
            cant = float(m.get('cantidad', 1))
            desc = float(m.get('montoDescu', 0) or m.get('monto_descuento', 0))
            compra = float(m.get('compra', 0) or (precio * cant - desc))
            resultado.append({
                "numItem": m.get('numItem', i),
                "tipoItem": int(m.get('tipoItem', 1)),
                "cantidad": round(cant, 2),
                "codigo": str(m.get('codigo', '') or m.get('codigo_libre', '') or 'ITEM')[:25],
                "uniMedida": int(m.get('uniMedida', 59)),
                "descripcion": (m.get('descripcion', '') or m.get('descripcion_libre', '') or 'Item')[:1000],
                "precioUni": round(precio, 2),
                "montoDescu": round(desc, 2),
                "compra": round(compra, 2),
            })
        return resultado

    def _construir_resumen(self, cuerpo):
        """fe-fse-v2: compra ya viene neta de montoDescu; descu = descuento global."""
        total_compra = round(sum(float(i.get("compra", 0) or 0) for i in cuerpo), 2)
        total_descu_lineas = round(sum(float(i.get("montoDescu", 0) or 0) for i in cuerpo), 2)
        descu_global = float(formatear_decimal(_val(self.documento, 'descu', 0) or 0))
        sub_total = round(max(total_compra - descu_global, 0), 2)
        rete_renta = float(formatear_decimal(_val(self.documento, 'rete_renta', 0)))
        iva_rete_legacy = float(formatear_decimal(_val(self.documento, 'iva_retenido', 0)))
        rete_total = round(rete_renta + iva_rete_legacy, 2)
        total_pagar = round(max(sub_total - rete_total, 0), 2)
        pagos = _val(self.documento, 'pagos', None)
        if not pagos:
            pagos = [{"codigo": "01", "montoPago": total_pagar, "referencia": None, "plazo": None, "periodo": None}]
        return {
            "totalCompra": total_compra,
            "descu": round(descu_global, 2),
            "totalDescu": round(total_descu_lineas + descu_global, 2),
            "subTotal": sub_total,
            "reteRenta": rete_total,
            "totalPagar": total_pagar,
            "totalLetras": _numero_a_letras(total_pagar),
            "condicionOperacion": int(_val(self.documento, 'condicion_operacion', 1) or 1),
            "pagos": pagos,
            "observaciones": _val(self.documento, 'observaciones', None),
        }

    def _construir_apendice(self):
        ap = _val(self.documento, 'apendice', None)
        return ap if isinstance(ap, list) and ap else [{"campo": "INFO", "etiqueta": "Compra", "valor": "Sujeto Excluido"}]

    def generar_json(self, ambiente='00', generar_codigo=True, generar_numero_control=True):
        codigo_gen = _val(self.documento, 'codigo_generacion', None)
        if generar_codigo and not codigo_gen:
            codigo_gen = str(uuid.uuid4()).upper()
        numero_ctrl = _val(self.documento, 'numero_control', None)
        ahora_sv = datetime.now(TZ_EL_SALVADOR)
        fecha_emision = _val(self.documento, 'fecha_emision', None)
        if hasattr(fecha_emision, 'strftime'):
            fecha_str = fecha_emision.strftime('%Y-%m-%d')
        elif isinstance(fecha_emision, str) and len(fecha_emision) >= 10:
            fecha_str = fecha_emision[:10]
        else:
            fecha_str = ahora_sv.strftime('%Y-%m-%d')
        hora_emision = (_val(self.documento, 'hora_emision', None) or '').strip()
        if len(hora_emision) >= 8 and hora_emision[2] == ':' and hora_emision[5] == ':':
            hora = hora_emision[:8]
        else:
            hora = ahora_sv.strftime('%H:%M:%S')

        cuerpo = self._construir_cuerpo_documento()
        emisor = self._construir_emisor()
        if 'nrc' not in emisor:
            emisor['nrc'] = None

        dte = {
            "identificacion": self._generar_identificacion(ambiente, codigo_gen, numero_ctrl, fecha_str, hora),
            "emisor": emisor,
            "receptor": self._construir_receptor(),
            "cuerpoDocumento": cuerpo,
            "resumen": self._construir_resumen(cuerpo),
            "apendice": self._construir_apendice(),
        }
        ident = dte["identificacion"]
        ident["tipoContingencia"] = None
        ident["motivoContin"] = None

        cod_est, cod_pv = self._obtener_codigos_establecimiento()
        if generar_numero_control and (not numero_ctrl or len(str(numero_ctrl)) != 31):
            ident["numeroControl"] = CorrelativoDTE.obtener_siguiente_correlativo(
                empresa_id=_val(self.empresa, 'id'), tipo_dte=self.TIPO_DTE, sucursal=cod_est, punto=cod_pv
            )

        campos_requeridos = [
            "identificacion.tipoContingencia",
            "identificacion.motivoContin",
            "emisor.nrc",
            "receptor.codActividad",
            "receptor.descActividad",
            "receptor.telefono",
            "receptor.correo",
            "resumen.totalDescu",
            "resumen.observaciones",
            "resumen.pagos.referencia",
            "resumen.pagos.plazo",
            "resumen.pagos.periodo",
        ]
        return self._limpiar_dte(dte, campos_requeridos=campos_requeridos)
