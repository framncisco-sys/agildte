"""
Builder para DTE-01 (Factura Consumidor Final).
Esquema fe-f-v2 - Sin NRC, sin nombreComercial en receptor cuando Consumidor Final.
Cuerpo: precioUni incluye IVA, ivaItem para desglose.
"""
from .dte_03_builder import DTE03Builder
from api.utils.mh_direccion import armar_direccion_mh


class DTE01Builder(DTE03Builder):
    """Builder para Factura Consumidor Final (DTE-01) - Esquema fe-f-v2."""

    TIPO_DTE = '01'
    VERSION_DTE = 2
    NOMBRE_CF_DEFAULT = "Consumidor Final"

    def _construir_emisor(self):
        """Emisor fe-f-v2."""
        return super()._construir_emisor()

    def _construir_receptor(self):
        """
        Receptor DTE-01: Consumidor Final.
        - Nombre vacío -> "Consumidor Final".
        - Dirección vacía -> null (fe-f-v2 permite receptor.direccion null).
        - No enviar campos nulos que Hacienda rechaza (nombreComercial, nrc si no existen).
        """
        cliente = self.venta.cliente

        # CAT-013 v1.1: San Salvador Centro=23; CAT-008: distrito San Salvador=14
        # Prioridad: snapshot venta > cliente > defaults SS Centro (solo si hay complemento)
        depto_v = getattr(self.venta, 'departamento_receptor', None)
        muni_v = getattr(self.venta, 'municipio_receptor', None)
        dist_v = getattr(self.venta, 'distrito_receptor', None)

        codigo_departamento = str(
            depto_v or (getattr(cliente, 'departamento', None) if cliente else None) or '06'
        ).strip().zfill(2)
        codigo_municipio = str(
            muni_v or (getattr(cliente, 'municipio', None) if cliente else None) or '23'
        ).strip().zfill(2)
        codigo_distrito = str(
            dist_v or (getattr(cliente, 'distrito', None) if cliente else None) or ''
        ).strip() or None
        if codigo_distrito:
            codigo_distrito = codigo_distrito.zfill(2)

        from ..mh_documento import normalizar_telefono_mh, normalizar_tipo_y_numero_mh, documento_cliente_para_mh

        dir_comp = (
            str(getattr(self.venta, 'direccion_receptor', None) or '').strip()
            or (str(getattr(cliente, 'direccion', None) or '').strip() if cliente else '')
        )
        direccion_obj = None
        if dir_comp:
            direccion_obj = armar_direccion_mh(
                codigo_departamento,
                codigo_municipio,
                dir_comp,
                distrito=codigo_distrito or '14',
            )

        if not cliente:
            nombre = (
                (getattr(self.venta, 'nombre_receptor', None) or '').strip()
                or self.NOMBRE_CF_DEFAULT
            )
            doc = getattr(self.venta, 'documento_receptor', None) and str(self.venta.documento_receptor).strip()
            tdoc = getattr(self.venta, 'tipo_doc_receptor', None) or None
            try:
                tipo_doc, num_doc = normalizar_tipo_y_numero_mh(tdoc, doc) if doc else (None, None)
                if tipo_doc == "13" and num_doc:
                    tipo_doc = None
            except ValueError:
                tipo_doc, num_doc = None, None
            correo = str(getattr(self.venta, 'correo_receptor', None) or '').strip() or None
            if correo and not ('@' in correo and '.' in correo.split('@')[-1]):
                correo = None
            tel_raw = getattr(self.venta, 'telefono_receptor', None)
            telefono = normalizar_telefono_mh(tel_raw) if tel_raw else None
            return {
                "tipoDocumento": tipo_doc,
                "numDocumento": num_doc,
                "nombre": nombre,
                "nrc": None,
                "codActividad": None,
                "descActividad": None,
                "direccion": direccion_obj,
                "telefono": telefono,
                "correo": correo,
            }

        nombre_receptor = (
            (self.venta.nombre_receptor or '').strip()
            or (cliente.nombre or '').strip()
            or self.NOMBRE_CF_DEFAULT
        )
        tel_raw = (
            getattr(self.venta, "telefono_receptor", None)
            or getattr(cliente, "telefono", None)
        )
        telefono = normalizar_telefono_mh(tel_raw)

        receptor = {}
        try:
            tipo_doc, num_doc = documento_cliente_para_mh(cliente)
        except ValueError:
            tipo_doc, num_doc = None, None
        # fe-f-v2: MH rechaza receptor.tipoDocumento "13" (DUI) en CF.
        if tipo_doc == "13" and num_doc:
            tipo_doc = None
        receptor["tipoDocumento"] = tipo_doc
        receptor["numDocumento"] = num_doc

        receptor["nombre"] = nombre_receptor
        receptor["nrc"] = None
        receptor["codActividad"] = None
        receptor["descActividad"] = None
        receptor["telefono"] = telefono
        receptor["direccion"] = direccion_obj

        correo_val = (
            str(getattr(self.venta, 'correo_receptor', None) or '').strip()
            or (cliente.email_contacto or '').strip()
        )
        if correo_val and '@' in correo_val and '.' in correo_val.split('@')[-1]:
            receptor["correo"] = correo_val[:100]
        else:
            receptor["correo"] = None

        return receptor

    def _construir_cuerpo_documento(self):
        """Cuerpo FC: precioUni incluye IVA, ivaItem para desglose. tributos=None."""
        return self._generar_items(tipo_dte='01', incluir_iva_item=True)

    def _construir_resumen(self, cuerpo_documento):
        """Resumen FC fe-f-v2: montos de línea ya netos de montoDescu."""
        total_gravado = float(sum(i.get("ventaGravada", 0) for i in cuerpo_documento))
        total_exento = float(sum(i.get("ventaExenta", 0) for i in cuerpo_documento))
        total_no_sujeto = float(sum(i.get("ventaNoSuj", 0) for i in cuerpo_documento))
        total_descu = float(sum(i.get("montoDescu", 0) for i in cuerpo_documento))
        total_iva = float(sum(i.get("ivaItem", 0) for i in cuerpo_documento))
        total_no_gravado = float(sum(i.get("noGravado", 0) for i in cuerpo_documento))

        # ventaGravada/Exenta/NoSuj ya vienen netas de descuento de línea.
        # descuGravada del schema es descuento GLOBAL; no volver a restar totalDescu.
        subtotal_ventas = round(total_gravado + total_exento + total_no_sujeto, 2)
        descu_global_gravada = 0.00
        sub_total = round(subtotal_ventas - descu_global_gravada, 2)
        monto_total_operacion = round(sub_total, 2)
        iva_retenido_1 = float(self.venta.iva_retenido_1 or 0) if self.venta.iva_retenido_1 is not None else 0.0
        total_pagar = round(max(monto_total_operacion - iva_retenido_1, 0), 2)

        condicion_op = int(getattr(self.venta, 'condicion_operacion', 1) or 1)
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

        observaciones = (getattr(self.venta, 'observaciones', None) or '').strip() or None

        return {
            "totalNoSuj": round(total_no_sujeto, 2),
            "totalExenta": round(total_exento, 2),
            "totalGravada": round(total_gravado, 2),
            "subTotalVentas": round(subtotal_ventas, 2),
            "descuNoSuj": 0.00,
            "descuExenta": 0.00,
            "descuGravada": round(descu_global_gravada, 2),
            "porcentajeDescuento": 0.00,
            "totalDescu": round(total_descu, 2),
            "tributos": [],
            "subTotal": sub_total,
            "ivaRete": round(iva_retenido_1, 2),
            "montoTotalOperacion": monto_total_operacion,
            "totalNoGravado": round(total_no_gravado, 2),
            "totalIva": round(total_iva, 2),
            "saldoFavor": 0.00,
            "totalPagar": total_pagar,
            "totalLetras": self._numero_a_letras(total_pagar),
            "condicionOperacion": condicion_op,
            "pagos": pagos,
            "numPagoElectronico": None,
            "observaciones": observaciones,
        }

    def _campos_requeridos_mh(self):
        """fe-f-v2: campos requeridos que pueden ser null."""
        base = super()._campos_requeridos_mh()
        extra = [
            "receptor.nrc", "receptor.codActividad", "receptor.descActividad",
            "receptor.tipoDocumento", "receptor.numDocumento",
            "receptor.direccion", "receptor.telefono", "receptor.correo",
            "resumen.tributos",
        ]
        for c in extra:
            if c not in base:
                base.append(c)
        return base
