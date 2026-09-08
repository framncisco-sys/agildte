"""
Identidades MH para ítems DTE.

Hacienda (código 003):
  round(precioUni * cantidad - montoDescu, 2)
    == ventaGravada + ventaExenta + ventaNoSuj

DTE-01 (CF): precioUni y ventaGravada van CON IVA.
  ivaItem == round(ventaGravada * 13 / 113, 2)
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

Q2 = Decimal('0.01')
Q8 = Decimal('0.00000001')
IVA = Decimal('1.13')
IVA_NUM = Decimal('13')
IVA_DEN = Decimal('113')


def _d(val, default: str = '0') -> Decimal:
    try:
        if val is None or val == '':
            return Decimal(default)
        return Decimal(str(val))
    except (ValueError, TypeError, ArithmeticError):
        return Decimal(default)


def money2(val) -> float:
    return float(_d(val).quantize(Q2, rounding=ROUND_HALF_UP))


def precio8(val) -> float:
    return float(_d(val).quantize(Q8, rounding=ROUND_HALF_UP))


def iva_item_cf(venta_gravada_con_iva) -> float:
    vg = _d(venta_gravada_con_iva)
    return money2(vg * IVA_NUM / IVA_DEN)


def total_linea_mh(precio_uni, cantidad, monto_descu=0) -> float:
    return money2(_d(precio_uni) * _d(cantidad) - _d(monto_descu))


def linea_mh_coherente(item: dict[str, Any], *, tolerancia: float = 0.005) -> bool:
    calc = total_linea_mh(
        item.get('precioUni', 0),
        item.get('cantidad', 0),
        item.get('montoDescu', 0),
    )
    suma = money2(
        _d(item.get('ventaGravada', 0))
        + _d(item.get('ventaExenta', 0))
        + _d(item.get('ventaNoSuj', 0))
    )
    return abs(calc - suma) < tolerancia


def alinear_precio_a_total(cantidad, total_linea, monto_descu=0) -> tuple[float, float]:
    """
    precioUni a 8 decimales tal que round(pu * cant - desc, 2) == total_linea (cobro).
    No cambia el cobro: si el primer redondeo descuadra 1 centavo, ajusta precioUni.
    Casos: 250 × $0.044 = $11.00 (788); 3 × $1.10 = $3.30 (0338).
    """
    cant = _d(cantidad)
    total = _d(total_linea).quantize(Q2, rounding=ROUND_HALF_UP)
    desc = _d(monto_descu).quantize(Q2, rounding=ROUND_HALF_UP)
    if cant <= 0:
        return precio8(total), money2(total)
    pu = ((total + desc) / cant).quantize(Q8, rounding=ROUND_HALF_UP)
    for _ in range(80):
        calc = (pu * cant - desc).quantize(Q2, rounding=ROUND_HALF_UP)
        if calc == total:
            return float(pu), float(total)
        diff = total - calc
        ajuste = (diff / cant).quantize(Q8, rounding=ROUND_HALF_UP)
        if ajuste == 0:
            ajuste = Q8 if diff > 0 else -Q8
        pu = pu + ajuste
        if pu < 0:
            pu = Decimal('0')
            break
    return float(pu), float(total)


def forzar_identidad_mh_item(item: dict[str, Any]) -> dict[str, Any]:
    """Garantiza código MH 003 sobre un ítem ya armado (DTE-01/03)."""
    vg = money2(item.get('ventaGravada', 0))
    ve = money2(item.get('ventaExenta', 0))
    vn = money2(item.get('ventaNoSuj', 0))
    desc = money2(item.get('montoDescu', 0))
    cant = item.get('cantidad', 1) or 1
    objetivo = money2(_d(vg) + _d(ve) + _d(vn))
    if objetivo <= 0:
        return item
    pu, total_ok = alinear_precio_a_total(cant, objetivo, desc)
    item['precioUni'] = pu
    if vg > 0:
        item['ventaGravada'] = total_ok
        if 'ivaItem' in item:
            item['ivaItem'] = iva_item_cf(total_ok)
    elif ve > 0:
        item['ventaExenta'] = total_ok
    else:
        item['ventaNoSuj'] = total_ok
    item['montoDescu'] = desc
    return item


def cobro_con_iva_detalle(detalle) -> Decimal:
    vg = _d(getattr(detalle, 'venta_gravada', 0))
    iva = _d(getattr(detalle, 'iva_item', 0))
    ve = _d(getattr(detalle, 'venta_exenta', 0))
    vn = _d(getattr(detalle, 'venta_no_sujeta', 0))
    if iva > 0:
        return (vg + iva + ve + vn).quantize(Q2, rounding=ROUND_HALF_UP)
    if vg > 0:
        return (vg * IVA).quantize(Q2, rounding=ROUND_HALF_UP)
    return (ve + vn).quantize(Q2, rounding=ROUND_HALF_UP)


def aplicar_cobro_cf_a_detalle(detalle, cobro_con_iva) -> None:
    """Ajusta una línea CF (BD: venta_gravada SIN IVA) al cobro CON IVA del POS."""
    cobro = _d(cobro_con_iva).quantize(Q2, rounding=ROUND_HALF_UP)
    cant = _d(getattr(detalle, 'cantidad', 1) or 1)
    if cant <= 0:
        cant = Decimal('1')
        detalle.cantidad = cant
    vg = (cobro / IVA).quantize(Q2, rounding=ROUND_HALF_UP)
    iva = (cobro - vg).quantize(Q2, rounding=ROUND_HALF_UP)
    detalle.venta_gravada = vg
    detalle.iva_item = iva
    detalle.precio_unitario = (vg / cant).quantize(Q8, rounding=ROUND_HALF_UP) if cant else vg
    detalle.venta_exenta = Decimal('0.00')
    detalle.venta_no_sujeta = Decimal('0.00')


def alinear_detalles_cf_al_cobro(detalles, cobro_con_iva) -> bool:
    """
    Si la suma de líneas no es el total cobrado en caja (ej. 807: $1.05 vs $1.00),
    ajusta la última línea gravada. Evita 003 por descuadre cabecera/detalle.
    """
    cobro = _d(cobro_con_iva).quantize(Q2, rounding=ROUND_HALF_UP)
    if cobro <= 0:
        return False
    filas = list(detalles)
    if not filas:
        return False
    suma = sum((cobro_con_iva_detalle(d) for d in filas), Decimal('0.00'))
    if suma == cobro:
        return False
    ultima = None
    for d in reversed(filas):
        if cobro_con_iva_detalle(d) > 0:
            ultima = d
            break
    if ultima is None:
        ultima = filas[-1]
    delta = cobro - suma
    nuevo = cobro_con_iva_detalle(ultima) + delta
    if nuevo <= 0:
        return False
    aplicar_cobro_cf_a_detalle(ultima, nuevo)
    return True


def cobro_cf_desde_payload(payload) -> Decimal:
    """Total cobrado en caja (POS envía `total` CON IVA)."""
    if not payload or not isinstance(payload, dict):
        return Decimal('0.00')
    for key in ('total', 'total_neto', 'montoTotalOperacion'):
        raw = payload.get(key)
        if raw is None or str(raw).strip() == '':
            continue
        val = _d(raw).quantize(Q2, rounding=ROUND_HALF_UP)
        if val > 0:
            return val
    return Decimal('0.00')


def total_con_iva_linea_cf(
    cantidad,
    precio_unitario,
    subtotal=None,
    venta_gravada=0,
    iva_item=0,
) -> Decimal:
    """
    Monto cobrado CON IVA de una línea CF.

    POS Ágil envía precio/subtotal CON IVA (a veces sin venta_gravada).
    El portal AgilDTE envía venta_gravada SIN IVA + iva_item.
    """
    cant = _d(cantidad, '1')
    prec = _d(precio_unitario)
    total_linea = (cant * prec).quantize(Q2, rounding=ROUND_HALF_UP)
    if subtotal is not None and str(subtotal).strip() != '':
        st = _d(subtotal).quantize(Q2, rounding=ROUND_HALF_UP)
        if st > 0:
            total_linea = st

    vg = _d(venta_gravada)
    iva = _d(iva_item)
    if total_linea <= 0 and vg <= 0:
        return Decimal('0.00')

    iva_si_vg_fuera_total = (vg - vg / IVA).quantize(Q2, rounding=ROUND_HALF_UP)
    if vg > 0 and abs(iva - iva_si_vg_fuera_total) <= Decimal('0.03'):
        # venta_gravada vino como total CON IVA (payload legado)
        return vg.quantize(Q2, rounding=ROUND_HALF_UP)

    suma_desglose = (vg + iva).quantize(Q2, rounding=ROUND_HALF_UP)
    if suma_desglose > 0:
        if total_linea > 0 and abs(suma_desglose - total_linea) <= Decimal('0.03'):
            return total_linea
        # Portal: cant*precio es SIN IVA; vg+iva es el cobro real
        return suma_desglose

    return total_linea if total_linea > 0 else Decimal('0.00')


def montos_item_dte01_gravado(
    *,
    cantidad,
    precio_unitario_bd,
    venta_gravada_bd,
    iva_item_bd,
    monto_descuento=0,
) -> dict[str, float]:
    """Reconstruye línea CF CON IVA coherente con el cobro POS y con MH 003."""
    cant = _d(cantidad)
    desc = _d(monto_descuento).quantize(Q2, rounding=ROUND_HALF_UP)
    vg = _d(venta_gravada_bd)
    iva = _d(iva_item_bd)
    pu_bd = _d(precio_unitario_bd)

    if vg > 0 and iva > 0:
        total_con = (vg + iva).quantize(Q2, rounding=ROUND_HALF_UP)
    elif vg > 0:
        total_con = (vg * IVA).quantize(Q2, rounding=ROUND_HALF_UP)
    else:
        total_sin = (pu_bd * cant).quantize(Q2, rounding=ROUND_HALF_UP) - desc
        if total_sin < 0:
            total_sin = Decimal('0.00')
        total_con = (total_sin * IVA).quantize(Q2, rounding=ROUND_HALF_UP)

    pu, v_grav = alinear_precio_a_total(cant, total_con, desc)
    return {
        'precioUni': pu,
        'ventaGravada': v_grav,
        'ventaExenta': 0.0,
        'ventaNoSuj': 0.0,
        'ivaItem': iva_item_cf(v_grav),
        'montoDescu': money2(desc),
        'cantidad': float(cant),
    }


def montos_item_dte_neto(
    *,
    cantidad,
    precio_unitario_bd,
    venta_gravada_bd=0,
    venta_exenta_bd=0,
    venta_nosuj_bd=0,
    monto_descuento=0,
) -> dict[str, float]:
    """CCF/NC/ND: precioUni y ventaGravada SIN IVA, alineados a identidad MH."""
    cant = _d(cantidad)
    desc = _d(monto_descuento).quantize(Q2, rounding=ROUND_HALF_UP)
    pu_bd = _d(precio_unitario_bd)
    vg = _d(venta_gravada_bd)
    ve = _d(venta_exenta_bd)
    vn = _d(venta_nosuj_bd)

    monto_calc = (pu_bd * cant).quantize(Q2, rounding=ROUND_HALF_UP) - desc
    if vg > 0:
        total = vg.quantize(Q2, rounding=ROUND_HALF_UP)
        v_grav, v_exenta, v_nosuj = float(total), 0.0, 0.0
    elif ve > 0:
        total = ve.quantize(Q2, rounding=ROUND_HALF_UP)
        v_grav, v_exenta, v_nosuj = 0.0, float(total), 0.0
    elif vn > 0:
        total = vn.quantize(Q2, rounding=ROUND_HALF_UP)
        v_grav, v_exenta, v_nosuj = 0.0, 0.0, float(total)
    else:
        total = monto_calc if monto_calc > 0 else Decimal('0.00')
        v_grav, v_exenta, v_nosuj = float(total), 0.0, 0.0

    pu, total_ok = alinear_precio_a_total(cant, total, desc)
    if v_grav:
        v_grav = total_ok
    elif v_exenta:
        v_exenta = total_ok
    else:
        v_nosuj = total_ok
    return {
        'precioUni': pu,
        'ventaGravada': v_grav,
        'ventaExenta': v_exenta,
        'ventaNoSuj': v_nosuj,
        'ivaItem': money2(_d(v_grav) * Decimal('0.13')) if v_grav else 0.0,
        'montoDescu': money2(desc),
        'cantidad': float(cant),
    }
