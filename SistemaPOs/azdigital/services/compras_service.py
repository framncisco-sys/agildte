# Programador: Oscar Amaya Romero
"""Servicio de compras: retención IVA MH y conversión presentación → UMB en ingreso de inventario."""

from __future__ import annotations

from typing import Any

from azdigital.repositories import presentaciones_repo


def linea_compra_a_unidad_base(
    cantidad_recibida: float,
    costo_por_unidad_presentacion: float,
    factor_presentacion: float,
) -> tuple[float, float, float]:
    """
    Convierte lo que dice la factura del proveedor a cantidad y costo en UMB.

    Ej.: 60 cajas × factor 50 → 3000 UMB; costo $5/caja → $0.10/UMB.
    Retorna (cantidad_umb, costo_unitario_umb, subtotal_factura).
    """
    fac = float(factor_presentacion)
    if fac <= 0:
        fac = 1.0
    q = float(cantidad_recibida)
    c = float(costo_por_unidad_presentacion)
    cant_umb = q * fac
    costo_umb = c / fac
    subtotal = q * c
    return (cant_umb, costo_umb, subtotal)


def opciones_presentacion_compra(cur, producto_id: int, prod_row: tuple | None = None) -> list[dict[str, Any]]:
    """
    Opciones para el select «Presentación» al registrar compra (nombre + factor respecto a UMB).
    Incluye filas de producto_presentación y, si aplica, Caja/Docena desde columnas legacy del producto.
    """
    opts: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()
    rows = presentaciones_repo.listar_por_producto(cur, producto_id) if presentaciones_repo.tabla_existe(cur) else []
    for r in rows:
        try:
            fac = float(r[2])
        except (TypeError, ValueError):
            continue
        if fac <= 0:
            continue
        nom = (str(r[1]).strip() if r[1] else "") or "Presentación"
        key = (nom.upper(), round(fac, 6))
        if key in seen:
            continue
        seen.add(key)
        opts.append({"nombre": nom, "factor": fac})

    uxc = None
    uxd = None
    if prod_row and len(prod_row) > 13:
        try:
            if prod_row[13] is not None:
                uxc = int(prod_row[13])
        except (TypeError, ValueError):
            uxc = None
        try:
            if len(prod_row) > 14 and prod_row[14] is not None:
                uxd = int(prod_row[14])
        except (TypeError, ValueError):
            uxd = None

    def _add_synthetic(nombre: str, fac: int) -> None:
        if fac <= 0:
            return
        ff = float(fac)
        key = (nombre.upper(), round(ff, 6))
        if key in seen:
            return
        if any(round(o["factor"], 6) == round(ff, 6) for o in opts):
            return
        seen.add(key)
        opts.append({"nombre": nombre, "factor": ff})

    _add_synthetic("Caja", uxc or 0)
    _add_synthetic("Docena", uxd or 0)

    if not opts:
        umb = presentaciones_repo.nombre_umb_producto(cur, producto_id)
        opts.append({"nombre": umb or "Unidad base", "factor": 1.0})

    opts.sort(key=lambda o: (0 if abs(float(o["factor"]) - 1.0) < 1e-9 else 1, float(o["factor"])))
    return opts


def calcular_retencion_iva_compras(
    empresa_es_gran_contribuyente: bool,
    proveedor_es_gran_contribuyente: bool,
    total_con_iva: float,
) -> float:
    """
    Retención IVA 1% en compras (normativa MH El Salvador).

    Aplica cuando uno es Gran Contribuyente y el otro no, y la base gravada > $100.

    - Si proveedor es Grande y empresa NO: el proveedor retiene → registramos el monto (retención sufrida).
    - Si empresa es Grande y proveedor NO: la empresa retiene → registramos el monto (retención practicada).

    En ambos casos el monto es 1% del IVA de la compra.
    Retorna el monto a registrar (siempre >= 0).
    """
    if total_con_iva <= 0:
        return 0.0
    compra_gravada = total_con_iva / 1.13
    if compra_gravada <= 100.0:
        return 0.0
    iva = total_con_iva - compra_gravada
    if empresa_es_gran_contribuyente == proveedor_es_gran_contribuyente:
        return 0.0
    return round(iva * 0.01, 2)


