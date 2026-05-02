# Programador: Oscar Amaya Romero
from __future__ import annotations

from datetime import date, timedelta

import psycopg2
from flask import Blueprint, jsonify, redirect, render_template, session, url_for

from azdigital.decorators import login_required, _rol_desde_bd
from azdigital.repositories import empresas_repo, productos_repo
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
        if activa is False:
            return False
        if vencimiento and vencimiento < date.today():
            return False
        return True
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
    try:
        db = ConexionDB()
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        emp = empresas_repo.get_empresa(cur, empresa_id)
        cur.close()
        conn.close()
        if emp:
            session["empresa_id"] = empresa_id
            session["empresa_nombre"] = (emp[1] or emp[9] if len(emp) > 9 else emp[1]) or "Empresa"
    except Exception:
        pass
    return redirect(url_for("core.dashboard"))


def _render_dashboard():
    """Renderiza el dashboard de administración para la empresa actual."""
    emp_id = session.get("empresa_id", 1)
    db = ConexionDB()
    v_hoy = db.ejecutar_sql(
        "SELECT SUM(total_pagar) FROM ventas WHERE fecha_registro::date = CURRENT_DATE AND (empresa_id IS NULL OR empresa_id = %s) AND COALESCE(estado, 'ACTIVO') = 'ACTIVO'",
        (emp_id,),
        es_select=True,
    )
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
        "total_ventas": round(float(v_hoy[0][0]), 2) if v_hoy and v_hoy[0][0] else 0.00,
        "total_productos": p_count[0][0] if p_count else 0,
        "total_usuarios": u_count[0][0] if u_count else 0,
        "total_empresas": e_count[0][0] if e_count else 0,
        "total_sucursales": s_count[0][0] if s_count else 0,
    }
    hoy = date.today()
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
    iva_ventas = db.ejecutar_sql(
        """SELECT COALESCE(SUM(total_pagar - (total_pagar/1.13)), 0), COALESCE(SUM(retencion_iva), 0)
           FROM ventas WHERE fecha_registro::date >= %s AND fecha_registro::date <= %s
           AND (empresa_id IS NULL OR empresa_id = %s) AND COALESCE(estado, 'ACTIVO') = 'ACTIVO'""",
        (primer_dia_mes, hoy, emp_id),
        es_select=True,
    )
    iva_debito = round(float(iva_ventas[0][0]), 2) if iva_ventas and iva_ventas[0][0] else 0
    retenciones_ventas = round(float(iva_ventas[0][1]), 2) if iva_ventas and len(iva_ventas[0]) > 1 and iva_ventas[0][1] else 0
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
    ventas_sucursal = []
    top_clientes_cf = []
    try:
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        stock_bajo = productos_repo.productos_stock_bajo(cur, umbral=5, empresa_id=emp_id) or []
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
                """SELECT COALESCE(c.nombre_cliente, v.cliente_nombre, 'Cliente'), COALESCE(SUM(v.total_pagar), 0)
                   FROM ventas v
                   LEFT JOIN clientes c ON c.id = v.cliente_id
                   WHERE v.fecha_registro::date >= %s AND (v.empresa_id IS NULL OR v.empresa_id = %s)
                   AND COALESCE(v.estado, 'ACTIVO') = 'ACTIVO'
                   AND COALESCE(v.tipo_comprobante, '') = 'CREDITO_FISCAL'
                   GROUP BY v.cliente_id, c.nombre_cliente, v.cliente_nombre
                   ORDER BY 2 DESC LIMIT 3""",
                (primer_dia_mes, emp_id),
            )
            top_clientes_cf = cur.fetchall() or []
        except Exception:
            pass
        cur.close()
        conn.close()
    except Exception:
        stock_bajo = []
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
        labels_ventas=[str(r[0]) for r in ventas_7d],
        valores_ventas=[float(r[1]) for r in ventas_7d],
        top_productos=top_productos,
        nombres_top=[r[0] for r in top_productos],
        cantidades_top=[r[1] for r in top_productos],
        ventas_mes=ventas_mes_val,
        proyeccion_mes=proyeccion_mes,
        ventas_mes_anterior=ventas_mes_anterior,
        dias_transcurridos=dias_transcurridos,
        dias_en_mes=dias_en_mes,
        dte_rechazados=dte_rechazados_cnt,
        iva_debito=iva_debito,
        iva_credito=iva_credito,
        iva_estimado=iva_estimado,
        retenciones_acumuladas=retenciones_ventas,
        stock_bajo=stock_bajo,
        ventas_sucursal=ventas_sucursal,
        dte_pendientes=dte_pendientes_cnt,
        top_clientes_cf=top_clientes_cf,
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


@bp.route("/api/mh_status")
@login_required
def api_mh_status():
    """Devuelve {online: true/false} para el semáforo DTE."""
    from azdigital.utils.mh_utils import check_mh_online
    return jsonify(online=check_mh_online())


@bp.route("/")
@login_required
def index():
    rol = _rol_desde_bd()
    if rol in ("ADMIN", "SUPERADMIN"):
        db = ConexionDB()
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        empresas = empresas_repo.listar_empresas(cur) or []
        cur.close()
        conn.close()
        return render_template("dashboard_superadmin.html", empresas=empresas)

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

