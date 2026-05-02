# Programador: Oscar Amaya Romero
"""Repositorio para Corte de Caja y CierreCaja bajo DTE."""

from __future__ import annotations


TIPOS_DTE = ("FACTURA", "CREDITO_FISCAL", "NOTA_CREDITO", "SUJETO_EXCLUIDO", "TICKET")
METODOS_PAGO = ("EFECTIVO", "TARJETA", "TRANSFERENCIA", "BITCOIN", "CREDITO", "OTRO")


def _inicializar_ventas_por_tipo() -> dict:
    return {t: {"cantidad": 0, "total": 0.0} for t in TIPOS_DTE}


def _inicializar_ventas_por_pago() -> dict:
    return {m: 0.0 for m in METODOS_PAGO}


def listar_cierres_cerrados(cur, empresa_id: int, usuario_id: int | None = None, limite: int = 10) -> list:
    """Lista los últimos cierres CERRADOS para ver comprobantes."""
    params = [empresa_id]
    where = "empresa_id = %s AND estado = 'CERRADO'"
    if usuario_id is not None:
        where += " AND usuario_id = %s"
        params.append(usuario_id)
    params.append(limite)
    cur.execute(
        f"""
        SELECT id, usuario_id, fecha_apertura, fecha_cierre, monto_real, diferencia
        FROM cierre_caja
        WHERE {where}
        ORDER BY fecha_cierre DESC
        LIMIT %s
        """,
        params,
    )
    return cur.fetchall() or []


def apertura_abierta(cur, usuario_id: int, empresa_id: int, sucursal_id: int | None = None) -> tuple | None:
    """Retorna el cierre_caja ABIERTO del usuario en la empresa/sucursal, o None."""
    params = [usuario_id, empresa_id]
    where = "usuario_id = %s AND empresa_id = %s AND estado = 'ABIERTO'"
    if sucursal_id is not None:
        where += " AND (sucursal_id IS NULL OR sucursal_id = %s)"
        params.append(sucursal_id)
    cur.execute(
        f"""
        SELECT id, monto_apertura, fecha_apertura
        FROM cierre_caja
        WHERE {where}
        ORDER BY fecha_apertura DESC
        LIMIT 1
        """,
        params,
    )
    return cur.fetchone()


def crear_apertura(
    cur,
    usuario_id: int,
    empresa_id: int,
    monto_apertura: float,
    sucursal_id: int | None = None,
) -> int:
    """Abre turno de caja. Retorna id."""
    cur.execute(
        """
        INSERT INTO cierre_caja (empresa_id, sucursal_id, usuario_id, monto_apertura, estado)
        VALUES (%s, %s, %s, %s, 'ABIERTO')
        RETURNING id
        """,
        (empresa_id, sucursal_id, usuario_id, float(monto_apertura)),
    )
    return int(cur.fetchone()[0])


def obtener_datos_corte(
    cur,
    empresa_id: int,
    fecha_str: str,
    usuario_id: int | None = None,
    sucursal_id: int | None = None,
) -> dict:
    """
    Datos para Corte de Caja: ventas por tipo DTE, por método pago, impuestos.
    fecha_str: YYYY-MM-DD
    """
    params = [empresa_id, fecha_str]
    where = [
        "(v.empresa_id IS NULL OR v.empresa_id = %s)",
        "v.fecha_registro::date = %s",
        "COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'",
    ]
    if usuario_id is not None:
        where.append("v.usuario_id = %s")
        params.append(usuario_id)
    if sucursal_id is not None:
        where.append("(v.sucursal_id IS NULL OR v.sucursal_id = %s)")
        params.append(sucursal_id)
    w = " AND ".join(where)

    cur.execute(
        f"""
        SELECT
            COALESCE(v.tipo_comprobante, 'TICKET'),
            COALESCE(v.tipo_pago, 'EFECTIVO'),
            v.total_pagar,
            COALESCE(v.retencion_iva, 0)
        FROM ventas v
        WHERE {w}
        ORDER BY v.fecha_registro
        """,
        params,
    )
    rows = cur.fetchall() or []

    ventas_por_tipo = _inicializar_ventas_por_tipo()
    ventas_por_pago = _inicializar_ventas_por_pago()
    total_ventas = 0.0
    total_iva = 0.0
    total_retencion = 0.0

    for tc, tp, total, ret in rows:
        t = float(total or 0)
        r = float(ret or 0)
        total_ventas += t
        total_retencion += r
        total_iva += t - (t / 1.13) if t else 0
        tc_u = (tc or "TICKET").strip().upper().replace(" ", "_")
        tp_u = (tp or "EFECTIVO").strip().upper()
        tipo_key = tc_u if tc_u in ventas_por_tipo else "TICKET"
        ventas_por_tipo[tipo_key]["cantidad"] += 1
        ventas_por_tipo[tipo_key]["total"] += t
        if tp_u in ventas_por_pago:
            ventas_por_pago[tp_u] += t
        elif tp_u == "BITCOIN":
            ventas_por_pago["BITCOIN"] += t
        elif tp_u == "TRANSFERENCIA":
            ventas_por_pago["TRANSFERENCIA"] += t
        else:
            ventas_por_pago["OTRO"] += t

    # Compatibilidad: formato plano para reporte_corte_caja existente
    ventas_por_tipo_flat = {k: v["total"] for k, v in ventas_por_tipo.items()}
    ventas_por_pago["TRANSFERENCIA"] = ventas_por_pago.get("TRANSFERENCIA", 0)

    return {
        "ventas_por_tipo_dte": ventas_por_tipo_flat,
        "ventas_por_tipo_dte_detalle": ventas_por_tipo,
        "ventas_por_pago": ventas_por_pago,
        "total_ventas": total_ventas,
        "total_iva": round(total_iva, 2),
        "total_retencion": round(total_retencion, 2),
        "cantidad_ventas": len(rows),
    }