def cantidades_umb_por_producto_desde_detalles(detalles: list[tuple]) -> dict[int, float]:
    """Suma cantidades UMB (detalle[3]) por producto_id (detalle[0])."""
    out: dict[int, float] = {}
    for d in detalles or []:
        try:
            pid = int(d[0])
            cant = float(d[3] or 0)
        except (TypeError, ValueError, IndexError):
            continue
        if pid > 0 and cant > 0:
            out[pid] = out.get(pid, 0.0) + cant
    return out


def _sucursal_stock_compra(cur, producto_id: int, empresa_id: int) -> int | None:
    from azdigital.repositories import kardex_repo

    cur.execute("SELECT sucursal_id FROM productos WHERE id = %s", (producto_id,))
    rp = cur.fetchone()
    if rp and rp[0]:
        return int(rp[0])
    return kardex_repo.primera_sucursal_empresa(cur, empresa_id)


def movimiento_stock_delta_compra(
    cur,
    producto_id: int,
    delta_umb: float,
    compra_id: int,
    empresa_id: int,
    usuario_id: int | None,
    *,
    motivo: str = "",
) -> None:
    """
    Ajusta inventario por la diferencia entre cantidad anterior y nueva (UMB).
    delta > 0: entrada; delta < 0: salida. delta == 0: sin movimiento.
    """
    from azdigital.repositories import kardex_repo, productos_repo

    if abs(float(delta_umb)) < 1e-9:
        return
    delta = float(delta_umb)
    notas_k = f"Compra #{compra_id}"
    if motivo:
        notas_k += f": {motivo[:500]}"
    suc_id = _sucursal_stock_compra(cur, producto_id, empresa_id)
    usa_kardex = bool(suc_id) and kardex_repo.tabla_existe(cur, kardex_repo.TABLA_STOCK)
    if delta > 0:
        if usa_kardex:
            kardex_repo.registrar_entrada(cur, producto_id, suc_id, delta, usuario_id, notas_k)
        else:
            productos_repo.incrementar_stock(cur, producto_id, delta)
        return
    qty = abs(delta)
    notas_sal = notas_k + " (ajuste − cantidad)"
    if usa_kardex:
        try:
            kardex_repo.registrar_salida(cur, producto_id, suc_id, qty, usuario_id, notas_sal)
        except ValueError as e:
            raise ValueError(
                f"Stock insuficiente para descontar {qty:g} UMB del producto #{producto_id}. {e}"
            ) from e
    else:
        productos_repo.incrementar_stock(cur, producto_id, -qty)


def aplicar_delta_stock_edicion_compra(
    cur,
    compra_id: int,
    empresa_id: int,
    usuario_id: int | None,
    cantidades_anteriores: dict[int, float],
    cantidades_nuevas: dict[int, float],
    *,
    motivo: str = "Edición de factura",
) -> None:
    """Solo mueve inventario por diferencias entre el detalle guardado y el nuevo."""
    todos = set(cantidades_anteriores) | set(cantidades_nuevas)
    for pid in todos:
        antes = float(cantidades_anteriores.get(pid, 0.0))
        despues = float(cantidades_nuevas.get(pid, 0.0))
        delta = despues - antes
        movimiento_stock_delta_compra(
            cur, pid, delta, compra_id, empresa_id, usuario_id, motivo=motivo
        )


def revertir_stock_detalle_compra(
    cur,
    detalle: tuple,
    compra_id: int,
    empresa_id: int,
    usuario_id: int | None,
    *,
    motivo: str = "",
) -> None:
    """
    Revierte el stock de una línea (eliminar factura).
    Preferir ``aplicar_delta_stock_edicion_compra`` con cantidades_nuevas vacías al editar.
    """
    try:
        pid = int(detalle[0])
        cant_umb = float(detalle[3])
    except (TypeError, ValueError, IndexError):
        return
    if pid <= 0 or cant_umb <= 0:
        return
    movimiento_stock_delta_compra(
        cur,
        pid,
        -cant_umb,
        compra_id,
        empresa_id,
        usuario_id,
        motivo=motivo or "Reversión compra",
    )
