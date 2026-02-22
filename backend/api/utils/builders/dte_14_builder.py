"""
Builder para DTE-14 (Factura de Sujeto Excluido Electrónica).
Esquema fe-fse-v1.

Estructura correcta según MH:
  emisor        = NUESTRA EMPRESA (quien genera el DTE ante MH, autenticado con nuestras credenciales)
  sujetoExcluido = el PROVEEDOR INFORMAL (quien vendió sin poder emitir DTE propio)
"""
import uuid
from datetime import datetime, timezone, timedelta

TZ_EL_SALVADOR = timezone(timedelta(hours=-6))

from .documento_base import BaseDocumentoDTEBuilder, _val, _numero_a_letras
from api.dte_generator import CorrelativoDTE, formatear_decimal, limpiar_nulos


class DTE14Builder(BaseDocumentoDTEBuilder):
    """
    Builder para Factura de Sujeto Excluido (DTE-14).
    - emisor        = empresa (nuestra compañía registrada en MH)
    - sujetoExcluido = proveedor informal (vendedor sin DTE propio)
    """

    TIPO_DTE = '14'
    VERSION_DTE = 1

    def _construir_emisor(self):
        """Emisor = nuestra empresa (autenticada ante MH). NIT del emisor debe coincidir con credenciales."""
        nit = (_val(self.empresa, 'nit', None) or _val(self.empresa, 'nrc', None) or "").replace('-', '').replace(' ', '')
        nrc = _val(self.empresa, 'nrc', None)
        cod_actividad = _val(self.empresa, 'cod_actividad', None) or "62010"
        desc_actividad = _val(self.empresa, 'desc_actividad', None) or "Servicios"
        dept = str(_val(self.empresa, 'departamento', None) or "06").strip().zfill(2)
        mun = str(_val(self.empresa, 'municipio', None) or "14").strip().zfill(2)
        cod_est, cod_pv = self._obtener_codigos_establecimiento()
        return {
            "nit": nit,
            "nrc": nrc,
            "nombre": _val(self.empresa, 'nombre', "Empresa"),
            "codActividad": cod_actividad,
            "descActividad": desc_actividad,
            "direccion": {
                "departamento": dept,
                "municipio": mun,
                "complemento": (_val(self.empresa, 'direccion', None) or "San Salvador")[:200]
            },
            "telefono": _val(self.empresa, 'telefono', None) or "22222222",
            "codEstableMH": cod_est,
            "codEstable": cod_est,
            "codPuntoVentaMH": cod_pv,
            "codPuntoVenta": cod_pv,
            "correo": _val(self.empresa, 'correo', None) or "info@empresa.com",
        }

    def _construir_sujeto_excluido(self):
        """sujetoExcluido = proveedor informal (quien vendió sin DTE). Datos vienen del formulario.

        Reglas de formato MH (fe-fse-v1):
          tipoDocumento "13" (DUI)  → numDocumento debe ser exactamente 9 dígitos
          tipoDocumento "36" (NIT)  → numDocumento debe ser 14 o 9 dígitos
          Determinar tipo según longitud del número limpio.
        """
        doc_raw = (_val(self.documento, 'nit_proveedor', None) or "")
        # Limpiar: solo dígitos
        doc_limpio = ''.join(c for c in str(doc_raw) if c.isdigit())

        if len(doc_limpio) == 14:
            tipo_doc = "36"   # NIT de 14 dígitos
            num_doc = doc_limpio
        elif len(doc_limpio) == 9:
            tipo_doc = "13"   # DUI de 9 dígitos
            num_doc = doc_limpio
        elif len(doc_limpio) == 10:
            # DUI con dígito verificador adicional — usar los primeros 9
            tipo_doc = "13"
            num_doc = doc_limpio[:9]
        else:
            raise ValueError(
                f"Número de documento del sujeto excluido inválido: '{doc_raw}'. "
                f"Debe ser DUI (9 dígitos) o NIT (14 dígitos). "
                f"Dígitos encontrados: {len(doc_limpio)}."
            )

        nombre_prov = _val(self.documento, 'nombre_proveedor', None) or "Proveedor Sujeto Excluido"
        dept = str(_val(self.documento, 'departamento_proveedor', None) or "06").zfill(2)
        mun = str(_val(self.documento, 'municipio_proveedor', None) or "14").zfill(2)
        return {
            "tipoDocumento": tipo_doc,
            "numDocumento": num_doc,
            "nombre": nombre_prov,
            "codActividad": None,
            "descActividad": None,
            "direccion": {
                "departamento": dept,
                "municipio": mun,
                "complemento": (_val(self.documento, 'direccion_proveedor', None) or "San Salvador")[:200]
            },
            "telefono": None,
            "correo": None,
        }

    def _construir_cuerpo_documento(self):
        """fe-fse-v1: numItem, tipoItem, cantidad, codigo, uniMedida, descripcion, precioUni, montoDescu, compra."""
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
        total_compra = sum(i.get("compra", 0) for i in cuerpo)
        total_descu = sum(i.get("montoDescu", 0) for i in cuerpo)
        sub_total = round(total_compra - total_descu, 2)
        iva_rete = float(formatear_decimal(_val(self.documento, 'iva_retenido', 0)))
        rete_renta = float(formatear_decimal(_val(self.documento, 'rete_renta', 0)))
        total_pagar = round(sub_total - iva_rete - rete_renta, 2)
        pagos = _val(self.documento, 'pagos', None)
        if not pagos:
            pagos = [{"codigo": "01", "montoPago": total_pagar, "referencia": None, "plazo": None, "periodo": None}]
        return {
            "totalCompra": round(total_compra, 2),
            "descu": round(total_descu, 2),
            "totalDescu": round(total_descu, 2),
            "subTotal": sub_total,
            "ivaRete1": round(iva_rete, 2),
            "reteRenta": round(rete_renta, 2),
            "totalPagar": total_pagar,
            "totalLetras": _numero_a_letras(total_pagar),
            "condicionOperacion": int(_val(self.documento, 'condicion_operacion', 1)),
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
        fecha_str = ahora_sv.strftime('%Y-%m-%d')
        hora = ahora_sv.strftime('%H:%M:%S')

        cuerpo = self._construir_cuerpo_documento()
        emisor = self._construir_emisor()
        # Asegurar nrc presente (schema lo requiere aunque sea null)
        if 'nrc' not in emisor:
            emisor['nrc'] = None

        dte = {
            "identificacion": self._generar_identificacion(ambiente, codigo_gen, numero_ctrl, fecha_str, hora),
            "emisor": emisor,
            "sujetoExcluido": self._construir_sujeto_excluido(),
            "cuerpoDocumento": cuerpo,
            "resumen": self._construir_resumen(cuerpo),
            "apendice": self._construir_apendice(),
        }
        ident = dte["identificacion"]
        # tipoContingencia y motivoContin son requeridos por schema (pueden ser null)
        ident["tipoContingencia"] = None
        ident["motivoContin"] = None

        cod_est, cod_pv = self._obtener_codigos_establecimiento()
        if generar_numero_control and (not numero_ctrl or len(str(numero_ctrl)) != 31):
            ident["numeroControl"] = CorrelativoDTE.obtener_siguiente_correlativo(
                empresa_id=_val(self.empresa, 'id'), tipo_dte=self.TIPO_DTE, sucursal=cod_est, punto=cod_pv
            )

        # Campos requeridos por fe-fse-v1 que pueden ser null — limpiar_nulos no debe eliminarlos
        campos_requeridos = [
            "identificacion.tipoContingencia",
            "identificacion.motivoContin",
            "emisor.nrc",
            "sujetoExcluido.codActividad",
            "sujetoExcluido.descActividad",
            "sujetoExcluido.telefono",
            "sujetoExcluido.correo",
            "resumen.totalDescu",
            "resumen.observaciones",
            "resumen.pagos.referencia",
            "resumen.pagos.plazo",
            "resumen.pagos.periodo",
        ]
        return self._limpiar_dte(dte, campos_requeridos=campos_requeridos)
