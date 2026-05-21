"""
Repara líneas de venta creadas desde PosAgil cuando precio_unitario llega en 0
pero subtotal/total del payload sí traen el monto cobrado.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from api.constants import DTE_LINEA_DESCRIPCION_MAX_LENGTH


def _dec(val, default: str = '0') -> Decimal:
    try:
        return Decimal(str(val if val is not None else default))
    except (ValueError, TypeError):
        return Decimal(default)


def es_consumidor_final_dte(tipo_dte: str | None, tipo_venta: str | None) -> bool:
    td = (tipo_dte or '').strip()
    if td in ('01', '1'):
        return True
    tv = (tipo_venta or '').strip().upper()
    return tv == 'CF' and not td


def aplicar_monto_linea_cf(cant: Decimal, total_con_iva: Decimal) -> dict[str, Decimal]:
    total_con_iva = total_con_iva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    monto_gravado = (total_con_iva / Decimal('1.13')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    iva_linea = (total_con_iva - monto_gravado).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    pu_sin_iva = (
        (monto_gravado / cant).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
        if cant > 0
        else monto_gravado
    )
    return {
        'precio_unitario': pu_sin_iva,
        'venta_gravada': monto_gravado,
        'iva_item': iva_linea,
        'venta_no_sujeta': Decimal('0.00'),
        'venta_exenta': Decimal('0.00'),
        'monto_descuento': Decimal('0.00'),
    }


def reparar_detalles_venta_desde_payload_pos(venta, payload: dict[str, Any]) -> bool:
    """
    Ajusta DetalleVenta según el JSON crudo del POS (antes de facturar ante MH).
    Retorna True si modificó algo.
    """
    from ..models import DetalleVenta

    if not payload or not isinstance(payload, dict):
        return False

    tipo_dte = payload.get('tipo_dte')
    tipo_venta = getattr(venta, 'tipo_venta', None) or payload.get('tipo_venta')
    es_cf = es_consumidor_final_dte(
        str(tipo_dte) if tipo_dte is not None else None,
        str(tipo_venta) if tipo_venta is not None else None,
    )

    raw_detalles = payload.get('detalles') or []
    if not isinstance(raw_detalles, list):
        raw_detalles = []

    detalles_db = list(venta.detalles.all().order_by('numero_item', 'id'))
    cambio = False

    for idx, raw in enumerate(raw_detalles):
        if not isinstance(raw, dict):
            continue
        cant = _dec(raw.get('cantidad', 1), '1')
        if cant <= 0:
            continue
        pu = _dec(raw.get('precio_unitario', 0))
        st = raw.get('subtotal')
        st_dec = _dec(st) if st is not None else (pu * cant).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        if pu <= 0 and st_dec > 0:
            pu = (st_dec / cant).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)

        total_linea = (pu * cant).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if st_dec > 0:
            total_linea = st_dec

        if total_linea <= 0:
            continue

        if idx >= len(detalles_db):
            continue
        d = detalles_db[idx]
        if es_cf:
            montos = aplicar_monto_linea_cf(cant, total_linea)
            d.precio_unitario = montos['precio_unitario']
            d.venta_gravada = montos['venta_gravada']
            d.iva_item = montos['iva_item']
            d.venta_no_sujeta = montos['venta_no_sujeta']
            d.venta_exenta = montos['venta_exenta']
            d.monto_descuento = montos['monto_descuento']
        else:
            d.precio_unitario = pu
            d.venta_gravada = total_linea
            d.iva_item = (total_linea * Decimal('0.13')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

        desc = (raw.get('descripcion_libre') or raw.get('nombre') or raw.get('descripcion') or '').strip()
        if desc:
            d.descripcion_libre = desc[:DTE_LINEA_DESCRIPCION_MAX_LENGTH]
        elif (d.descripcion_libre or '').strip().lower() == 'item sin producto':
            d.descripcion_libre = 'Venta POS'
        d.cantidad = cant
        d.save()
        cambio = True

    # Sincronizar teléfono y documento del payload POS al cliente AgilDTE
    if venta.cliente_id:
        try:
            c = venta.cliente
            if c:
                from .mh_documento import documento_receptor_desde_payload, normalizar_telefono_mh

                tel_payload = (payload.get('receptor_telefono') or '').strip()
                if tel_payload:
                    c.telefono = normalizar_telefono_mh(tel_payload)
                    cambio = True

                doc_payload = (
                    (payload.get('documento_receptor') or '').strip()
                    or (payload.get('nit_receptor') or '').strip()
                )
                if doc_payload:
                    tipo_p = (payload.get('tipo_doc_receptor') or '').strip() or None
                    tipo_doc, nit_v, dui_v, doc_id = documento_receptor_desde_payload(tipo_p, doc_payload)
                    if tipo_doc:
                        c.tipo_documento = tipo_doc
                    if nit_v is not None:
                        c.nit = nit_v
                    if dui_v is not None:
                        c.dui = dui_v
                    if doc_id:
                        c.documento_identidad = doc_id
                    cambio = True
                if cambio:
                    c.save()
        except Exception:
            pass

    suma_grav = sum(_dec(d.venta_gravada) for d in venta.detalles.all())
    if suma_grav <= 0:
        total_req = _dec(payload.get('total'))
        if total_req > 0 and es_cf:
            if detalles_db:
                d = detalles_db[0]
                montos = aplicar_monto_linea_cf(Decimal('1.00'), total_req)
                d.cantidad = Decimal('1.00')
                d.precio_unitario = montos['precio_unitario']
                d.venta_gravada = montos['venta_gravada']
                d.iva_item = montos['iva_item']
                if not (d.descripcion_libre or '').strip():
                    d.descripcion_libre = 'Venta POS'
                if not (d.codigo_libre or '').strip():
                    d.codigo_libre = 'LIBRE'
                d.save()
                cambio = True
            else:
                montos = aplicar_monto_linea_cf(Decimal('1.00'), total_req)
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=None,
                    descripcion_libre='Venta POS',
                    codigo_libre='LIBRE',
                    numero_item=1,
                    cantidad=Decimal('1.00'),
                    **montos,
                )
                cambio = True

    if cambio:
        venta.calcular_totales()
        venta.save()
    return cambio
