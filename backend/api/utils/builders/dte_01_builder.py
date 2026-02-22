"""
Builder para DTE-01 (Factura Consumidor Final).
Esquema fe-fc-v1 - Sin NRC, sin nombreComercial en receptor cuando Consumidor Final.
Cuerpo: precioUni incluye IVA, ivaItem para desglose.
"""
from .dte_03_builder import DTE03Builder


class DTE01Builder(DTE03Builder):
    """Builder para Factura Consumidor Final (DTE-01) - Esquema fe-fc-v1."""

    TIPO_DTE = '01'
    VERSION_DTE = 1

    def _construir_emisor(self):
        """
        Emisor fe-fc-v1 con envelope version 1: codEstable y codPuntoVenta requeridos (como null).
        """
        return super()._construir_emisor()

    def _construir_receptor(self):
        """
        Receptor DTE-01: Consumidor Final.
        - Si cliente es NULL -> "Consumidor Final" (sin NRC, sin Actividad, sin nombreComercial).
        - No enviar campos nulos que Hacienda rechaza (nombreComercial, nrc si no existen).
        """
        cliente = self.venta.cliente

        codigo_departamento = str(getattr(cliente, 'departamento', None) or '06').strip().zfill(2) if cliente else '06'
        codigo_municipio = str(getattr(cliente, 'municipio', None) or '14').strip().zfill(2) if cliente else '14'

        # Consumidor Final sin cliente: datos de venta.direccion_receptor, correo_receptor, documento_receptor
        if not cliente:
            nombre = self.venta.nombre_receptor or "Consumidor Final"
            doc = getattr(self.venta, 'documento_receptor', None) and str(self.venta.documento_receptor).strip()
            tdoc = getattr(self.venta, 'tipo_doc_receptor', None) or 'NIT'
            tipo_doc = "36" if tdoc == 'NIT' and doc else "13" if doc else None
            if doc:
                doc_limpio = doc.replace('-', '').replace(' ', '')
                # DUI (tipo 13) → 9 dígitos; NIT (tipo 36) → 14 dígitos
                num_doc = doc_limpio.zfill(9) if tipo_doc == "13" else doc_limpio.zfill(14)
            else:
                num_doc = None
            dir_comp = getattr(self.venta, 'direccion_receptor', None) and str(self.venta.direccion_receptor).strip()
            correo = getattr(self.venta, 'correo_receptor', None) and str(self.venta.correo_receptor).strip()
            direccion_obj = {
                "departamento": "06",
                "municipio": "14",
                "complemento": dir_comp or "San Salvador",
            }
            return {
                "tipoDocumento": tipo_doc,
                "numDocumento": num_doc,
                "nombre": nombre,
                "nrc": None,
                "codActividad": None,
                "descActividad": None,
                "direccion": direccion_obj,
                "telefono": "22222222",
                "correo": correo,
            }

        nombre_receptor = self.venta.nombre_receptor or cliente.nombre or "Consumidor Final"
        tiene_nit = cliente.nit and str(cliente.nit).strip()
        tiene_dui = cliente.dui and str(cliente.dui).strip()
        telefono = getattr(cliente, 'telefono', None) or "22222222"

        receptor = {}
        if tiene_nit:
            receptor["tipoDocumento"] = "36"
            # NIT: exactamente 14 dígitos
            receptor["numDocumento"] = cliente.nit.replace('-', '').replace(' ', '').zfill(14)
        elif tiene_dui:
            receptor["tipoDocumento"] = "13"
            # DUI: exactamente 9 dígitos (NO zfill(14) — MH rechaza DUI de 14 dígitos)
            receptor["numDocumento"] = cliente.dui.replace('-', '').replace(' ', '').zfill(9)
        else:
            receptor["tipoDocumento"] = None
            receptor["numDocumento"] = None

        receptor["nombre"] = nombre_receptor
        receptor["nrc"] = None
        receptor["codActividad"] = None
        receptor["descActividad"] = None
        receptor["telefono"] = telefono

        if cliente.direccion and str(cliente.direccion).strip():
            receptor["direccion"] = {
                "departamento": codigo_departamento,
                "municipio": codigo_municipio,
                "complemento": cliente.direccion
            }
        else:
            receptor["direccion"] = None

        if cliente.email_contacto:
            receptor["correo"] = cliente.email_contacto
        else:
            receptor["correo"] = None

        return receptor

    def _construir_cuerpo_documento(self):
        """Cuerpo FC: precioUni incluye IVA, ivaItem para desglose. tributos=None."""
        return self._generar_items(tipo_dte='01', incluir_iva_item=True)

    def _construir_resumen(self, cuerpo_documento):
        """Resumen FC: totalIva, tributos=None, NO ivaPerci1."""
        total_gravado = float(sum(i.get("ventaGravada", 0) for i in cuerpo_documento))
        total_exento = float(sum(i.get("ventaExenta", 0) for i in cuerpo_documento))
        total_no_sujeto = float(sum(i.get("ventaNoSuj", 0) for i in cuerpo_documento))
        total_descu = float(sum(i.get("montoDescu", 0) for i in cuerpo_documento))
        total_iva = float(sum(i.get("ivaItem", 0) for i in cuerpo_documento))

        subtotal_ventas = round(total_gravado + total_exento + total_no_sujeto, 2)
        monto_total_operacion = round(subtotal_ventas, 2)
        iva_retenido_1 = float(self.venta.iva_retenido_1 or 0) if self.venta.iva_retenido_1 is not None else 0.0
        iva_retenido_2 = float(self.venta.iva_retenido_2 or 0) if self.venta.iva_retenido_2 is not None else 0.0
        rete_renta = float(self.venta.rete_renta or 0) if hasattr(self.venta, 'rete_renta') and self.venta.rete_renta is not None else 0.0
        total_pagar = round(monto_total_operacion - iva_retenido_1 - iva_retenido_2, 2)

        condicion_op = int(getattr(self.venta, 'condicion_operacion', 1) or 1)
        # MH esquema fe-fc-v1 (mismo patrón que CCF):
        #   plazo  → string "01"|"02"|"03" (Días|Semanas|Meses)
        #   periodo → number entero (cantidad de unidades)
        plazo_raw = str(getattr(self.venta, 'plazo_pago', '') or '').strip()
        periodo_raw = str(getattr(self.venta, 'periodo_pago', '') or '').strip()

        if condicion_op == 2:
            plazo_val = plazo_raw if plazo_raw in ("01", "02", "03") else "03"
            try:
                periodo_val = int(periodo_raw)
            except (ValueError, TypeError):
                periodo_val = 30
        else:
            plazo_val = None
            periodo_val = None

        pagos = [{
            "codigo": "01",
            "montoPago": round(total_pagar, 2),
            "referencia": None,
            "periodo": periodo_val,
            "plazo": plazo_val,
        }]

        resumen = {
            "totalNoSuj": round(total_no_sujeto, 2),
            "totalExenta": round(total_exento, 2),
            "totalGravada": round(total_gravado, 2),
            "subTotalVentas": round(subtotal_ventas, 2),
            "descuNoSuj": 0.00,
            "descuExenta": 0.00,
            "descuGravada": round(total_descu, 2),
            "porcentajeDescuento": 0.00,
            "totalDescu": round(total_descu, 2),
            "tributos": None,
            "subTotal": round(subtotal_ventas - total_descu, 2),
            "reteRenta": round(rete_renta, 2),
            "ivaRete1": round(iva_retenido_1, 2),
            "montoTotalOperacion": monto_total_operacion,
            "totalNoGravado": 0.00,
            "totalIva": round(total_iva, 2),
            "saldoFavor": 0.00,
            "totalPagar": total_pagar,
            "totalLetras": self._numero_a_letras(total_pagar),
            "condicionOperacion": condicion_op,
            "pagos": pagos,
            "numPagoElectronico": None,
        }
        return resumen

    def _campos_requeridos_mh(self):
        """fe-fc-v1 envelope v1: mantener todos los campos requeridos como null."""
        base = super()._campos_requeridos_mh()
        extra = [
            "receptor.nrc", "receptor.codActividad", "receptor.descActividad",
            "receptor.tipoDocumento", "receptor.numDocumento", "receptor.direccion", "receptor.correo",
            "resumen.tributos",
        ]
        for c in extra:
            if c not in base:
                base.append(c)
        return base
