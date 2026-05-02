# Programador: Oscar Amaya Romero
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from decimal import Decimal

from datetime import date

from azdigital.repositories import clientes_repo, empresas_repo, presentaciones_repo, productos_repo, promociones_repo, ventas_repo
from azdigital.utils.conversion_venta import (
    cantidad_base_desde_factor,
    cantidad_base_desde_ui,
    cantidad_base_venta_por_monto,
    texto_presentacion_cantidad,
)
from azdigital.utils.mh_cat003_unidades import normalizar_codigo_mh


@dataclass(frozen=True)
class LineaVenta:
    producto_id: int
    cantidad: float
    precio_unitario: float
    subtotal: float
    texto_cantidad: str | None = None
    presentacion_id: int | None = None


def _calcular_subtotal_con_promo(
    precio: float,
    cantidad: float,
    promocion_tipo: str | None,
    promocion_valor: float,
    valor_comprar: float = 2,
    valor_pagar: float = 1,
    descuento_monto: float | None = None,
) -> tuple[float, float]:
    """
    Aplica promoción al subtotal. Retorna (subtotal, precio_efectivo_unitario).
    - 2X1/3X2/VOLUMEN: comprar X pagar Y. Ej: 3x2 → 6 und = 4*precio.
    - PORCENTAJE: descuento %. Ej: 15% = precio * 0.85.
    - DESCUENTO_MONTO: precio - monto fijo por unidad.
    """
    if cantidad <= 0:
        return 0.0, 0.0
    promo = (promocion_tipo or "").strip().upper()
    valor = float(promocion_valor or 0)
    comprar = float(valor_comprar or 2)
    pagar = float(valor_pagar or 1)
    if comprar <= 0:
        comprar = 2
    if pagar <= 0:
        pagar = 1
    if promo in ("2X1", "3X2", "VOLUMEN") and comprar > 0:
        grupos = int(cantidad // comprar)
        resto = cantidad - (grupos * comprar)
        unidades_pagar = grupos * pagar + resto
        subtotal = round(unidades_pagar * precio, 2)
    elif promo == "PORCENTAJE" and 0 < valor < 100:
        precio_efectivo = precio * (1 - valor / 100)
        subtotal = round(precio_efectivo * cantidad, 2)
    elif promo == "DESCUENTO_MONTO" and descuento_monto is not None and descuento_monto > 0:
        precio_efectivo = max(0, precio - float(descuento_monto))
        subtotal = round(precio_efectivo * cantidad, 2)
    elif promo == "PRECIO_FIJO" and valor > 0:
        subtotal = round(valor * cantidad, 2)
    elif promo == "DESCUENTO_CANTIDAD":
        cmin = float(valor_comprar) if valor_comprar else 0
        if cmin > 0 and cantidad >= cmin and 0 < valor < 100:
            precio_efectivo = precio * (1 - valor / 100)
            subtotal = round(precio_efectivo * cantidad, 2)
        else:
            subtotal = round(precio * cantidad, 2)
    else:
        if promo == "2X1":
            unidades_pagar = math.ceil(cantidad / 2)
            subtotal = round(unidades_pagar * precio, 2)
        else:
            subtotal = round(precio * cantidad, 2)
    precio_efectivo = subtotal / cantidad if cantidad else precio
    return subtotal, round(precio_efectivo, 4)


def _parse_item_carrito(p) -> dict:
    if isinstance(p, dict):
        pid = p.get("producto_id", p.get("id"))
        if pid is None:
            raise ValueError("Ítem sin producto_id")
        modo = str(p.get("modo") or "CANTIDAD").strip().upper()
        uv = str(p.get("unidad_venta") or "UNIDAD").strip().upper()
        c_ui = p.get("cantidad_ui")
        if c_ui is None and modo != "MONTO":
            c_ui = p.get("cantidad", 1)
        ms = p.get("monto_solicitado")
        pres_id = p.get("presentacion_id")
        fac_um = p.get("factor_umb")
        if fac_um is None and p.get("presentacion_factor") is not None:
            fac_um = p.get("presentacion_factor")
        try:
            pres_id_i = int(pres_id) if pres_id is not None and str(pres_id).strip() not in ("", "0", "None") else None
        except (TypeError, ValueError):
            pres_id_i = None
        if pres_id_i is not None and pres_id_i <= 0:
            pres_id_i = None
        return {
            "producto_id": int(pid),
            "modo": modo if modo in ("CANTIDAD", "MONTO") else "CANTIDAD",
            "unidad_venta": uv if uv in ("UNIDAD", "DOCENA", "CAJA") else "UNIDAD",
            "cantidad_ui": float(c_ui) if c_ui is not None else 1.0,
            "monto_solicitado": float(ms) if ms is not None else None,
            "presentacion_id": pres_id_i,
            "factor_umb": float(fac_um) if fac_um is not None else None,
        }
    if isinstance(p, (list, tuple)) and len(p) >= 4:
        extra = p[4] if len(p) > 4 and isinstance(p[4], dict) else {}
        d = {
            "producto_id": int(p[0]),
            "modo": "CANTIDAD",
            "unidad_venta": "UNIDAD",
            "cantidad_ui": float(p[3]),
            "monto_solicitado": None,
            "presentacion_id": None,
            "factor_umb": None,
        }
        if extra.get("unidad_venta"):
            d["unidad_venta"] = str(extra["unidad_venta"]).strip().upper()
        if extra.get("modo"):
            d["modo"] = str(extra["modo"]).strip().upper()
        if extra.get("monto_solicitado") is not None:
            d["monto_solicitado"] = float(extra["monto_solicitado"])
        if extra.get("presentacion_id") is not None:
            try:
                d["presentacion_id"] = int(extra["presentacion_id"])
            except (TypeError, ValueError):
                d["presentacion_id"] = None
        else:
            d["presentacion_id"] = None
        if extra.get("factor_umb") is not None:
            d["factor_umb"] = float(extra["factor_umb"])
        else:
            d["factor_umb"] = None
        if d["modo"] not in ("CANTIDAD", "MONTO"):
            d["modo"] = "CANTIDAD"
        if d["unidad_venta"] not in ("UNIDAD", "DOCENA", "CAJA"):
            d["unidad_venta"] = "UNIDAD"
        return d
    raise ValueError("Formato de carrito inválido")


def _resolver_cantidad_presentacion(
    cur,
    item: dict,
    producto_id: int,
    unidad_venta: str,
    upc: int | None,
    upd: int,
) -> tuple[float, str | None, int | None]:
    """
    Convierte cantidad en presentación a UMB (stock/Kardex).
    Retorna (cantidad_base, nombre para ticket, presentacion_id si aplica).
    """
    c_ui = float(item["cantidad_ui"])
    if not presentaciones_repo.tabla_existe(cur):
        return (
            cantidad_base_desde_ui(c_ui, unidad_venta, upc, upd),
            None,
            None,
        )
    filas = presentaciones_repo.listar_por_producto(cur, producto_id)
    if not filas:
        return (
            cantidad_base_desde_ui(c_ui, unidad_venta, upc, upd),
            None,
            None,
        )

    pres_id = item.get("presentacion_id")
    if pres_id is not None and pres_id > 0:
        fp = presentaciones_repo.fila_por_id(cur, int(pres_id), producto_id)
        if not fp:
            raise ValueError("Presentación inválida")
        fac, nombre = fp
        return cantidad_base_desde_factor(c_ui, float(fac)), nombre, int(pres_id)

    fac_raw = item.get("factor_umb")
    if fac_raw is not None:
        try:
            fac_dec = Decimal(str(fac_raw))
        except Exception:
            raise ValueError("Factor de presentación inválido")
        bp = presentaciones_repo.buscar_por_factor(cur, producto_id, fac_dec)
        if not bp:
            raise ValueError("El factor no coincide con las presentaciones del producto")
        pid, nombre = bp
        return cantidad_base_desde_factor(c_ui, float(fac_dec)), nombre, pid

    uv = (unidad_venta or "UNIDAD").strip().upper()
    if uv == "UNIDAD":
        for r in filas:
            if len(r) > 3 and r[3]:
                return cantidad_base_desde_factor(c_ui, float(r[2])), str(r[1] or "").strip(), int(r[0])
        bp = presentaciones_repo.buscar_por_factor(cur, producto_id, Decimal("1"))
        if bp:
            pid, nombre = bp
            return cantidad_base_desde_factor(c_ui, 1.0), nombre, pid
    tf: Decimal | None = None
    if uv == "DOCENA":
        tf = Decimal(max(1, int(upd or 12)))
    elif uv == "CAJA":
        if not upc or int(upc) <= 0:
            raise ValueError("Este producto no tiene definidas unidades por caja en Inventario.")
        tf = Decimal(int(upc))
    else:
        tf = Decimal("1")
    bp = presentaciones_repo.buscar_por_factor(cur, producto_id, tf) if tf is not None else None
    if bp:
        pid, nombre = bp
        return cantidad_base_desde_factor(c_ui, float(tf)), nombre, pid
    cant = cantidad_base_desde_ui(c_ui, unidad_venta, upc, upd)
    return cant, None, None


def crear_venta_desde_carrito(
    cur, carrito, empresa_id: int = 1, fecha_venta: date | None = None
) -> tuple[float, list[LineaVenta]]:
    """
    Carrito: listas [id, nombre, precio, cantidad_ui, {opciones}] o dicts con producto_id, modo, unidad_venta, etc.

    Por cada tipo de medida, `LineaVenta.cantidad` queda siempre en UMB; `persistir_venta` descuenta
    ese mismo valor de `productos` / `producto_stock_sucursal` y registra Kardex `SALIDA_VENTA`.
    """
    total = 0.0
    lineas: list[LineaVenta] = []
    fecha = fecha_venta or date.today()

    for p in carrito:
        item = _parse_item_carrito(p)
        producto_id = item["producto_id"]
        modo = item["modo"]
        unidad_venta = item["unidad_venta"]

        prod = productos_repo.get_precio_y_stock_for_update(cur, producto_id)
        if not prod:
            raise ValueError(f"Producto no existe: {producto_id}")
        precio_unitario = float(prod[0])
        stock_actual = float(prod[1] if prod[1] is not None else 0)
        promo_tipo = (prod[2] or "").strip() if len(prod) > 2 else None
        promo_val = float(prod[3]) if len(prod) > 3 and prod[3] else 0
        fraccionable = bool(prod[4]) if len(prod) > 4 else False
        upc = int(prod[5]) if len(prod) > 5 and prod[5] is not None else None
        upd = int(prod[6]) if len(prod) > 6 and prod[6] is not None else 12
        mh_cod = normalizar_codigo_mh(str(prod[7]) if len(prod) > 7 else None)
        promo_comprar, promo_pagar, promo_desc_monto = 2, 1, None
        promo_regalo_id, promo_min_compra, promo_cant_regalo = None, 1, 1

        texto_cant: str | None = None
        pres_lin: int | None = None
        if modo == "MONTO":
            if not fraccionable:
                raise ValueError(f"El producto {producto_id} no admite venta por monto (active Fraccionable en Inventario).")
            ms = item["monto_solicitado"]
            if ms is None or ms <= 0:
                raise ValueError("Indique el monto a cobrar (venta por monto).")
            cantidad = cantidad_base_venta_por_monto(ms, precio_unitario)
            texto_cant = texto_presentacion_cantidad(
                0, "UNIDAD", venta_por_monto=True, monto=ms, cantidad_base=cantidad, etiqueta_unidad_mh=mh_cod
            )
        else:
            c_ui = float(item["cantidad_ui"])
            if c_ui <= 0:
                raise ValueError("Cantidad inválida")
            cantidad, nombre_pres, pres_lin = _resolver_cantidad_presentacion(
                cur, item, producto_id, unidad_venta, upc, upd
            )
            texto_cant = texto_presentacion_cantidad(
                c_ui,
                unidad_venta,
                etiqueta_unidad_mh=mh_cod,
                nombre_presentacion=nombre_pres,
            )
            if not fraccionable and abs(cantidad - round(cantidad)) > 1e-6:
                raise ValueError(f"El producto {producto_id} solo admite cantidades enteras en unidad base (UMB).")

        if stock_actual < cantidad:
            raise ValueError(
                f"Stock insuficiente (producto interno #{producto_id}): "
                f"en inventario hay {stock_actual:.4f} unidad base; esta venta requiere {cantidad:.4f}. "
                f"Si cobraba un monto en $ (ej. $5 de queso), active «Venta por monto ($)». "
                f"Si usó cantidad, recuerde que es en libras/unidad base, no en dólares."
            )

        try:
            promo_activa = promociones_repo.get_promocion_activa_producto(cur, producto_id, empresa_id, fecha)
            if promo_activa:
                promo_tipo = promo_activa[0]
                promo_val = float(promo_activa[1] or 0)
                if len(promo_activa) > 2:
                    promo_comprar = float(promo_activa[2] or 2)
                    promo_pagar = float(promo_activa[3] or 1)
                    promo_desc_monto = float(promo_activa[4]) if promo_activa[4] is not None else None
                    promo_regalo_id = int(promo_activa[5]) if promo_activa[5] else None
                    promo_min_compra = float(promo_activa[6] or 1)
                    promo_cant_regalo = float(promo_activa[7] or 1)
                    if promo_tipo == "DESCUENTO_CANTIDAD":
                        promo_comprar = promo_min_compra
        except Exception:
            pass

        if promo_tipo == "REGALO" and promo_regalo_id and cantidad >= promo_min_compra:
            grupos_regalo = int(cantidad // promo_min_compra)
            cant_regalo = grupos_regalo * promo_cant_regalo
            prod_regalo = productos_repo.get_precio_y_stock_for_update(cur, promo_regalo_id)
            if prod_regalo and float(prod_regalo[1] or 0) >= cant_regalo:
                lineas.append(LineaVenta(promo_regalo_id, cant_regalo, 0.0, 0.0, None, None))

        if modo == "MONTO":
            ms = float(item["monto_solicitado"] or 0)
            subtotal = round(ms, 2)
            # Ajuste por redondeo DTE: el total cobrado es exactamente el monto; el precio unitario deriva de subtotal/cantidad UMB.
            precio_efectivo = round(subtotal / cantidad, 8) if cantidad else precio_unitario
            total += subtotal
            lineas.append(LineaVenta(producto_id, cantidad, precio_efectivo, subtotal, texto_cant, None))
            continue

        calc_tipo = None if promo_tipo == "REGALO" else promo_tipo
        subtotal, precio_efectivo = _calcular_subtotal_con_promo(
            precio_unitario, cantidad, calc_tipo, promo_val,
            valor_comprar=promo_comprar, valor_pagar=promo_pagar, descuento_monto=promo_desc_monto,
        )
        total += subtotal
        lineas.append(
            LineaVenta(producto_id, cantidad, precio_efectivo, subtotal, texto_cant, pres_lin)
        )

    return total, lineas


def calcular_retencion_iva(
    cur,
    total_con_iva: float,
    tipo_comprobante: str,
    cliente_id: int | None,
    empresa_id: int,
) -> float:
    """
    Retención IVA 1%: aplica si cliente es Gran Contribuyente y empresa no (o viceversa),
    y la venta gravada (sin IVA) es mayor a $100. Solo para Factura o Crédito Fiscal.
    """
    tc = (tipo_comprobante or "").strip().upper()
    if tc not in ("FACTURA", "CREDITO_FISCAL") or not cliente_id or total_con_iva <= 0:
        return 0.0
    venta_gravada = total_con_iva / 1.13
    if venta_gravada <= 100.0:
        return 0.0
    iva = total_con_iva - venta_gravada
    cl = clientes_repo.get_cliente(cur, cliente_id)
    emp_gran = empresas_repo.get_empresa_es_gran_contribuyente(cur, empresa_id)
    cl_gran = bool(cl[8]) if cl and len(cl) > 8 else False
    if cl_gran == emp_gran:
        return 0.0
    return round(iva * 0.01, 2)


def aplicar_descuento(total_bruto: float, descuento_pct: float | None, descuento_monto: float | None) -> tuple[float, float]:
    """
    Retorna (descuento_aplicado, total_neto).
    - descuento_pct: 0..100
    - descuento_monto: >=0
    Si vienen ambos, se prioriza monto.
    """
    tb = float(total_bruto or 0)
    if tb <= 0:
        return 0.0, 0.0

    monto = None
    pct = None
    try:
        if descuento_monto is not None:
            monto = float(descuento_monto)
    except Exception:
        monto = None
    try:
        if descuento_pct is not None:
            pct = float(descuento_pct)
    except Exception:
        pct = None

    descuento = 0.0
    if monto is not None and monto > 0:
        descuento = monto
    elif pct is not None and pct > 0:
        if pct > 100:
            pct = 100.0
        descuento = tb * (pct / 100.0)

    if descuento < 0:
        descuento = 0.0
    if descuento > tb:
        descuento = tb

    return round(descuento, 2), round(tb - descuento, 2)


def persistir_venta(
    cur,
    usuario_id: int,
    cliente_nombre: str,
    tipo_pago: str,
    total: float,
    lineas: list[LineaVenta],
    empresa_id: int = 1,
    sucursal_id: int = None,
    tipo_comprobante: str = "TICKET",
    cliente_id: int | None = None,
    descuento: float = 0.0,
    total_bruto: float | None = None,
    emitir_contingencia: bool = False,
    causa_contingencia: int | None = None,
) -> int:
    retencion_iva = calcular_retencion_iva(cur, total, tipo_comprobante, cliente_id, empresa_id)
    tc = (tipo_comprobante or "TICKET").strip().upper()
    estado_inicial = "CONTINGENCIA" if (emitir_contingencia and tc in ("FACTURA", "CREDITO_FISCAL")) else "RESPALDO"

    venta_id = ventas_repo.crear_venta(
        cur,
        total,
        usuario_id,
        cliente_nombre,
        tipo_pago,
        empresa_id,
        sucursal_id,
        tipo_comprobante=tipo_comprobante,
        cliente_id=cliente_id,
        retencion_iva=retencion_iva,
        descuento=descuento,
        total_bruto=total_bruto if total_bruto is not None else total,
        estado_dte=estado_inicial,
    )
    # codigo_generacion, numero_control y sello: solo los asigna AgilDTE (sync tras POST /api/pos/procesar-venta/).
    if tc in ("FACTURA", "CREDITO_FISCAL") and emitir_contingencia and causa_contingencia is not None:
        ventas_repo.actualizar_causa_contingencia(cur, venta_id, causa_contingencia, empresa_id=empresa_id)
    suc = int(sucursal_id) if sucursal_id is not None and str(sucursal_id).strip().isdigit() else None
    for ln in lineas:
        ventas_repo.crear_detalle(
            cur,
            venta_id,
            ln.producto_id,
            ln.cantidad,
            ln.precio_unitario,
            ln.subtotal,
            texto_cantidad=ln.texto_cantidad,
            presentacion_id=ln.presentacion_id,
        )
        productos_repo.descontar_stock(cur, ln.producto_id, ln.cantidad, suc)
        try:
            from azdigital.repositories import kardex_repo

            if kardex_repo.tabla_existe(cur, kardex_repo.TABLA_KARDEX):
                # SAVEPOINT: un fallo en kardex no debe abortar toda la transacción (dejaría la venta
                # sin commit o commit inválido; antes el except: pass ocultaba el estado abortado).
                sp_k = "spkx" + uuid.uuid4().hex[:12]
                cur.execute(f"SAVEPOINT {sp_k}")
                try:
                    kardex_repo.insertar_kardex(
                        cur,
                        empresa_id,
                        ln.producto_id,
                        "SALIDA_VENTA",
                        ln.cantidad,
                        suc,
                        None,
                        usuario_id,
                        f"Cant. en UMB (inventario): {ln.cantidad:g}",
                        referencia=f"Venta #{venta_id}",
                    )
                    cur.execute(f"RELEASE SAVEPOINT {sp_k}")
                except Exception:
                    cur.execute(f"ROLLBACK TO SAVEPOINT {sp_k}")
        except Exception:
            pass
    return venta_id

