"""
Builder para DTE-03 (Comprobante Crédito Fiscal).
Esquema fe-ccf-v3 - Contribuyente con NRC, Nombre Comercial, Actividad.
"""
from .base_builder import BaseDTEBuilder
from api.dte_generator import formatear_decimal


class DTE03Builder(BaseDTEBuilder):
    """Builder para Crédito Fiscal (DTE-03)."""

    TIPO_DTE = '03'
    VERSION_DTE = 3

    def _construir_receptor(self):
        """Receptor CCF: NRC, Nombre Comercial, codActividad, descActividad obligatorios.
        Prioriza nrc_receptor/cod_actividad_receptor/desc_actividad_receptor de la Venta
        sobre los campos del cliente en BD (permite editar desde el formulario sin cambiar el cliente).
        """
        cliente = self.venta.cliente
        if not cliente:
            raise ValueError("DTE-03 (Crédito Fiscal) requiere cliente con NRC.")

        codigo_departamento = str(getattr(cliente, 'departamento', None) or '06').strip().zfill(2)
        codigo_municipio = str(getattr(cliente, 'municipio', None) or '14').strip().zfill(2)

        # nrc: primero usar el que viene del formulario (nrc_receptor), luego el del cliente en BD
        nrc_receptor_venta = str(self.venta.nrc_receptor or '').strip()
        ambiente_actual = getattr(self.venta.empresa, 'ambiente', '00') or '00'
        nrc_cliente = nrc_receptor_venta or cliente.nrc or ("0000000" if ambiente_actual == '00' else None)
        if not nrc_cliente:
            raise ValueError(f"Cliente '{cliente.nombre}' no tiene NRC. DTE-03 requiere Contribuyente con NRC.")

        # MH requiere NIT/DUI con el cero inicial. Excel elimina ceros al inicio.
        # Regla de normalización:
        #   8 dígitos  → DUI incompleto (Excel quitó el 0) → agregar "0" → 9 dígitos
        #   9 dígitos  → DUI correcto
        #   13 dígitos → NIT incompleto (Excel quitó el 0) → agregar "0" → 14 dígitos
        #   14 dígitos → NIT correcto
        doc_raw = str(cliente.nit or cliente.dui or getattr(cliente, 'documento_identidad', '') or "").strip()
        doc_limpio = ''.join(c for c in doc_raw.replace('-', '').replace(' ', '') if c.isdigit())
        if len(doc_limpio) == 10:
            doc_limpio = doc_limpio[:9]   # DUI con dígito verificador extra, recortar
        elif len(doc_limpio) == 8:
            doc_limpio = '0' + doc_limpio  # Excel quitó el cero → DUI de 9 dígitos
        elif len(doc_limpio) == 13:
            doc_limpio = '0' + doc_limpio  # Excel quitó el cero → NIT de 14 dígitos
        if not doc_limpio or len(doc_limpio) < 9:
            raise ValueError(
                f"Cliente '{cliente.nombre}' (NRC {cliente.nrc}): sin identificación válida. "
                "Ingrese NIT (14 dígitos) o DUI (9 dígitos) en la columna 'nit' del Excel."
            )
        doc_limpio = doc_limpio[:14]
        es_dui = len(doc_limpio) == 9
        nombre_receptor = self.venta.nombre_receptor or (
            getattr(cliente, 'nombre_comercial', None) or
            getattr(cliente, 'razon_social', None) or
            cliente.nombre
        )
        nombre_comercial = (
            getattr(cliente, 'nombre_comercial', None) or
            getattr(cliente, 'razon_social', None) or
            nombre_receptor
        )
        # Actividad: primero la del formulario, luego la del cliente en BD
        cod_actividad = str(getattr(self.venta, 'cod_actividad_receptor', '') or '').strip() or cliente.cod_actividad or "10005"
        desc_actividad = str(getattr(self.venta, 'desc_actividad_receptor', '') or '').strip() or cliente.desc_actividad or (cliente.giro or "Otros")
        telefono = getattr(cliente, 'telefono', None) or "22222222"

        nrc_limpio = ''.join(c for c in str(nrc_cliente or "").replace('-', '').replace(' ', '') if c.isdigit())
        nrc_final = (nrc_limpio or "00000000")[:8]

        # MH fe-ccf-v3: campo "nit" requerido. Enviar dígitos tal como están en BD (sin rellenar
        # con ceros). MH acepta NITs de 9 dígitos (DUI homologado) o 14 dígitos (NIT clásico).
        # NO usar zfill(14): convierte "020579096" → "00000020579096" que MH rechaza.
        nit_enviar = doc_limpio[:14]
        receptor = {
            "nit": nit_enviar,
            "nrc": nrc_final,
            "nombre": nombre_receptor,
            "nombreComercial": nombre_comercial,
            "codActividad": cod_actividad,
            "descActividad": desc_actividad,
            "direccion": {
                "departamento": codigo_departamento,
                "municipio": codigo_municipio,
                "complemento": cliente.direccion and str(cliente.direccion).strip() or "San Miguel"
            },
            "telefono": telefono,
        }
        if cliente.email_contacto:
            receptor["correo"] = cliente.email_contacto
        return receptor

    def _construir_cuerpo_documento(self):
        """Cuerpo CCF: tributos ["20"] si gravado, NO incluir ivaItem (V3)."""
        return self._generar_items(tipo_dte='03', incluir_iva_item=False)

    def _generar_items(self, tipo_dte, incluir_iva_item=False):
        """Genera items del cuerpo. incluir_iva_item=True para DTE-01.

        Para DTE-01 (CF): en BD se guarda precio_unitario y venta_gravada SIN IVA (÷1.13).
        MH exige que precioUni y ventaGravada vayan CON IVA (precio que el usuario ingresó).
        Se reconstruye: total_con_iva = venta_gravada_sin_iva * 1.13
        """
        items = []
        detalles = self.venta.detalles.all().order_by('numero_item')

        if detalles.exists():
            for detalle in detalles:
                codigo_raw = detalle.producto.codigo if detalle.producto else (detalle.codigo_libre or "")
                codigo = str(codigo_raw).strip() if codigo_raw else "ITEM"
                descripcion = detalle.producto.descripcion if detalle.producto else (detalle.descripcion_libre or "Item")
                tipo_item = detalle.producto.tipo_item if detalle.producto else 1
                precio_unitario_bd = float(formatear_decimal(detalle.precio_unitario))
                cantidad = float(formatear_decimal(detalle.cantidad))
                monto_descuento = float(formatear_decimal(detalle.monto_descuento))

                detalle_gravada = float(formatear_decimal(detalle.venta_gravada))
                detalle_exenta = float(formatear_decimal(detalle.venta_exenta))
                detalle_nosuj = float(formatear_decimal(detalle.venta_no_sujeta))

                if tipo_dte == '01':
                    # En BD: precio_unitario y venta_gravada están SIN IVA.
                    # MH CF exige precioUni y ventaGravada CON IVA.
                    # total_sin_iva = precio_unitario_bd * cantidad (≈ venta_gravada en BD)
                    total_sin_iva = round(precio_unitario_bd * cantidad, 2) - monto_descuento
                    if detalle_gravada > 0 or (detalle_exenta == 0 and detalle_nosuj == 0):
                        total_con_iva = round(total_sin_iva * 1.13, 2)
                        iva_item = round(total_con_iva - total_sin_iva, 2)
                        precio_uni_mh = round(total_con_iva / cantidad, 2) if cantidad else total_con_iva
                        v_gravada = total_con_iva
                        v_exenta = 0.0
                        v_nosujeta = 0.0
                    elif detalle_exenta > 0:
                        total_con_iva = round(precio_unitario_bd * cantidad, 2) - monto_descuento
                        iva_item = 0.0
                        precio_uni_mh = precio_unitario_bd
                        v_gravada = 0.0
                        v_exenta = total_con_iva
                        v_nosujeta = 0.0
                    else:
                        total_con_iva = round(precio_unitario_bd * cantidad, 2) - monto_descuento
                        iva_item = 0.0
                        precio_uni_mh = precio_unitario_bd
                        v_gravada = 0.0
                        v_exenta = 0.0
                        v_nosujeta = total_con_iva
                else:
                    # CCF y otros: precio_unitario ya es sin IVA, ventaGravada sin IVA
                    monto_total_linea = round(precio_unitario_bd * cantidad, 2) - monto_descuento
                    if detalle_gravada > 0:
                        v_gravada = round(monto_total_linea, 2)
                        v_exenta = 0.0
                        v_nosujeta = 0.0
                    elif detalle_exenta > 0:
                        v_gravada = 0.0
                        v_exenta = round(monto_total_linea, 2)
                        v_nosujeta = 0.0
                    elif detalle_nosuj > 0:
                        v_gravada = 0.0
                        v_exenta = 0.0
                        v_nosujeta = round(monto_total_linea, 2)
                    else:
                        v_gravada = round(monto_total_linea, 2)
                        v_exenta = 0.0
                        v_nosujeta = 0.0
                    iva_item = round(v_gravada * 0.13, 2) if v_gravada > 0 else 0.0
                    precio_uni_mh = precio_unitario_bd

                tributos = None if tipo_dte == '01' else (["20"] if v_gravada > 0 else [])
                item = {
                    "numItem": detalle.numero_item,
                    "tipoItem": tipo_item,
                    "numeroDocumento": None,
                    "codigo": str(codigo or "ITEM")[:25],
                    "codTributo": None,
                    "descripcion": descripcion,
                    "cantidad": cantidad,
                    "uniMedida": 59,
                    "precioUni": round(precio_uni_mh, 2),
                    "montoDescu": monto_descuento,
                    "ventaNoSuj": round(v_nosujeta, 2),
                    "ventaExenta": round(v_exenta, 2),
                    "ventaGravada": round(v_gravada, 2),
                    "tributos": tributos,
                    "psv": 0.00,
                    "noGravado": 0.00,
                }
                if incluir_iva_item:
                    item["ivaItem"] = round(iva_item, 2)
                items.append(item)
        else:
            items = self._items_desde_totales(tipo_dte, incluir_iva_item)

        if not items:
            items = [self._item_default(tipo_dte, incluir_iva_item)]
        return items

    def _items_desde_totales(self, tipo_dte, incluir_iva_item):
        """Fallback: items desde totales de venta.
        Para CF: venta_gravada en BD está sin IVA. MH exige precioUni y ventaGravada con IVA.
        """
        items = []
        venta_gravada_bd = float(self.venta.venta_gravada or 0)
        venta_exenta = float(self.venta.venta_exenta or 0)
        venta_no_sujeta = float(self.venta.venta_no_sujeta or 0)
        debito_fiscal = float(self.venta.debito_fiscal or 0)

        num_item = 1
        if venta_gravada_bd > 0:
            if tipo_dte == '01':
                # Reconstruir total con IVA desde el valor sin IVA guardado en BD
                venta_gravada_mh = round(venta_gravada_bd * 1.13, 2)
                iva = round(venta_gravada_mh - venta_gravada_bd, 2)
            else:
                venta_gravada_mh = venta_gravada_bd
                iva = round(venta_gravada_bd * 0.13, 2)
            tributos = None if tipo_dte == '01' else (["20"] if debito_fiscal > 0 else [])
            item = {
                "numItem": num_item, "tipoItem": 1, "cantidad": 1.0, "codigo": "PROD001", "codTributo": None,
                "uniMedida": 59, "descripcion": "Venta gravada", "precioUni": venta_gravada_mh, "montoDescu": 0.00,
                "ventaNoSuj": 0.00, "ventaExenta": 0.00, "ventaGravada": venta_gravada_mh,
                "psv": 0.00, "noGravado": 0.00, "numeroDocumento": None, "tributos": tributos
            }
            if incluir_iva_item:
                item["ivaItem"] = iva
            items.append(item)
            num_item += 1

        if venta_exenta > 0:
            tributos = None if tipo_dte == '01' else []
            item = {
                "numItem": num_item, "tipoItem": 1, "cantidad": 1.0, "codigo": "PROD002", "codTributo": None,
                "uniMedida": 59, "descripcion": "Venta exenta", "precioUni": venta_exenta, "montoDescu": 0.00,
                "ventaNoSuj": 0.00, "ventaExenta": venta_exenta, "ventaGravada": 0.00,
                "psv": 0.00, "noGravado": 0.00, "numeroDocumento": None, "tributos": tributos
            }
            if incluir_iva_item:
                item["ivaItem"] = 0.00
            items.append(item)
            num_item += 1

        if venta_no_sujeta > 0:
            tributos = None if tipo_dte == '01' else []
            item = {
                "numItem": num_item, "tipoItem": 1, "cantidad": 1.0, "codigo": "PROD003", "codTributo": None,
                "uniMedida": 59, "descripcion": "Venta no sujeta", "precioUni": venta_no_sujeta, "montoDescu": 0.00,
                "ventaNoSuj": venta_no_sujeta, "ventaExenta": 0.00, "ventaGravada": 0.00,
                "psv": 0.00, "noGravado": 0.00, "numeroDocumento": None, "tributos": tributos
            }
            if incluir_iva_item:
                item["ivaItem"] = 0.00
            items.append(item)
        return items

    def _item_default(self, tipo_dte, incluir_iva_item):
        """Item por defecto cuando no hay detalles.
        Para CF: venta_gravada en BD está sin IVA → reconstruir con IVA para MH.
        """
        venta_gravada_bd = float(formatear_decimal(self.venta.venta_gravada or 0))
        debito = float(formatear_decimal(self.venta.debito_fiscal or 0))
        if tipo_dte == '01':
            venta_gravada_mh = round(venta_gravada_bd * 1.13, 2)
            iva = round(venta_gravada_mh - venta_gravada_bd, 2)
        else:
            venta_gravada_mh = venta_gravada_bd
            iva = round(venta_gravada_bd * 0.13, 2)
        tributos = None if tipo_dte == '01' else (["20"] if debito > 0 else [])
        item = {
            "numItem": 1, "tipoItem": 1, "cantidad": 1.0, "codigo": "PROD001", "codTributo": None,
            "uniMedida": 59, "descripcion": "Venta", "precioUni": venta_gravada_mh, "montoDescu": 0.00,
            "ventaNoSuj": 0.00, "ventaExenta": 0.00, "ventaGravada": venta_gravada_mh,
            "psv": 0.00, "noGravado": 0.00, "numeroDocumento": None, "tributos": tributos
        }
        if incluir_iva_item:
            item["ivaItem"] = iva
        return item

    def _construir_resumen(self, cuerpo_documento):
        """Resumen CCF: ivaPerci1=0, tributos con IVA, NO totalIva."""
        total_gravado = float(sum(i.get("ventaGravada", 0) for i in cuerpo_documento))
        total_exento = float(sum(i.get("ventaExenta", 0) for i in cuerpo_documento))
        total_no_sujeto = float(sum(i.get("ventaNoSuj", 0) for i in cuerpo_documento))
        total_descu = float(sum(i.get("montoDescu", 0) for i in cuerpo_documento))
        total_iva = round(total_gravado * 0.13, 2)

        subtotal_ventas = round(total_gravado + total_exento + total_no_sujeto, 2)
        sub_total = round(subtotal_ventas - total_descu, 2)
        monto_total_operacion = round(sub_total + total_iva, 2)
        iva_retenido_1 = float(self.venta.iva_retenido_1 or 0) if self.venta.iva_retenido_1 is not None else 0.0
        iva_retenido_2 = float(self.venta.iva_retenido_2 or 0) if self.venta.iva_retenido_2 is not None else 0.0
        rete_renta = float(self.venta.rete_renta or 0) if hasattr(self.venta, 'rete_renta') and self.venta.rete_renta is not None else 0.0
        total_pagar = round(monto_total_operacion - iva_retenido_1 - iva_retenido_2, 2)

        tributos_value = [
            {"codigo": "20", "descripcion": "Impuesto al Valor Agregado 13%", "valor": round(total_iva, 2)}
        ] if total_iva > 0 else []

        condicion_op = int(getattr(self.venta, 'condicion_operacion', 1) or 1)
        # MH esquema fe-ccf-v3:
        #   plazo  → string con patrón ^0[1-3]$ : "01"=Días, "02"=Semanas, "03"=Meses
        #   periodo → number (entero): cantidad de unidades (ej: 30)
        plazo_raw = str(getattr(self.venta, 'plazo_pago', '') or '').strip()
        periodo_raw = str(getattr(self.venta, 'periodo_pago', '') or '').strip()

        if condicion_op == 2:
            # plazo debe ser "01", "02" o "03"
            plazo_val = plazo_raw if plazo_raw in ("01", "02", "03") else "03"
            # periodo debe ser un número entero
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
            "tributos": tributos_value,
            "subTotal": sub_total,
            "reteRenta": round(rete_renta, 2),
            "ivaPerci1": 0.0,
            "ivaRete1": round(iva_retenido_1, 2),
            "montoTotalOperacion": monto_total_operacion,
            "totalNoGravado": 0.00,
            "saldoFavor": 0.00,
            "totalPagar": total_pagar,
            "totalLetras": self._numero_a_letras(total_pagar),
            "condicionOperacion": condicion_op,
            "pagos": pagos,
            "numPagoElectronico": None,
        }
        return resumen
