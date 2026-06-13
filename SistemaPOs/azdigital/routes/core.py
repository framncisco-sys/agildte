# Programador: Oscar Amaya Romero
from __future__ import annotations

from datetime import date, timedelta

import psycopg2
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from azdigital.decorators import login_required, _rol_desde_bd
from azdigital.repositories import empresas_repo, productos_repo
from azdigital.utils.fecha_sv import hoy_sv
from database import ConexionDB

bp = Blueprint("core", __name__)

RUTAS_SIN_VALIDAR_SUSCRIPCION = {"/login", "/logout", "/suscripcion_expirada"}


def tiene_suscripcion(empresa_id: int = 1) -> bool:
    db = ConexionDB()
    conn = None
    try:
        conn = __import__("psycopg2").connect(**db.config)
        cur = conn.cursor()
        estado = empresas_repo.get_estado_suscripcion(cur, empresa_id)
        cur.close()
        conn.close()
        if not estado:
            return False
        activa, vencimiento = estado[0], estado[1]
        return empresas_repo.es_suscripcion_vigente(bool(activa), vencimiento, hoy_sv())
    except Exception:
        # fail-closed
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


@bp.route("/entrar_empresa/<int:empresa_id>")
@login_required
def entrar_empresa(empresa_id):
    """Solo ADMIN/SUPERADMIN (superusuario): selecciona una empresa para gestionarla."""
    from azdigital.decorators import _rol_desde_bd
    if _rol_desde_bd() not in ("ADMIN", "SUPERADMIN"):
        return redirect(url_for("core.index"))
    from flask import flash

    try:
        db = ConexionDB()
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        emp = empresas_repo.get_empresa(cur, empresa_id)
        cur.close()
        conn.close()
        if emp:
            session["empresa_id"] = empresa_id
            vista = empresas_repo.empresa_row_a_vista(emp)
            session["empresa_nombre"] = (vista.get("nombre_comercial") or vista.get("nombre") or "Empresa") if vista else "Empresa"
            return redirect(url_for("core.dashboard"))
    except Exception as ex:
        current_app.logger.exception("entrar_empresa")
        flash(f"No se pudo abrir la empresa: {ex}", "danger")
        return redirect(url_for("core.index"))
    flash("Empresa no encontrada en el sistema POS.", "warning")
    return redirect(url_for("core.index"))