def get_cierre_con_cabecera(cur, cierre_id: int) -> dict | None:
    """
    Retorna el cierre_caja con datos de empresa, sucursal y usuario para el comprobante.
    Solo cierres CERRADOS tienen arqueo completo.
    """
    cur.execute(
        """
        SELECT c.id, c.empresa_id, c.sucursal_id, c.usuario_id,
               c.fecha_apertura, c.fecha_cierre, c.monto_apertura,
               c.ventas_efectivo, c.ventas_tarjeta, c.ventas_credito, c.ventas_otro,
               c.salidas_efectivo, c.monto_esperado, c.monto_real, c.diferencia, c.estado
        FROM cierre_caja c
        WHERE c.id = %s
        """,
        (cierre_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    emp_id = row[1]
    suc_id = row[2]
    user_id = row[3]
    emp_nombre = ""
    suc_nombre = ""
    cajero_nombre = ""
    cur.execute("SELECT nombre FROM empresas WHERE id = %s", (emp_id,))
    r = cur.fetchone()
    if r:
        emp_nombre = r[0] or ""
    if suc_id:
        cur.execute("SELECT nombre FROM sucursales WHERE id = %s", (suc_id,))
        r = cur.fetchone()
        if r:
            suc_nombre = r[0] or ""
    cur.execute("SELECT username FROM usuarios WHERE id = %s", (user_id,))
    r = cur.fetchone()
    if r:
        cajero_nombre = r[0] or ""
    return {
        "id": row[0],
        "empresa_id": emp_id,
        "sucursal_id": suc_id,
        "usuario_id": user_id,
        "fecha_apertura": row[4],
        "fecha_cierre": row[5],
        "monto_apertura": float(row[6] or 0),
        "ventas_efectivo": float(row[7] or 0),
        "ventas_tarjeta": float(row[8] or 0),
        "ventas_credito": float(row[9] or 0),
        "ventas_otro": float(row[10] or 0),
        "salidas_efectivo": float(row[11] or 0),
        "monto_esperado": float(row[12] or 0),
        "monto_real": float(row[13] or 0),
        "diferencia": float(row[14] or 0),
        "estado": row[15] or "CERRADO",
        "empresa_nombre": emp_nombre,
        "sucursal_nombre": suc_nombre,
        "cajero_nombre": cajero_nombre,
    }


def obtener_datos_corte_por_cierre(cur, cierre_id: int) -> dict:
    """
    Datos de ventas para un turno cerrado específico.
    Usa fecha_apertura y fecha_cierre del cierre.
    """
    cur.execute(
        """
        SELECT fecha_apertura, fecha_cierre, usuario_id, empresa_id, sucursal_id
        FROM cierre_caja WHERE id = %s
        """,
        (cierre_id,),
    )
    r = cur.fetchone()
    if not r:
        return _datos_corte_vacios()
    fa, fc, uid, eid, sid = r
    if not fa or not fc:
        return _datos_corte_vacios()
    params = [eid, fa, fc, uid]
    where = [
        "(v.empresa_id IS NULL OR v.empresa_id = %s)",
        "v.fecha_registro >= %s",
        "v.fecha_registro <= %s",
        "v.usuario_id = %s",
        "COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'",
    ]
    if sid:
        where.append("(v.sucursal_id IS NULL OR v.sucursal_id = %s)")
        params.append(sid)
    w = " AND ".join(where)
    cur.execute(
        f"""
        SELECT COALESCE(v.tipo_comprobante, 'TICKET'), COALESCE(v.tipo_pago, 'EFECTIVO'),
               v.total_pagar, COALESCE(v.retencion_iva, 0)
        FROM ventas v
        WHERE {w}
        ORDER BY v.fecha_registro
        """,
        params,
    )
    rows = cur.fetchall() or []
    return _procesar_filas_corte(rows)


def _datos_corte_vacios() -> dict:
    ventas_por_tipo = _inicializar_ventas_por_tipo()
    ventas_por_tipo_flat = {k: v["total"] for k, v in ventas_por_tipo.items()}
    return {
        "ventas_por_tipo_dte": ventas_por_tipo_flat,
        "ventas_por_tipo_dte_detalle": ventas_por_tipo,
        "ventas_por_pago": _inicializar_ventas_por_pago(),
        "total_ventas": 0.0,
        "total_iva": 0.0,
        "total_retencion": 0.0,
        "cantidad_ventas": 0,
    }


def _procesar_filas_corte(rows: list) -> dict:
    ventas_por_tipo = _inicializar_ventas_por_tipo()
    ventas_por_pago = _inicializar_ventas_por_pago()
    total_ventas = 0.0
    total_iva = 0.0
    total_retencion = 0.0
    for tc, tp, total, ret in rows:
        t = float(total or 0)
        r = float(ret or 0)
        total_ventas += t
        total_retencion += r
        total_iva += t - (t / 1.13) if t else 0
        tc_u = (tc or "TICKET").strip().upper().replace(" ", "_")
        tp_u = (tp or "EFECTIVO").strip().upper()
        tipo_key = tc_u if tc_u in ventas_por_tipo else "TICKET"
        ventas_por_tipo[tipo_key]["cantidad"] += 1
        ventas_por_tipo[tipo_key]["total"] += t
        if tp_u in ventas_por_pago:
            ventas_por_pago[tp_u] += t
        elif tp_u == "BITCOIN":
            ventas_por_pago["BITCOIN"] += t
        elif tp_u == "TRANSFERENCIA":
            ventas_por_pago["TRANSFERENCIA"] += t
        else:
            ventas_por_pago["OTRO"] += t
    ventas_por_tipo_flat = {k: v["total"] for k, v in ventas_por_tipo.items()}
    return {
        "ventas_por_tipo_dte": ventas_por_tipo_flat,
        "ventas_por_tipo_dte_detalle": ventas_por_tipo,
        "ventas_por_pago": ventas_por_pago,
        "total_ventas": total_ventas,
        "total_iva": round(total_iva, 2),
        "total_retencion": round(total_retencion, 2),
        "cantidad_ventas": len(rows),
    }


def cerrar_caja(
    cur,
    cierre_id: int,
    ventas_efectivo: float,
    ventas_tarjeta: float,
    ventas_credito: float,
    ventas_otro: float,
    salidas_efectivo: float,
    monto_real: float,
    empresa_id: int,
) -> bool:
    """
    Cierre a ciegas: calcula monto_esperado y diferencia.
    monto_esperado = apertura + ventas_efectivo - salidas
    """
    cur.execute(
        "SELECT monto_apertura FROM cierre_caja WHERE id = %s AND empresa_id = %s AND estado = 'ABIERTO'",
        (cierre_id, empresa_id),
    )
    row = cur.fetchone()
    if not row:
        return False
    monto_apertura = float(row[0] or 0)
    monto_esperado = monto_apertura + ventas_efectivo - salidas_efectivo
    diferencia = float(monto_real or 0) - monto_esperado
    cur.execute(
        """
        UPDATE cierre_caja SET
            ventas_efectivo = %s, ventas_tarjeta = %s, ventas_credito = %s, ventas_otro = %s,
            salidas_efectivo = %s, monto_esperado = %s, monto_real = %s, diferencia = %s,
            fecha_cierre = CURRENT_TIMESTAMP, estado = 'CERRADO'
        WHERE id = %s AND empresa_id = %s
        """,
        (ventas_efectivo, ventas_tarjeta, ventas_credito, ventas_otro,
         salidas_efectivo, monto_esperado, monto_real, diferencia, cierre_id, empresa_id),
    )
    return cur.rowcount > 0
