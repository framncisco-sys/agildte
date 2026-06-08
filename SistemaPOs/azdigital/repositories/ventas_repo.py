# Programador: Oscar Amaya Romero
from __future__ import annotations

import uuid

from azdigital.utils.fecha_sv import ahora_sv_naive


def get_fecha_registro(cur, venta_id: int):
    """Fecha/hora de registro de la venta (naive = hora local SV en BD)."""
    cur.execute("SELECT fecha_registro FROM ventas WHERE id = %s", (int(venta_id),))
    row = cur.fetchone()
    return row[0] if row else None


def crear_venta(
    cur,
    total_pagar: float,
    usuario_id: int,
    cliente_nombre: str,
    tipo_pago: str,
    empresa_id: int = 1,
    sucursal_id: int = None,
    tipo_comprobante: str = "TICKET",
    cliente_id: int | None = None,
    retencion_iva: float = 0.0,
    descuento: float = 0.0,
    total_bruto: float | None = None,
    codigo_generacion: str | None = None,
    numero_control: str | None = None,
    estado_dte: str = "RESPALDO",
    causa_contingencia: int | None = None,
) -> int:
    tc = (tipo_comprobante or "TICKET").strip().upper()[:32]
    ret_iva = float(retencion_iva or 0)
    desc = float(descuento or 0)
    tb = float(total_bruto) if total_bruto is not None else total_pagar
    cg = (codigo_generacion or "").strip() or None
    nc = (numero_control or "").strip() or None
    ed = (estado_dte or "RESPALDO").strip().upper()[:32] or "RESPALDO"
    ts_sv = ahora_sv_naive()
    try:
        cur.execute(
            """
            INSERT INTO ventas (
                fecha_registro, total_pagar, usuario_id, cliente_nombre, tipo_pago,
                empresa_id, sucursal_id, tipo_comprobante, cliente_id, retencion_iva, estado_cobro,
                descuento, total_bruto, codigo_generacion, numero_control, estado_dte
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                CASE WHEN %s IN ('CREDITO', 'CRÉDITO') THEN 'PENDIENTE' ELSE 'COBRADO' END,
                %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (ts_sv, total_pagar, usuario_id, cliente_nombre, tipo_pago, empresa_id, sucursal_id, tc, cliente_id, ret_iva, tipo_pago, desc, tb, cg, nc, ed),
        )
    except Exception:
        cur.connection.rollback()
        try:
            cur.execute(
                """
                INSERT INTO ventas (
                    fecha_registro, total_pagar, usuario_id, cliente_nombre, tipo_pago,
                    empresa_id, sucursal_id, tipo_comprobante, cliente_id, retencion_iva, estado_cobro,
                    descuento, total_bruto, codigo_generacion, numero_control, estado_dte
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    CASE WHEN %s IN ('CREDITO', 'CRÉDITO') THEN 'PENDIENTE' ELSE 'COBRADO' END,
                    %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (ts_sv, total_pagar, usuario_id, cliente_nombre, tipo_pago, empresa_id, sucursal_id, tc, cliente_id, ret_iva, tipo_pago, desc, tb, cg, nc, ed),
            )
        except Exception:
            cur.connection.rollback()
            try:
                cur.execute(
                    """
                    INSERT INTO ventas (
                        fecha_registro, total_pagar, usuario_id, cliente_nombre, tipo_pago,
                        empresa_id, sucursal_id, tipo_comprobante, cliente_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (ts_sv, total_pagar, usuario_id, cliente_nombre, tipo_pago, empresa_id, sucursal_id, tc, cliente_id),
                )
            except Exception:
                cur.connection.rollback()
                cur.execute(
                    """
                    INSERT INTO ventas (fecha_registro, total_pagar, usuario_id, cliente_nombre, tipo_pago, empresa_id, sucursal_id, tipo_comprobante, cliente_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (ts_sv, total_pagar, usuario_id, cliente_nombre, tipo_pago, empresa_id, sucursal_id, tc, cliente_id),
                )
    return int(cur.fetchone()[0])


def actualizar_numero_caja(
    cur,
    venta_id: int,
    numero_caja: int,
    empresa_id: int | None = None,
) -> None:
    """Número correlativo de caja (ticket/factura) por ambiente."""
    from azdigital.utils.db_savepoint import sql_opcional

    def _upd() -> None:
        if empresa_id is not None:
            cur.execute(
                "UPDATE ventas SET numero_caja = %s WHERE id = %s AND empresa_id = %s",
                (int(numero_caja), int(venta_id), int(empresa_id)),
            )
        else:
            cur.execute(
                "UPDATE ventas SET numero_caja = %s WHERE id = %s",
                (int(numero_caja), int(venta_id)),
            )

    sql_opcional(cur, _upd)


def actualizar_dte_desde_respuesta_agildte(
    cur,
    venta_id: int,
    empresa_id: int | None,
    remota: dict,
) -> bool:
    """
    Persiste en la venta local los campos DTE devueltos por AgilDTE (VentaSerializer)
    tras POST /api/pos/procesar-venta/.
    """
    if not remota or not isinstance(remota, dict):
        return False
    cg = str(remota.get("codigo_generacion") or "").strip()
    nc = str(remota.get("numero_control") or "").strip()
    sello = str(remota.get("sello_recepcion") or "").strip()
    estado = str(remota.get("estado_dte") or "").strip()
    sets: list[str] = []
    vals: list = []
    if cg:
        sets.append("codigo_generacion = %s")
        vals.append(cg)
    if nc:
        sets.append("numero_control = %s")
        vals.append(nc)
    if sello:
        sets.append("sello_recepcion = %s")
        vals.append(sello)
    if estado:
        sets.append("estado_dte = %s")
        vals.append(estado[:40])
    amb = str(remota.get("ambiente_emision") or "").strip()
    if amb in ("00", "01"):
        sets.append("ambiente_emision = %s")
        vals.append(amb)
    if not sets:
        return False
    vals.append(venta_id)
    sql = f"UPDATE ventas SET {', '.join(sets)} WHERE id = %s"
    if empresa_id is not None:
        sql += " AND (empresa_id IS NULL OR empresa_id = %s)"
        vals.append(empresa_id)
    sp = "spag" + uuid.uuid4().hex[:12]
    cur.execute(f"SAVEPOINT {sp}")
    try:
        cur.execute(sql, vals)
        ok = cur.rowcount > 0
        cur.execute(f"RELEASE SAVEPOINT {sp}")
        return ok
    except Exception:
        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        return False


def actualizar_dte_venta(
    cur,
    venta_id: int,
    codigo_generacion: str,
    numero_control: str,
    estado_dte: str = "RESPALDO",
    empresa_id: int | None = None,
) -> bool:
    """Actualiza campos DTE en venta ya creada (para Factura/Crédito Fiscal)."""
    cg = (codigo_generacion or "").strip()
    nc = (numero_control or "").strip()
    ed = (estado_dte or "RESPALDO").strip().upper()[:32] or "RESPALDO"
    if not cg or not nc:
        return False
    sp = "spdte" + uuid.uuid4().hex[:12]
    cur.execute(f"SAVEPOINT {sp}")
    try:
        if empresa_id is not None:
            cur.execute(
                """
                UPDATE ventas SET codigo_generacion = %s, numero_control = %s, estado_dte = %s
                WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)
                """,
                (cg, nc, ed, venta_id, empresa_id),
            )
        else:
            cur.execute(
                """
                UPDATE ventas SET codigo_generacion = %s, numero_control = %s, estado_dte = %s
                WHERE id = %s
                """,
                (cg, nc, ed, venta_id),
            )
        ok = cur.rowcount > 0
        cur.execute(f"RELEASE SAVEPOINT {sp}")
        return ok
    except Exception:
        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        return False


def actualizar_causa_contingencia(
    cur, venta_id: int, causa: int, empresa_id: int | None = None
) -> bool:
    """Registra causa de contingencia (1=MH, 2=Internet, 3=Energía, 4=Sistema)."""
    sp = "spcc" + uuid.uuid4().hex[:12]
    cur.execute(f"SAVEPOINT {sp}")
    try:
        if empresa_id is not None:
            cur.execute(
                "UPDATE ventas SET causa_contingencia = %s WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)",
                (causa, venta_id, empresa_id),
            )
        else:
            cur.execute("UPDATE ventas SET causa_contingencia = %s WHERE id = %s", (causa, venta_id))
        ok = cur.rowcount > 0
        cur.execute(f"RELEASE SAVEPOINT {sp}")
        return ok
    except Exception:
        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        return False


def crear_detalle(
    cur,
    venta_id: int,
    producto_id: int,
    cantidad: float,
    precio_unitario: float,
    subtotal: float,
    texto_cantidad: str | None = None,
    presentacion_id: int | None = None,
) -> None:
    """
    Inserta línea de venta. Prueba columnas opcionales (presentacion_id, texto_cantidad) con SAVEPOINT:
    un fallo no debe hacer rollback de toda la transacción (la fila en `ventas` ya existe).
    """
    tx = (texto_cantidad or "").strip() or None
    sp = "spvd" + uuid.uuid4().hex[:14]
    cur.execute(f"SAVEPOINT {sp}")
    try:
        if presentacion_id is not None:
            try:
                cur.execute(
                    """
                    INSERT INTO venta_detalles (venta_id, producto_id, cantidad, precio_unitario, subtotal, texto_cantidad, presentacion_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (venta_id, producto_id, cantidad, precio_unitario, subtotal, tx, presentacion_id),
                )
                cur.execute(f"RELEASE SAVEPOINT {sp}")
                return
            except Exception:
                cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        try:
            cur.execute(
                """
                INSERT INTO venta_detalles (venta_id, producto_id, cantidad, precio_unitario, subtotal, texto_cantidad)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (venta_id, producto_id, cantidad, precio_unitario, subtotal, tx),
            )
            cur.execute(f"RELEASE SAVEPOINT {sp}")
            return
        except Exception:
            cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        cur.execute(
            """
            INSERT INTO venta_detalles (venta_id, producto_id, cantidad, precio_unitario, subtotal)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (venta_id, producto_id, cantidad, precio_unitario, subtotal),
        )
        cur.execute(f"RELEASE SAVEPOINT {sp}")
    except Exception:
        try:
            cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        except Exception:
            pass
        raise


def get_venta(cur, venta_id: int, empresa_id: int = None):
    """
    Retorna: id, fecha, total, cliente_nombre, tipo_comprobante, cliente_id,
    doc_cliente, tipo_doc_cliente, nombre_cliente_cat, tipo_pago, estado_cobro,
    retencion_iva, descuento, total_bruto,
    codigo_generacion, numero_control, sello_recepcion, estado_dte
    """
    params = (venta_id,) if empresa_id is None else (venta_id, empresa_id)
    sql_base = """
        SELECT v.id, TO_CHAR(v.fecha_registro, 'DD/MM/YYYY HH:MI AM'), v.total_pagar, v.cliente_nombre,
               COALESCE(v.tipo_comprobante, 'TICKET'), v.cliente_id,
               COALESCE(c.numero_documento, ''), COALESCE(c.tipo_documento, ''),
               COALESCE(c.nombre_cliente, v.cliente_nombre),
               COALESCE(v.tipo_pago, 'EFECTIVO'),
               COALESCE(v.estado_cobro, 'COBRADO'),
               COALESCE(v.retencion_iva, 0), COALESCE(v.descuento, 0), COALESCE(v.total_bruto, v.total_pagar),
               COALESCE(v.codigo_generacion, ''), COALESCE(v.numero_control, ''),
               COALESCE(v.sello_recepcion, ''), COALESCE(v.estado_dte, 'RESPALDO')
        FROM ventas v
        LEFT JOIN clientes c ON c.id = v.cliente_id
        WHERE v.id = %s
    """
    try:
        if empresa_id is not None:
            cur.execute(sql_base + " AND (v.empresa_id IS NULL OR v.empresa_id = %s)", params)
        else:
            cur.execute(sql_base, params)
        return cur.fetchone()
    except Exception:
        cur.connection.rollback()
        try:
            sql_fallback = """
                SELECT v.id, TO_CHAR(v.fecha_registro, 'DD/MM/YYYY HH:MI AM'), v.total_pagar, v.cliente_nombre,
                       COALESCE(v.tipo_comprobante, 'TICKET'), v.cliente_id,
                       COALESCE(c.numero_documento, ''), COALESCE(c.tipo_documento, ''),
                       COALESCE(c.nombre_cliente, v.cliente_nombre),
                       COALESCE(v.tipo_pago, 'EFECTIVO'),
                       COALESCE(v.estado_cobro, 'COBRADO'),
                       COALESCE(v.retencion_iva, 0), COALESCE(v.descuento, 0), COALESCE(v.total_bruto, v.total_pagar),
                       NULL, NULL, NULL, 'RESPALDO'
                FROM ventas v
                LEFT JOIN clientes c ON c.id = v.cliente_id
                WHERE v.id = %s
            """
            if empresa_id is not None:
                cur.execute(sql_fallback + " AND (v.empresa_id IS NULL OR v.empresa_id = %s)", params)
            else:
                cur.execute(sql_fallback, params)
            return cur.fetchone()
        except Exception:
            cur.connection.rollback()
            return None


def venta_existe_y_empresa_id(cur, venta_id: int) -> tuple[bool, int | None]:
    """
    Para impresión / permisos: saber si la venta existe y a qué empresa pertenece.
    Retorna (False, None) si no hay fila; (True, None) si empresa_id es NULL; (True, id) si tiene empresa.
    No atrapa errores de SQL: un fallo real de BD no debe devolverse como «no existe».
    """
    cur.execute("SELECT empresa_id FROM ventas WHERE id = %s", (venta_id,))
    r = cur.fetchone()
    if not r:
        return False, None
    e = r[0]
    if e is None:
        return True, None
    return True, int(e)


def get_detalles(cur, venta_id: int):
    try:
        cur.execute(
            """
            SELECT p.nombre, dv.cantidad, dv.precio_unitario, COALESCE(dv.texto_cantidad, '')
            FROM venta_detalles dv
            JOIN productos p ON dv.producto_id = p.id
            WHERE dv.venta_id = %s
            """,
            (venta_id,),
        )
        return cur.fetchall()
    except Exception:
        cur.connection.rollback()
        cur.execute(
            """
            SELECT p.nombre, dv.cantidad, dv.precio_unitario, ''
            FROM venta_detalles dv
            JOIN productos p ON dv.producto_id = p.id
            WHERE dv.venta_id = %s
            """,
            (venta_id,),
        )
        return cur.fetchall()


def _sql_etiqueta_cliente_venta() -> str:
    """Misma lógica que clientes_repo.texto_snapshot_cliente_venta (para filas con JOIN a clientes)."""
    return """
        CASE WHEN c.id IS NULL THEN COALESCE(NULLIF(TRIM(v.cliente_nombre), ''), 'Consumidor Final')
        ELSE CASE
            WHEN NULLIF(TRIM(COALESCE(c.numero_documento, '')), '') IS NOT NULL
                 AND NULLIF(TRIM(COALESCE(c.tipo_documento, '')), '') IS NOT NULL
                THEN TRIM(COALESCE(NULLIF(TRIM(c.nombre_cliente), ''), 'Cliente'))
                     || ' · ' || TRIM(c.tipo_documento) || ': ' || TRIM(c.numero_documento)
            WHEN NULLIF(TRIM(COALESCE(c.numero_documento, '')), '') IS NOT NULL
                THEN TRIM(COALESCE(NULLIF(TRIM(c.nombre_cliente), ''), 'Cliente'))
                     || ' · Doc. ' || TRIM(c.numero_documento)
            ELSE TRIM(COALESCE(NULLIF(TRIM(c.nombre_cliente), ''), 'Cliente'))
        END END
    """


def actualizar_ambiente_emision(
    cur,
    venta_id: int,
    ambiente_emision: str,
    empresa_id: int | None = None,
) -> bool:
    """Marca ambiente de emisión ('00' prod, '01' pruebas). Ignora si la columna no existe aún."""
    amb = (ambiente_emision or "").strip()
    if amb not in ("00", "01"):
        return False
    sp = "spamb" + uuid.uuid4().hex[:12]
    cur.execute(f"SAVEPOINT {sp}")
    try:
        if empresa_id is not None:
            cur.execute(
                """
                UPDATE ventas SET ambiente_emision = %s
                WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)
                """,
                (amb, venta_id, empresa_id),
            )
        else:
            cur.execute(
                "UPDATE ventas SET ambiente_emision = %s WHERE id = %s",
                (amb, venta_id),
            )
        ok = cur.rowcount > 0
        cur.execute(f"RELEASE SAVEPOINT {sp}")
        return ok
    except Exception:
        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        return False


def listar_ventas_recientes(
    cur,
    empresa_id: int,
    limit: int = 100,
    ambiente_emision: str | None = None,
):
    """
    Lista ventas activas. Si ambiente_emision ('00'|'01'), filtra como AgilDTE
    (solo documentos del ambiente actual de la empresa).
    """
    etiqueta = _sql_etiqueta_cliente_venta()
    amb = (ambiente_emision or "").strip()
    filtro_amb = ""
    params: list = [empresa_id]
    if amb in ("00", "01"):
        filtro_amb = """
          AND (
            v.ambiente_emision = %s
            OR (v.ambiente_emision IS NULL AND %s = '01')
          )
        """
        params.extend([amb, amb])
    params.append(limit)
    sql = f"""
        SELECT v.id, TO_CHAR(v.fecha_registro, 'DD/MM/YYYY HH24:MI'), v.total_pagar, ({etiqueta}), v.tipo_pago,
               COALESCE(v.tipo_comprobante, 'TICKET'), v.cliente_id
        FROM ventas v
        LEFT JOIN clientes c ON c.id = v.cliente_id
        WHERE (v.empresa_id IS NULL OR v.empresa_id = %s)
          AND COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
          {filtro_amb}
        ORDER BY v.id DESC
        LIMIT %s
        """
    try:
        cur.execute(sql, tuple(params))
        return cur.fetchall()
    except Exception as ex:
        if "ambiente_emision" not in str(ex):
            raise
        cur.connection.rollback()
        params_sin_amb = [empresa_id, limit]
        cur.execute(
            f"""
            SELECT v.id, TO_CHAR(v.fecha_registro, 'DD/MM/YYYY HH24:MI'), v.total_pagar, ({etiqueta}), v.tipo_pago,
                   COALESCE(v.tipo_comprobante, 'TICKET'), v.cliente_id
            FROM ventas v
            LEFT JOIN clientes c ON c.id = v.cliente_id
            WHERE (v.empresa_id IS NULL OR v.empresa_id = %s)
              AND COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
            ORDER BY v.id DESC
            LIMIT %s
            """,
            tuple(params_sin_amb),
        )
        return cur.fetchall()


def actualizar_venta_cabecera(
    cur,
    venta_id: int,
    empresa_id: int,
    cliente_nombre: str,
    tipo_pago: str,
    tipo_comprobante: str,
    cliente_id: int | None,
    estado_cobro: str | None = None,
    retencion_iva: float | None = None,
) -> bool:
    tc = (tipo_comprobante or "TICKET").strip().upper()[:32]
    ret_iva = float(retencion_iva) if retencion_iva is not None else None
    try:
        if ret_iva is not None:
            if estado_cobro is not None:
                ec = (estado_cobro or "COBRADO").strip().upper()[:16]
                cur.execute(
                    """
                    UPDATE ventas SET cliente_nombre = %s, tipo_pago = %s, tipo_comprobante = %s, cliente_id = %s, estado_cobro = %s, retencion_iva = %s
                    WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)
                    """,
                    (cliente_nombre.strip(), tipo_pago, tc, cliente_id, ec if ec in ("COBRADO", "PENDIENTE") else "COBRADO", ret_iva, venta_id, empresa_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE ventas SET cliente_nombre = %s, tipo_pago = %s, tipo_comprobante = %s, cliente_id = %s, retencion_iva = %s
                    WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)
                    """,
                    (cliente_nombre.strip(), tipo_pago, tc, cliente_id, ret_iva, venta_id, empresa_id),
                )
        else:
            if estado_cobro is not None:
                ec = (estado_cobro or "COBRADO").strip().upper()[:16]
                cur.execute(
                    """
                    UPDATE ventas SET cliente_nombre = %s, tipo_pago = %s, tipo_comprobante = %s, cliente_id = %s, estado_cobro = %s
                    WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)
                    """,
                    (cliente_nombre.strip(), tipo_pago, tc, cliente_id, ec if ec in ("COBRADO", "PENDIENTE") else "COBRADO", venta_id, empresa_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE ventas SET cliente_nombre = %s, tipo_pago = %s, tipo_comprobante = %s, cliente_id = %s
                    WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)
                    """,
                    (cliente_nombre.strip(), tipo_pago, tc, cliente_id, venta_id, empresa_id),
                )
        return cur.rowcount > 0
    except Exception:
        cur.connection.rollback()
        if estado_cobro is not None:
            ec = (estado_cobro or "COBRADO").strip().upper()[:16]
            cur.execute(
                """
                UPDATE ventas SET cliente_nombre = %s, tipo_pago = %s, tipo_comprobante = %s, cliente_id = %s, estado_cobro = %s
                WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)
                """,
                (cliente_nombre.strip(), tipo_pago, tc, cliente_id, ec if ec in ("COBRADO", "PENDIENTE") else "COBRADO", venta_id, empresa_id),
            )
        else:
            cur.execute(
                """
                UPDATE ventas SET cliente_nombre = %s, tipo_pago = %s, tipo_comprobante = %s, cliente_id = %s
                WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)
                """,
                (cliente_nombre.strip(), tipo_pago, tc, cliente_id, venta_id, empresa_id),
            )
        return cur.rowcount > 0


def eliminar_venta_restaurar_stock(
    cur,
    venta_id: int,
    empresa_id: int,
    motivo_anulacion: str = "",
    usuario_anulo_id: int | None = None,
) -> bool:
    """Anula la venta (soft-delete): restaura stock, marca estado=ANULADO. Trazabilidad para auditoría."""
    from azdigital.repositories import kardex_repo, productos_repo

    cur.execute(
        "SELECT 1 FROM ventas WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)",
        (venta_id, empresa_id),
    )
    if not cur.fetchone():
        return False
    cur.execute("SELECT producto_id, cantidad FROM venta_detalles WHERE venta_id = %s", (venta_id,))
    for pid, cant in cur.fetchall():
        productos_repo.incrementar_stock(cur, int(pid), float(cant))
    try:
        if kardex_repo.tabla_existe(cur, kardex_repo.TABLA_KARDEX):
            cur.execute("DELETE FROM inventario_kardex WHERE referencia = %s", (f"Venta #{venta_id}",))
    except Exception:
        pass
    motivo = (motivo_anulacion or "").strip() or "Anulación por gestión"
    try:
        cur.execute(
            """
            UPDATE ventas SET estado = 'ANULADO', motivo_anulacion = %s,
                   usuario_anulo_id = %s, fecha_anulacion = CURRENT_TIMESTAMP
            WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)
            """,
            (motivo, usuario_anulo_id, venta_id, empresa_id),
        )
        return cur.rowcount > 0
    except Exception:
        cur.connection.rollback()
        try:
            cur.execute(
                "UPDATE ventas SET estado = 'ANULADO' WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)",
                (venta_id, empresa_id),
            )
            return cur.rowcount > 0
        except Exception:
            cur.connection.rollback()
            cur.execute("DELETE FROM venta_detalles WHERE venta_id = %s", (venta_id,))
            cur.execute("DELETE FROM ventas WHERE id = %s", (venta_id,))
            return True