def _render_dashboard():
    """Renderiza el dashboard de administración para la empresa actual."""
    emp_id = session.get("empresa_id", 1)
    hoy = hoy_sv()
    db = ConexionDB()
    v_hoy = db.ejecutar_sql(
        """SELECT COALESCE(SUM(total_pagar), 0) FROM ventas
           WHERE fecha_registro::date = %s
           AND (empresa_id IS NULL OR empresa_id = %s)
           AND COALESCE(estado, 'ACTIVO') = 'ACTIVO'""",
        (hoy, emp_id),
        es_select=True,
    )
    ventas_hoy_val = round(float(v_hoy[0][0]), 2) if v_hoy and v_hoy[0][0] else 0.00
    ayer = hoy - timedelta(days=1)
    v_ayer = db.ejecutar_sql(
        """SELECT COALESCE(SUM(total_pagar), 0) FROM ventas
           WHERE fecha_registro::date = %s
           AND (empresa_id IS NULL OR empresa_id = %s)
           AND COALESCE(estado, 'ACTIVO') = 'ACTIVO'""",
        (ayer, emp_id),
        es_select=True,
    )
    ventas_ayer_val = round(float(v_ayer[0][0]), 2) if v_ayer and v_ayer[0][0] else 0.00
    n_hoy = db.ejecutar_sql(
        """SELECT COUNT(*) FROM ventas
           WHERE fecha_registro::date = %s
           AND (empresa_id IS NULL OR empresa_id = %s)
           AND COALESCE(estado, 'ACTIVO') = 'ACTIVO'""",
        (hoy, emp_id),
        es_select=True,
    )
    n_ventas_hoy = int(n_hoy[0][0]) if n_hoy and n_hoy[0][0] else 0
    try:
        p_count = db.ejecutar_sql("SELECT COUNT(*) FROM productos WHERE empresa_id = %s", (emp_id,), es_select=True)
    except Exception:
        p_count = db.ejecutar_sql("SELECT COUNT(*) FROM productos", (), es_select=True)
    u_count = db.ejecutar_sql(
        "SELECT COUNT(*) FROM usuarios u LEFT JOIN sucursales s ON u.sucursal_id = s.id WHERE COALESCE(u.empresa_id, s.empresa_id, 1) = %s",
        (emp_id,),
        es_select=True,
    )
    e_count = db.ejecutar_sql("SELECT COUNT(*) FROM empresas WHERE id = %s", (emp_id,), es_select=True)
    s_count = db.ejecutar_sql("SELECT COUNT(*) FROM sucursales WHERE empresa_id = %s", (emp_id,), es_select=True)
    resumen = {
        "total_ventas": ventas_hoy_val,
        "total_productos": p_count[0][0] if p_count else 0,
        "total_usuarios": u_count[0][0] if u_count else 0,
        "total_empresas": e_count[0][0] if e_count else 0,
        "total_sucursales": s_count[0][0] if s_count else 0,
    }
    mes_actual = hoy.month
    ano_actual = hoy.year
    primer_dia_mes = date(ano_actual, mes_actual, 1)
    ventas_mes = db.ejecutar_sql(
        """SELECT COALESCE(SUM(total_pagar), 0)
           FROM ventas WHERE fecha_registro::date >= %s AND fecha_registro::date <= %s
           AND (empresa_id IS NULL OR empresa_id = %s) AND COALESCE(estado, 'ACTIVO') = 'ACTIVO'""",
        (primer_dia_mes, hoy, emp_id),
        es_select=True,
    )
    ventas_mes_val = round(float(ventas_mes[0][0]), 2) if ventas_mes and ventas_mes[0][0] else 0.00
    dias_transcurridos = (hoy - primer_dia_mes).days + 1
    if mes_actual == 12:
        dias_en_mes = 31
    else:
        dias_en_mes = (date(ano_actual, mes_actual + 1, 1) - timedelta(days=1)).day
    prom_diario_mes = ventas_mes_val / dias_transcurridos if dias_transcurridos > 0 else 0
    proyeccion_mes = round(prom_diario_mes * dias_en_mes, 2) if prom_diario_mes else 0
    mes_anterior_fin = primer_dia_mes - timedelta(days=1)
    mes_anterior_inicio = date(mes_anterior_fin.year, mes_anterior_fin.month, 1)
    ventas_mes_ant = db.ejecutar_sql(
        """SELECT COALESCE(SUM(total_pagar), 0)
           FROM ventas WHERE fecha_registro::date BETWEEN %s AND %s
           AND (empresa_id IS NULL OR empresa_id = %s) AND COALESCE(estado, 'ACTIVO') = 'ACTIVO'""",
        (mes_anterior_inicio, mes_anterior_fin, emp_id),
        es_select=True,
    )
    ventas_mes_anterior = round(float(ventas_mes_ant[0][0]), 2) if ventas_mes_ant and ventas_mes_ant[0][0] else 0.00
    dte_rechazados = db.ejecutar_sql(
        """SELECT COUNT(*) FROM ventas WHERE (empresa_id IS NULL OR empresa_id = %s)
           AND COALESCE(estado_dte, 'RESPALDO') IN ('RECHAZADO', 'CONTINGENCIA')""",
        (emp_id,),
        es_select=True,
    )
    dte_rechazados_cnt = dte_rechazados[0][0] if dte_rechazados and dte_rechazados[0][0] else 0
    dte_pendientes = db.ejecutar_sql(
        """SELECT COUNT(*) FROM ventas WHERE (empresa_id IS NULL OR empresa_id = %s)
           AND COALESCE(estado, 'ACTIVO') = 'ACTIVO'
           AND COALESCE(estado_dte, 'RESPALDO') IN ('PENDIENTE_TRANSMISION', 'CONTINGENCIA')""",
        (emp_id,),
        es_select=True,
    )
    dte_pendientes_cnt = dte_pendientes[0][0] if dte_pendientes and dte_pendientes[0][0] else 0
    iva_por_tipo = db.ejecutar_sql(
        """SELECT COALESCE(UPPER(TRIM(tipo_comprobante)), 'TICKET'),
                  COALESCE(SUM(total_pagar - (total_pagar/1.13)), 0),
                  COALESCE(SUM(retencion_iva), 0),
                  COUNT(*),
                  COALESCE(SUM(total_pagar), 0)
           FROM ventas
           WHERE fecha_registro::date >= %s AND fecha_registro::date <= %s
             AND (empresa_id IS NULL OR empresa_id = %s)
             AND COALESCE(estado, 'ACTIVO') = 'ACTIVO'
           GROUP BY COALESCE(UPPER(TRIM(tipo_comprobante)), 'TICKET')""",
        (primer_dia_mes, hoy, emp_id),
        es_select=True,
    ) or []
    iva_debito_ccf = iva_debito_cf = iva_debito_ticket = 0.0
    retenciones_ventas = 0.0
    n_ventas_ccf = n_ventas_cf = n_ventas_ticket = 0
    total_ccf_mes = 0.0
    for row in iva_por_tipo:
        tipo = (row[0] or "TICKET").upper()
        iva_row = float(row[1] or 0)
        ret_row = float(row[2] or 0) if len(row) > 2 else 0.0
        cnt = int(row[3] or 0) if len(row) > 3 else 0
        total_tipo = float(row[4] or 0) if len(row) > 4 else 0.0
        retenciones_ventas += ret_row
        if tipo == "CREDITO_FISCAL":
            iva_debito_ccf += iva_row
            n_ventas_ccf += cnt
            total_ccf_mes += total_tipo
        elif tipo == "FACTURA":
            iva_debito_cf += iva_row
            n_ventas_cf += cnt
        else:
            iva_debito_ticket += iva_row
            n_ventas_ticket += cnt
    iva_debito_ccf = round(iva_debito_ccf, 2)
    iva_debito_cf = round(iva_debito_cf, 2)
    iva_debito_ticket = round(iva_debito_ticket, 2)
    total_ccf_mes = round(total_ccf_mes, 2)
    iva_debito = round(iva_debito_ccf + iva_debito_cf + iva_debito_ticket, 2)
    retenciones_ventas = round(retenciones_ventas, 2)
    iva_compras = db.ejecutar_sql(
        """SELECT COALESCE(SUM(c.total - (c.total/1.13)), 0), COALESCE(SUM(c.retencion_iva), 0)
           FROM compras c WHERE c.fecha::date >= %s AND c.fecha::date <= %s AND c.empresa_id = %s""",
        (primer_dia_mes, hoy, emp_id),
        es_select=True,
    )
    iva_credito = round(float(iva_compras[0][0]), 2) if iva_compras and iva_compras[0][0] else 0
    ret_compras = round(float(iva_compras[0][1]), 2) if iva_compras and len(iva_compras[0]) > 1 and iva_compras[0][1] else 0
    iva_estimado = round(iva_debito - iva_credito - retenciones_ventas + ret_compras, 2)
    stock_bajo = []
    n_stock_bajo_total = 0
    ventas_sucursal = []
    top_clientes_cf = []
    try:
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        stock_bajo = productos_repo.productos_stock_bajo(cur, umbral=5, empresa_id=emp_id) or []
        n_stock_bajo_total = productos_repo.contar_productos_stock_bajo(cur, umbral=5, empresa_id=emp_id)
        try:
            cur.execute(
                """SELECT COALESCE(s.nombre, 'Sin sucursal'), COALESCE(SUM(v.total_pagar), 0)
                   FROM ventas v LEFT JOIN sucursales s ON s.id = v.sucursal_id
                   WHERE v.fecha_registro::date >= %s AND (v.empresa_id IS NULL OR v.empresa_id = %s)
                   AND COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
                   GROUP BY s.id, s.nombre ORDER BY 2 DESC""",
                (primer_dia_mes, emp_id),
            )
            ventas_sucursal = cur.fetchall() or []
        except Exception:
            pass
        try:
            cur.execute(
                """SELECT COALESCE(c.nombre_cliente, v.cliente_nombre, 'Cliente'),
                          COALESCE(SUM(v.total_pagar), 0),
                          COUNT(*)::int
                   FROM ventas v
                   LEFT JOIN clientes c ON c.id = v.cliente_id
                   WHERE v.fecha_registro::date >= %s AND v.fecha_registro::date <= %s
                   AND (v.empresa_id IS NULL OR v.empresa_id = %s)
                   AND COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
                   AND COALESCE(v.tipo_comprobante, '') = 'CREDITO_FISCAL'
                   GROUP BY v.cliente_id, c.nombre_cliente, v.cliente_nombre
                   ORDER BY 2 DESC LIMIT 5""",
                (primer_dia_mes, hoy, emp_id),
            )
            top_clientes_cf = cur.fetchall() or []
        except Exception:
            pass
        cur.close()
        conn.close()
    except Exception:
        stock_bajo = []
        n_stock_bajo_total = 0
        ventas_sucursal = []
        top_clientes_cf = []
    desde = (hoy - timedelta(days=6)).strftime("%Y-%m-%d")
    ventas_7d = db.ejecutar_sql(
        """SELECT fecha_registro::date, COALESCE(SUM(total_pagar), 0)
           FROM ventas WHERE fecha_registro::date >= %s AND (empresa_id IS NULL OR empresa_id = %s) AND COALESCE(estado, 'ACTIVO') = 'ACTIVO'
           GROUP BY 1 ORDER BY 1""",
        (desde, emp_id),
        es_select=True,
    ) or []
    _DIAS_CORTO = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
    dia_hoy_nombre = _DIAS_CORTO[hoy.weekday()]
    ventas_por_dia = {}
    for row in ventas_7d:
        fd = row[0]
        if hasattr(fd, "isoformat"):
            ventas_por_dia[fd.isoformat()] = float(row[1] or 0)
        else:
            ventas_por_dia[str(fd)[:10]] = float(row[1] or 0)
    labels_ventas = []
    valores_ventas = []
    fechas_ventas = []
    for offset in range(6, -1, -1):
        dia = hoy - timedelta(days=offset)
        iso = dia.isoformat()
        fechas_ventas.append(iso)
        labels_ventas.append(f"{_DIAS_CORTO[dia.weekday()]} {dia.strftime('%d/%m')}")
        valores_ventas.append(round(ventas_por_dia.get(iso, 0.0), 2))
    _MESES_CORTO = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
    _MESES_LARGO = (
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    )
    mes_corto = _MESES_CORTO[hoy.month - 1]
    mes_largo = _MESES_LARGO[hoy.month - 1]
    pct_avance_mes = min(100, round((dias_transcurridos / dias_en_mes) * 100)) if dias_en_mes else 0
    prom_diario_mes_val = round(prom_diario_mes, 2)
    try:
        top_productos = db.ejecutar_sql(
            """SELECT p.nombre, COALESCE(SUM(dv.cantidad), 0)::int
               FROM venta_detalles dv
               JOIN productos p ON dv.producto_id = p.id
               JOIN ventas v ON dv.venta_id = v.id
               WHERE (v.empresa_id IS NULL OR v.empresa_id = %s) AND COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
               GROUP BY p.id, p.nombre ORDER BY 2 DESC LIMIT 10""",
            (emp_id,),
            es_select=True,
        ) or []
    except Exception:
        top_productos = db.ejecutar_sql(
            """SELECT p.nombre, COALESCE(SUM(dv.cantidad), 0)::int
               FROM venta_detalles dv
               JOIN productos p ON dv.producto_id = p.id
               JOIN ventas v ON dv.venta_id = v.id
               WHERE COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
               GROUP BY p.id, p.nombre ORDER BY 2 DESC LIMIT 10""",
            (),
            es_select=True,
        ) or []
    return render_template(
        "dashboard.html",
        resumen=resumen,
        labels_ventas=labels_ventas,
        valores_ventas=valores_ventas,
        fechas_ventas=fechas_ventas,
        top_productos=top_productos,
        nombres_top=[r[0] for r in top_productos],
        cantidades_top=[r[1] for r in top_productos],
        ventas_mes=ventas_mes_val,
        proyeccion_mes=proyeccion_mes,
        ventas_mes_anterior=ventas_mes_anterior,
        dias_transcurridos=dias_transcurridos,
        dias_en_mes=dias_en_mes,
        mes_corto=mes_corto,
        mes_largo=mes_largo,
        ano_mes=ano_actual,
        pct_avance_mes=pct_avance_mes,
        inicio_mes=primer_dia_mes.isoformat(),
        fin_mes=hoy.isoformat(),
        prom_diario_mes=prom_diario_mes_val,
        fecha_hoy=hoy.isoformat(),
        fecha_hoy_fmt=hoy.strftime("%d/%m/%Y"),
        dia_hoy_nombre=dia_hoy_nombre,
        ventas_ayer=ventas_ayer_val,
        n_ventas_hoy=n_ventas_hoy,
        dte_rechazados=dte_rechazados_cnt,
        iva_debito=iva_debito,
        iva_debito_ccf=iva_debito_ccf,
        iva_debito_cf=iva_debito_cf,
        iva_debito_ticket=iva_debito_ticket,
        n_ventas_ccf=n_ventas_ccf,
        n_ventas_cf=n_ventas_cf,
        n_ventas_ticket=n_ventas_ticket,
        iva_credito=iva_credito,
        iva_estimado=iva_estimado,
        retenciones_acumuladas=retenciones_ventas,
        stock_bajo=stock_bajo,
        n_stock_bajo_total=n_stock_bajo_total,
        ventas_sucursal=ventas_sucursal,
        dte_pendientes=dte_pendientes_cnt,
        top_clientes_cf=top_clientes_cf,
        total_ccf_mes=total_ccf_mes,
    )


@bp.route("/dashboard")
@login_required
def dashboard():
    """Dashboard: ADMIN/SUPERADMIN (con empresa), GERENTE, siempre con empresa."""
    rol = session.get("rol")
    if rol not in ("ADMIN", "SUPERADMIN", "GERENTE"):
        return redirect(url_for("core.index"))
    if rol in ("ADMIN", "SUPERADMIN") and not session.get("empresa_id"):
        return redirect(url_for("core.index"))
    return _render_dashboard()


@bp.route("/api/actividades")
@login_required
def api_actividades_agildte():
    """
    Catálogo MH de actividades económicas (proxy a AgilDTE GET /api/actividades/).
    PosAgil y configuración usan la misma fuente que el portal AgilDTE.
    """
    search = (request.args.get("search") or "").strip() or None
    try:
        limit = int(request.args.get("limit") or 50)
    except (TypeError, ValueError):
        limit = 50
    try:
        offset = int(request.args.get("offset") or 0)
    except (TypeError, ValueError):
        offset = 0
    from azdigital.integration.agildte_actividades import listar_actividades_agildte

    payload = listar_actividades_agildte(search=search, limit=limit, offset=offset)
    status = 200 if payload.get("ok") else 503
    return jsonify(payload), status


@bp.route("/posagil/agildte_status")
@bp.route("/api/mh_status")
@bp.route("/api/agildte_status")
@login_required
def api_agildte_status():
    """
    Estado del canal DTE vía AgilDTE (el POS ya no habla directo con el portal MH).

    La ruta canónica es ``/posagil/agildte_status`` para evitar proxies que reenvían
    ``/api/*`` a otro backend (respuesta HTML → «respuesta no JSON» en el dashboard).

    Compatibilidad: ``/api/mh_status`` y ``/api/agildte_status`` siguen sirviendo el mismo JSON.
    """
    try:
        from azdigital.integration.agildte_client import check_agildte_api_reachable

        st = check_agildte_api_reachable()
        return jsonify(
            online=st["online"],
            configured=st.get("configured", True),
            detail=st.get("detail"),
            source="agildte",
        )
    except Exception:
        current_app.logger.exception("api_agildte_status")
        return jsonify(
            online=False,
            configured=True,
            detail="pos_error",
            source="agildte",
        )


@bp.route("/")
@login_required
def index():
    rol = _rol_desde_bd()
    if rol in ("ADMIN", "SUPERADMIN"):
        db = ConexionDB()
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        empresas = empresas_repo.listar_empresas_detalle(cur) or []
        cur.close()
        conn.close()
        hoy = date.today()
        total = len(empresas)
        vigentes = sum(
            1 for e in empresas if empresas_repo.es_suscripcion_vigente(bool(e[4]), e[5], hoy)
        )
        return render_template(
            "dashboard_superadmin.html",
            empresas=empresas,
            total_empresas=total,
            empresas_vigentes=vigentes,
            hoy=hoy,
        )

    if rol == "GERENTE":
        return redirect(url_for("core.dashboard"))
    if not tiene_suscripcion(session.get("empresa_id", 1)):
        return redirect(url_for("core.suscripcion_expirada"))
    if rol == "CONTADOR":
        return redirect(url_for("admin.reporte"))
    if rol == "BODEGUERO":
        return redirect(url_for("admin.inventario"))
    if rol == "CAJERO":
        return redirect(url_for("pos.ventas_pos"))
    return redirect(url_for("pos.ventas_pos"))


@bp.route("/ayuda")
@login_required
def ayuda():
    """Página con todas las URLs que funcionan. Útil cuando algo da 'Not Found'."""
    return """
    <!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
    <title>AZ DIGITAL - Enlaces</title>
    <style>body{font-family:sans-serif;max-width:500px;margin:50px auto;padding:25px;}
    a{display:block;padding:10px;margin:5px 0;background:#f1f5f9;border-radius:8px;color:#1e40af;text-decoration:none;}
    a:hover{background:#e2e8f0;} h1{color:#334155;}</style></head><body>
    <h1>AZ DIGITAL - Enlaces que funcionan</h1>
    <p>Si ves "Not Found", usa una de estas direcciones:</p>
    <a href="/">Inicio (panel)</a>
    <a href="/login">Iniciar sesión</a>
    <a href="/ventas_pos">Punto de venta</a>
    <a href="/inventario">Inventario</a>
    <a href="/clientes">Clientes</a>
    <a href="/configuracion">Configuración empresa</a>
    <a href="/usuarios">Usuarios</a>
    <a href="/sucursales">Sucursales</a>
    <a href="/reporte">Reportes</a>
    </body></html>
    """


@bp.route("/suscripcion_expirada")
@login_required
def suscripcion_expirada():
    """Página mostrada cuando la suscripción de la empresa ha expirado."""
    return render_template("suscripcion_expirada.html")


@bp.route("/ventas")
@bp.route("/index")
@login_required
def redirects_comunes():
    """Redirige URLs frecuentes: /ventas -> ventas_pos, /index -> /"""
    from flask import request
    if request.path.rstrip("/") == "/ventas":
        return redirect(url_for("pos.ventas_pos"))
    return redirect(url_for("core.index"))

