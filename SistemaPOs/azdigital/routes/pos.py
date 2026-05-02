# Programador: Oscar Amaya Romero
from __future__ import annotations

from datetime import date
import os

import psycopg2
from flask import Blueprint, current_app, jsonify, render_template, request, session

from azdigital.decorators import login_required, rol_requerido
from azdigital.repositories import (
    actividades_repo,
    clientes_repo,
    empresas_repo,
    historial_usuarios_repo,
    pos_favoritos_repo,
    presentaciones_repo,
    productos_repo,
    promociones_repo,
    usuarios_repo,
    ventas_repo,
)
from azdigital.services.auth_service import verificar_password
from azdigital.services.whatsapp_notificacion_service import preparar_envio_whatsapp_venta
from azdigital.integration.agildte_sync import intentar_sync_venta_si_habilitado
from azdigital.services.ventas_service import aplicar_descuento, crear_venta_desde_carrito, persistir_venta
from azdigital.utils.historial_helper import registrar_accion
from azdigital.utils.mh_cat003_unidades import normalizar_codigo_mh
from azdigital.utils.numero_letras import numero_a_letras_dolares
from azdigital.utils.qr_dte import generar_qr_dte_base64, url_consulta_publica_dte
from database import ConexionDB

bp = Blueprint("pos", __name__)


def _empresa_fiscal_por_fila(empresa) -> dict:
    """
    Fila `empresas` (orden típico SELECT * / schema_bootstrap_min):
    0 id, 1 nombre_comercial, 2 nombre (razón social), 3 nit, 4 nrc,
    5 actividad_economica, 6 giro, 7 direccion, 8 telefono, 9 correo, ...
    """
    if not empresa or not isinstance(empresa, (tuple, list)):
        return {
            "nombre_comercial": "Empresa",
            "nombre_razon": "",
            "nit": "—",
            "nrc": "—",
            "actividad": "",
            "giro": "",
            "direccion": "",
            "telefono": "",
            "correo": "",
        }
    nc = (empresa[1] or "").strip() if len(empresa) > 1 else ""
    rz = (empresa[2] or "").strip() if len(empresa) > 2 else ""
    nit = (empresa[3] or "").strip() if len(empresa) > 3 else ""
    nrc = (empresa[4] or "").strip() if len(empresa) > 4 else ""
    act = (empresa[5] or "").strip() if len(empresa) > 5 else ""
    giro = (empresa[6] or "").strip() if len(empresa) > 6 else ""
    dir_ = (empresa[7] or "").strip() if len(empresa) > 7 else ""
    tel = (empresa[8] or "").strip() if len(empresa) > 8 else ""
    mail = (empresa[9] or "").strip() if len(empresa) > 9 else ""
    return {
        "nombre_comercial": nc or "Empresa",
        "nombre_razon": rz,
        "nit": nit or "—",
        "nrc": nrc or "—",
        "actividad": act,
        "giro": giro,
        "direccion": dir_,
        "telefono": tel,
        "correo": mail,
    }


def _emisor_desde_empresa(empresa) -> dict:
    """Compatibilidad comprobante A4 / emisor (índices corregidos)."""
    f = _empresa_fiscal_por_fila(empresa)
    return {
        "nombre": f["nombre_comercial"],
        "nit": f["nit"],
        "nrc": f["nrc"],
        "actividad": f["actividad"],
        "direccion": f["direccion"],
        "telefono": f["telefono"],
        "correo": f["correo"],
        "nombre_comercial": f["nombre_comercial"],
    }


def _parse_cliente_id(raw) -> int | None:
    if raw is None or raw is False:
        return None
    if isinstance(raw, str) and not str(raw).strip():
        return None
    if isinstance(raw, bool):
        return None
    try:
        n = int(float(raw))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


@bp.route("/ventas_pos")
@login_required
def ventas_pos():
    r = (session.get("rol") or "").strip().upper()
    es_super = r in ("ADMIN", "SUPERADMIN")
    requiere_clave_supervisor = r in ("CAJERO", "BODEGUERO")
    requiere_clave_supervisor_descuento = r in ("CAJERO", "BODEGUERO")
    limite_descuento_cajero = 5
    try:
        empresa_id_pos = int(session.get("empresa_id") or 1)
    except (TypeError, ValueError):
        empresa_id_pos = 1
    suc_u = session.get("sucursal_id")
    try:
        sucursal_id_pos = int(suc_u) if suc_u is not None and str(suc_u).strip().isdigit() else None
    except (TypeError, ValueError):
        sucursal_id_pos = None
    tok_ag = (session.get("agildte_access_token") or "").strip()
    return render_template(
        "ventas.html",
        es_superadmin=es_super,
        requiere_clave_supervisor=requiere_clave_supervisor,
        requiere_clave_supervisor_descuento=requiere_clave_supervisor_descuento,
        limite_descuento_cajero=limite_descuento_cajero,
        empresa_id_pos=empresa_id_pos,
        sucursal_id_pos=sucursal_id_pos,
        agildte_bearer_para_fetch=tok_ag if tok_ag else None,
    )


@bp.route("/autorizar_eliminar_item", methods=["POST"])
@rol_requerido("GERENTE", "CAJERO", "BODEGUERO")
def autorizar_eliminar_item():
    """Valida usuario y clave de Gerente/Admin para autorizar borrar item del carrito (anti-fraude)."""
    datos = request.get_json() or {}
    username = (datos.get("username") or "").strip()
    password = (datos.get("password") or "").strip()
    if not username or not password:
        return jsonify({"ok": False, "msg": "Usuario y contraseña requeridos."})
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        u = usuarios_repo.get_usuario_login(cur, username)
        if not u:
            return jsonify({"ok": False, "msg": "Usuario o contraseña incorrectos."})
        user_id, _, password_hash, rol, *_ = u[:5]
        rol = (rol or "").strip().upper()
        if rol not in ("GERENTE", "ADMIN", "SUPERADMIN"):
            return jsonify({"ok": False, "msg": "Solo Gerente o Administrador puede autorizar."})
        if not verificar_password(password_hash, password):
            return jsonify({"ok": False, "msg": "Usuario o contraseña incorrectos."})
        return jsonify({"ok": True})
    finally:
        cur.close()
        conn.close()


@bp.route("/buscar_clientes")
@rol_requerido("GERENTE", "CAJERO")
def buscar_clientes():
    q = (request.args.get("q") or "").strip().upper()
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        emp_id = session.get("empresa_id", 1)
        res = clientes_repo.buscar_clientes(cur, q, empresa_id=emp_id, limit=15) or []
        clientes = [
            {
                "id": r[0],
                "nombre": r[1],
                "documento": (r[2] or "").strip(),
                "tipo_documento": (r[3] or "").strip(),
                "contribuyente": bool(r[4]) if len(r) > 4 else False,
                "es_gran_contribuyente": bool(r[5]) if len(r) > 5 else False,
                "nit": (r[2] or "").strip(),
                "telefono": (r[6] or "").strip() if len(r) > 6 else "",
            }
            for r in res
        ]
        return jsonify(clientes)
    finally:
        cur.close()
        conn.close()


@bp.route("/cliente/<int:cliente_id>/datos")
@rol_requerido("GERENTE", "CAJERO")
def cliente_datos(cliente_id: int):
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        emp_id = session.get("empresa_id", 1)
        cl = clientes_repo.get_cliente(cur, cliente_id)
        if not cl or (cl[1] != emp_id and cl[1] is not None):
            return jsonify({"error": "No encontrado"}), 404
        return jsonify({
            "id": cl[0],
            "nombre": (cl[3] or "").strip(),
            "tipo_documento": (cl[4] or "").strip(),
            "numero_documento": (cl[5] or "").strip(),
            "correo": (cl[6] or "").strip(),
            "contribuyente": bool(cl[7]) if len(cl) > 7 else False,
            "es_gran_contribuyente": bool(cl[8]) if len(cl) > 8 else False,
            "direccion": (cl[9] or "").strip(),
            "telefono": (cl[10] or "").strip(),
            "codigo_actividad": (cl[11] or "").strip() if len(cl) > 11 else "",
        })
    finally:
        cur.close()
        conn.close()


@bp.route("/buscar_producto/<codigo>")
@rol_requerido("GERENTE", "CAJERO")
def buscar_producto(codigo: str):
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        emp_id = session.get("empresa_id", 1)
        suc_u = session.get("sucursal_id")
        suc_f = int(suc_u) if suc_u is not None and str(suc_u).strip().isdigit() else None
        r = productos_repo.buscar_por_codigo(cur, codigo, empresa_id=emp_id, sucursal_id_usuario=suc_f)
        if not r:
            return jsonify({"error": "No encontrado"}), 404
        promo_tipo = (r[4] or "").strip().upper() if len(r) > 4 else ""
        promo_val = float(r[5]) if len(r) > 5 and r[5] else 0
        promo_vc, promo_vp, promo_dm = 2, 1, None
        try:
            promo_activa = promociones_repo.get_promocion_activa_producto(cur, r[0], emp_id, date.today())
            if promo_activa:
                promo_tipo, promo_val = promo_activa[0], float(promo_activa[1] or 0)
                if len(promo_activa) > 4:
                    promo_vc = float(promo_activa[2] or 2)
                    promo_vp = float(promo_activa[3] or 1)
                    promo_dm = float(promo_activa[4]) if promo_activa[4] is not None else None
                if promo_tipo == "DESCUENTO_CANTIDAD" and len(promo_activa) > 6 and promo_activa[6] is not None:
                    promo_vc = float(promo_activa[6])
        except Exception:
            pass
        if promo_tipo not in ("2X1", "3X2", "PORCENTAJE", "DESCUENTO_MONTO", "VOLUMEN", "REGALO", "PRECIO_FIJO", "DESCUENTO_CANTIDAD"):
            promo_tipo = ""
        fracc = bool(r[6]) if len(r) > 6 else False
        uxcaja = int(r[7]) if len(r) > 7 and r[7] is not None else None
        uxdoc = int(r[8]) if len(r) > 8 and r[8] is not None else 12
        mh = normalizar_codigo_mh(str(r[9]) if len(r) > 9 else None)
        nom_prod = str(r[1] or "").strip() if len(r) > 1 else None
        pres = presentaciones_repo.lista_para_pos_json(cur, int(r[0]), uxdoc, uxcaja, nombre_producto=nom_prod)
        ex_val = float(r[10]) if len(r) > 10 and r[10] is not None else 0.0
        return jsonify({
            "id": r[0], "nombre": r[1], "precio": float(r[2]), "codigo": (r[3] or "").strip(),
            "promocion_tipo": promo_tipo, "promocion_valor": promo_val,
            "promocion_valor_comprar": promo_vc, "promocion_valor_pagar": promo_vp, "promocion_descuento_monto": promo_dm,
            "fraccionable": fracc, "unidades_por_caja": uxcaja, "unidades_por_docena": uxdoc, "mh_codigo_unidad": mh,
            "presentaciones": pres,
            "existencia": ex_val,
        })
    finally:
        cur.close()
        conn.close()


@bp.route("/productos_pos_cache")
@rol_requerido("GERENTE", "CAJERO", "BODEGUERO")
def productos_pos_cache():
    """Lista todos los productos para cache offline del POS. Máx 800 para no exceder localStorage."""
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        emp_id = session.get("empresa_id", 1)
        suc_u = session.get("sucursal_id")
        suc_f = int(suc_u) if suc_u is not None and str(suc_u).strip().isdigit() else None
        res = productos_repo.buscar_por_nombre(cur, "", limit=800, empresa_id=emp_id, sucursal_id_usuario=suc_f) or []
        productos = []
        for r in res:
            promo_tipo = (r[4] or "").strip().upper() if len(r) > 4 else ""
            promo_val = float(r[5]) if len(r) > 5 and r[5] else 0
            promo_vc, promo_vp, promo_dm = 2, 1, None
            try:
                promo_activa = promociones_repo.get_promocion_activa_producto(cur, r[0], emp_id, date.today())
                if promo_activa:
                    promo_tipo, promo_val = promo_activa[0], float(promo_activa[1] or 0)
                    if len(promo_activa) > 4:
                        promo_vc = float(promo_activa[2] or 2)
                        promo_vp = float(promo_activa[3] or 1)
                        promo_dm = float(promo_activa[4]) if promo_activa[4] is not None else None
                    if promo_tipo == "DESCUENTO_CANTIDAD" and len(promo_activa) > 6 and promo_activa[6] is not None:
                        promo_vc = float(promo_activa[6])
            except Exception:
                pass
            if promo_tipo not in ("2X1", "3X2", "PORCENTAJE", "DESCUENTO_MONTO", "VOLUMEN", "REGALO", "PRECIO_FIJO", "DESCUENTO_CANTIDAD"):
                promo_tipo = ""
            fracc = bool(r[6]) if len(r) > 6 else False
            uxcaja = int(r[7]) if len(r) > 7 and r[7] is not None else None
            uxdoc = int(r[8]) if len(r) > 8 and r[8] is not None else 12
            mh = normalizar_codigo_mh(str(r[9]) if len(r) > 9 else None)
            nom_prod = str(r[1] or "").strip() if len(r) > 1 else None
            pres = presentaciones_repo.lista_para_pos_json(cur, int(r[0]), uxdoc, uxcaja, nombre_producto=nom_prod)
            ex_cache = float(r[10]) if len(r) > 10 and r[10] is not None else 0.0
            productos.append({
                "id": r[0], "nombre": r[1], "precio": float(r[2]), "codigo": (r[3] or "").strip(),
                "promocion_tipo": promo_tipo, "promocion_valor": promo_val,
                "promocion_valor_comprar": promo_vc, "promocion_valor_pagar": promo_vp, "promocion_descuento_monto": promo_dm,
                "fraccionable": fracc, "unidades_por_caja": uxcaja, "unidades_por_docena": uxdoc, "mh_codigo_unidad": mh,
                "presentaciones": pres,
                "existencia": ex_cache,
            })
        return jsonify({"productos": productos, "empresa_id": emp_id})
    finally:
        cur.close()
        conn.close()


def _fila_a_producto_pos_json(cur, r: tuple, emp_id: int) -> dict:
    """Convierte fila SQL del catálogo POS a JSON (promociones activas + presentaciones)."""
    promo_tipo = (r[4] or "").strip().upper() if len(r) > 4 else ""
    promo_val = float(r[5]) if len(r) > 5 and r[5] else 0
    promo_vc, promo_vp, promo_dm = 2, 1, None
    try:
        promo_activa = promociones_repo.get_promocion_activa_producto(cur, r[0], emp_id, date.today())
        if promo_activa:
            promo_tipo, promo_val = promo_activa[0], float(promo_activa[1] or 0)
            if len(promo_activa) > 4:
                promo_vc = float(promo_activa[2] or 2)
                promo_vp = float(promo_activa[3] or 1)
                promo_dm = float(promo_activa[4]) if promo_activa[4] is not None else None
            if promo_tipo == "DESCUENTO_CANTIDAD" and len(promo_activa) > 6 and promo_activa[6] is not None:
                promo_vc = float(promo_activa[6])
    except Exception:
        pass
    if promo_tipo not in ("2X1", "3X2", "PORCENTAJE", "DESCUENTO_MONTO", "VOLUMEN", "REGALO", "PRECIO_FIJO", "DESCUENTO_CANTIDAD"):
        promo_tipo = ""
    fracc = bool(r[6]) if len(r) > 6 else False
    uxcaja = int(r[7]) if len(r) > 7 and r[7] is not None else None
    uxdoc = int(r[8]) if len(r) > 8 and r[8] is not None else 12
    mh = normalizar_codigo_mh(str(r[9]) if len(r) > 9 else None)
    nom_prod = str(r[1] or "").strip() if len(r) > 1 else None
    pres = presentaciones_repo.lista_para_pos_json(cur, int(r[0]), uxdoc, uxcaja, nombre_producto=nom_prod)
    ex = float(r[10]) if len(r) > 10 and r[10] is not None else 0.0
    return {
        "id": r[0],
        "nombre": r[1],
        "precio": float(r[2]),
        "codigo": (r[3] or "").strip(),
        "promocion_tipo": promo_tipo,
        "promocion_valor": promo_val,
        "promocion_valor_comprar": promo_vc,
        "promocion_valor_pagar": promo_vp,
        "promocion_descuento_monto": promo_dm,
        "fraccionable": fracc,
        "unidades_por_caja": uxcaja,
        "unidades_por_docena": uxdoc,
        "mh_codigo_unidad": mh,
        "presentaciones": pres,
        "existencia": ex,
    }


@bp.route("/pos/catalogo_productos")
@rol_requerido("GERENTE", "CAJERO", "BODEGUERO")
def pos_catalogo_productos():
    """Catálogo completo para modal POS: existencia + precio (misma sucursal/empresa que sesión)."""
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        emp_id = session.get("empresa_id", 1)
        suc_u = session.get("sucursal_id")
        suc_f = int(suc_u) if suc_u is not None and str(suc_u).strip().isdigit() else None
        res = productos_repo.listar_catalogo_pos_modal(cur, emp_id, sucursal_id_usuario=suc_f, limit=800)
        productos = [_fila_a_producto_pos_json(cur, row, emp_id) for row in res]
        return jsonify({"productos": productos, "empresa_id": emp_id})
    finally:
        cur.close()
        conn.close()


@bp.route("/buscar_por_nombre")
@rol_requerido("GERENTE", "CAJERO")
def buscar_por_nombre():
    q = request.args.get("q", "").upper()
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        emp_id = session.get("empresa_id", 1)
        suc_u = session.get("sucursal_id")
        suc_f = int(suc_u) if suc_u is not None and str(suc_u).strip().isdigit() else None
        res = productos_repo.buscar_por_nombre(cur, q, limit=10, empresa_id=emp_id, sucursal_id_usuario=suc_f) or []
        productos = []
        for r in res:
            promo_tipo = (r[4] or "").strip().upper() if len(r) > 4 else ""
            promo_val = float(r[5]) if len(r) > 5 and r[5] else 0
            promo_vc, promo_vp, promo_dm = 2, 1, None
            try:
                promo_activa = promociones_repo.get_promocion_activa_producto(cur, r[0], emp_id, date.today())
                if promo_activa:
                    promo_tipo, promo_val = promo_activa[0], float(promo_activa[1] or 0)
                    if len(promo_activa) > 4:
                        promo_vc = float(promo_activa[2] or 2)
                        promo_vp = float(promo_activa[3] or 1)
                        promo_dm = float(promo_activa[4]) if promo_activa[4] is not None else None
                    if promo_tipo == "DESCUENTO_CANTIDAD" and len(promo_activa) > 6 and promo_activa[6] is not None:
                        promo_vc = float(promo_activa[6])
            except Exception:
                pass
            if promo_tipo not in ("2X1", "3X2", "PORCENTAJE", "DESCUENTO_MONTO", "VOLUMEN", "REGALO", "PRECIO_FIJO", "DESCUENTO_CANTIDAD"):
                promo_tipo = ""
            fracc = bool(r[6]) if len(r) > 6 else False
            uxcaja = int(r[7]) if len(r) > 7 and r[7] is not None else None
            uxdoc = int(r[8]) if len(r) > 8 and r[8] is not None else 12
            mh = normalizar_codigo_mh(str(r[9]) if len(r) > 9 else None)
            nom_prod = str(r[1] or "").strip() if len(r) > 1 else None
            pres = presentaciones_repo.lista_para_pos_json(cur, int(r[0]), uxdoc, uxcaja, nombre_producto=nom_prod)
            ex_n = float(r[10]) if len(r) > 10 and r[10] is not None else 0.0
            productos.append({
                "id": r[0], "nombre": r[1], "precio": float(r[2]), "codigo": (r[3] or "").strip(),
                "promocion_tipo": promo_tipo, "promocion_valor": promo_val,
                "promocion_valor_comprar": promo_vc, "promocion_valor_pagar": promo_vp, "promocion_descuento_monto": promo_dm,
                "fraccionable": fracc, "unidades_por_caja": uxcaja, "unidades_por_docena": uxdoc, "mh_codigo_unidad": mh,
                "presentaciones": pres,
                "existencia": ex_n,
            })
        return jsonify(productos)
    finally:
        cur.close()
        conn.close()


@bp.route("/guardar_venta", methods=["POST"])
@rol_requerido("GERENTE", "CAJERO", "BODEGUERO")
def guardar_venta():
    datos = request.get_json() or {}
    carrito = datos.get("carrito", [])
    usuario_id = int(session["user_id"])
    pago = datos.get("tipo_pago", "EFECTIVO")
    descuento_pct = datos.get("descuento_pct")
    descuento_monto = datos.get("descuento_monto")
    tipo_comp = (datos.get("tipo_comprobante") or "TICKET").strip().upper()
    if tipo_comp not in ("TICKET", "FACTURA", "CREDITO_FISCAL"):
        tipo_comp = "TICKET"
    cliente_id = _parse_cliente_id(datos.get("cliente_id"))
    cliente = (datos.get("cliente_nombre") or "").strip() or "Consumidor Final"
    if tipo_comp == "TICKET" and not cliente_id:
        cliente = (os.environ.get("POSAGIL_NOMBRE_CF_TICKET") or "Cliente de contado").strip() or "Cliente de contado"

    if not carrito:
        return jsonify({"status": "error", "msg": "Carrito vacío"})

    db = ConexionDB()
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()

        emp_id = session.get("empresa_id", 1)
        if tipo_comp == "FACTURA" and not cliente_id:
            return jsonify(
                {
                    "status": "error",
                    "msg": "Factura: debe buscar y elegir un cliente del catálogo (no basta con escribir el nombre).",
                }
            )
        if tipo_comp == "CREDITO_FISCAL":
            if not cliente_id:
                return jsonify(
                    {"status": "error", "msg": "Crédito fiscal: busque y seleccione un cliente del catálogo."}
                )
            cur.execute(
                "SELECT COALESCE(es_contribuyente, FALSE) FROM clientes WHERE id = %s AND empresa_id = %s",
                (cliente_id, emp_id),
            )
            row_cf = cur.fetchone()
            if not row_cf or not row_cf[0]:
                return jsonify(
                    {
                        "status": "error",
                        "msg": "Crédito fiscal: el cliente debe estar marcado como contribuyente en Clientes.",
                    }
                )

        total_bruto, lineas = crear_venta_desde_carrito(cur, carrito, empresa_id=emp_id)
        descuento_aplicado, total_neto = aplicar_descuento(total_bruto, descuento_pct, descuento_monto)
        if descuento_aplicado > total_bruto:
            descuento_aplicado = total_bruto
        if total_neto < 0:
            total_neto = 0.0
        raw_umbral = (os.environ.get("POSAGIL_MONTO_EXIGE_DOC_CF_USD") or "").strip()
        if tipo_comp == "TICKET" and raw_umbral and not cliente_id:
            try:
                umbral_cf = float(raw_umbral.replace(",", "."))
            except ValueError:
                umbral_cf = 0.0
            if umbral_cf > 0 and float(total_neto) > umbral_cf:
                return jsonify(
                    {
                        "status": "error",
                        "msg": (
                            f"Ticket con total mayor a ${umbral_cf:,.2f}: puede requerirse identificación del comprador "
                            "ante el MH. Seleccione un cliente del catálogo (con DUI/NIT)."
                        ),
                    }
                )
        rol = (session.get("rol") or "").strip().upper()
        LIMITE_DESC_CAJERO = 5.0
        if rol in ("CAJERO", "BODEGUERO") and total_bruto > 0 and descuento_aplicado > 0:
            pct_desc = 100.0 * descuento_aplicado / total_bruto
            if pct_desc > LIMITE_DESC_CAJERO:
                sup_user = (datos.get("supervisor_user") or "").strip()
                sup_pass = datos.get("supervisor_password") or ""
                if not sup_user or not sup_pass:
                    return jsonify({
                        "status": "error",
                        "msg": f"Descuento mayor al {int(LIMITE_DESC_CAJERO)}% requiere autorización de Gerente. Ingrese usuario y contraseña.",
                    })
                u = usuarios_repo.get_usuario_login(cur, sup_user)
                if not u:
                    return jsonify({"status": "error", "msg": "Usuario o contraseña de gerente incorrectos."})
                u_rol = (u[3] or "").strip().upper() if len(u) > 3 else ""
                if u_rol not in ("GERENTE", "ADMIN", "SUPERADMIN"):
                    return jsonify({"status": "error", "msg": "Solo Gerente o Administrador puede autorizar descuentos mayores."})
                if not verificar_password(u[2], sup_pass):
                    return jsonify({"status": "error", "msg": "Usuario o contraseña de gerente incorrectos."})
        if cliente_id:
            snap = clientes_repo.snapshot_cliente_venta_por_id(cur, cliente_id, emp_id)
            if snap:
                cliente = snap
        suc_id = session.get("sucursal_id")
        emitir_contingencia = bool(datos.get("emitir_contingencia"))
        causa_contingencia = int(datos.get("causa_contingencia") or 1) if datos.get("causa_contingencia") else 1

        # Contingencia DTE: la resolución queda en AgilDTE (respuesta /api/pos/procesar-venta/), no pre-chequeo local al MH.

        venta_id = persistir_venta(
            cur,
            usuario_id,
            cliente,
            pago,
            total_neto,
            lineas,
            empresa_id=emp_id,
            sucursal_id=suc_id,
            tipo_comprobante=tipo_comp,
            cliente_id=cliente_id,
            descuento=descuento_aplicado,
            total_bruto=total_bruto,
            emitir_contingencia=emitir_contingencia,
            causa_contingencia=causa_contingencia if emitir_contingencia else None,
        )
        # No leer cliente aquí: get_cliente() hace rollback() en except y tumbaría TODA la venta
        # antes del commit (el POS recibía venta_id pero la fila nunca existía).
        registrar_accion(
            cur,
            historial_usuarios_repo.EVENTO_VENTA_CREADA,
            f"Venta #{venta_id}. Total ${total_neto:,.2f}",
        )
        conn.commit()

        cur.execute("SELECT 1 FROM ventas WHERE id = %s", (venta_id,))
        if cur.fetchone() is None:
            current_app.logger.error("guardar_venta: venta_id=%s no existe tras commit", venta_id)
            return (
                jsonify(
                    {
                        "status": "error",
                        "msg": "Error grave: la venta no quedó en la base de datos. No repita el cobro sin revisar reportes.",
                    }
                ),
                500,
            )

        agildte_sync = intentar_sync_venta_si_habilitado(
            cur=cur,
            empresa_id_local=int(emp_id),
            venta_id_local=int(venta_id),
            tipo_comprobante=tipo_comp,
            tipo_pago=str(pago or "EFECTIVO"),
            lineas=lineas,
            total_neto=float(total_neto),
            total_bruto=float(total_bruto),
            descuento=float(descuento_aplicado),
            cliente_id=cliente_id,
            cliente_nombre_ticket=str(cliente or "Consumidor Final"),
        )
        if agildte_sync is not None and not agildte_sync.get("ok"):
            current_app.logger.warning("AgilDTE sync venta #%s: %s", venta_id, agildte_sync)

        if agildte_sync is not None and agildte_sync.get("dte_persistido"):
            try:
                conn.commit()
            except Exception:
                current_app.logger.exception("No se pudo confirmar en BD los datos DTE devueltos por AgilDTE")

        telefono_whatsapp = None
        if cliente_id:
            try:
                cl_wa = clientes_repo.get_cliente(cur, cliente_id)
                if cl_wa and len(cl_wa) > 10:
                    telefono_whatsapp = (cl_wa[10] or "").strip()
            except Exception:
                pass

        raw_ew = datos.get("enviar_whatsapp")
        if raw_ew is None:
            enviar_wa = True
        elif isinstance(raw_ew, str):
            enviar_wa = raw_ew.strip().lower() in ("1", "true", "yes", "on")
        else:
            enviar_wa = bool(raw_ew)

        whatsapp_info = None
        if not enviar_wa:
            whatsapp_info = {
                "ok": False,
                "motivo": "opcion_desactivada",
                "detalle": "El envío por WhatsApp estaba desmarcado.",
                "wa_me_url": None,
                "twilio_enviado": False,
            }
        else:
            puede_wa_tipo = tipo_comp in ("FACTURA", "CREDITO_FISCAL") or (tipo_comp == "TICKET" and cliente_id)
            if not puede_wa_tipo:
                whatsapp_info = {
                    "ok": False,
                    "motivo": "tipo_sin_whatsapp",
                    "detalle": "WhatsApp solo aplica a Factura, Crédito fiscal o Ticket con cliente elegido del catálogo.",
                    "wa_me_url": None,
                    "twilio_enviado": False,
                }
            elif not telefono_whatsapp:
                whatsapp_info = {
                    "ok": False,
                    "motivo": "sin_telefono",
                    "detalle": "El cliente no tiene teléfono en ficha. Actualícelo en Clientes para poder enviar el comprobante.",
                    "wa_me_url": None,
                    "twilio_enviado": False,
                }
            else:
                nombre_neg = ""
                try:
                    emp_row = empresas_repo.get_empresa(cur, emp_id)
                    if emp_row and len(emp_row) > 1:
                        nombre_neg = (emp_row[1] or "").strip()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                try:
                    whatsapp_info = preparar_envio_whatsapp_venta(
                        cur,
                        venta_id,
                        emp_id,
                        telefono_whatsapp,
                        tipo_comp,
                        request.url_root.rstrip("/"),
                        current_app.secret_key,
                        nombre_neg,
                    )
                except Exception as ex:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    whatsapp_info = {
                        "ok": False,
                        "motivo": "error_preparacion",
                        "detalle": str(ex),
                        "wa_me_url": None,
                        "twilio_enviado": False,
                    }

        payload = {
            "status": "ok",
            "venta_id": venta_id,
            "total_bruto": total_bruto,
            "descuento": descuento_aplicado,
            "total": total_neto,
            "whatsapp": whatsapp_info,
        }
        if agildte_sync is not None:
            payload["agildte_sync"] = agildte_sync
        return jsonify(payload)
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return jsonify({"status": "error", "msg": str(e)})
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _texto_sello_recepcion(
    estado_dte: str,
    sello_recepcion: str,
    *,
    codigo_generacion: str = "",
    numero_control: str = "",
) -> str:
    """Texto del sello en ticket. Si AgilDTE ya asignó código/número control, no mostrar «solo respaldo local».
    AceptadoMH sin sello en BD (sincro incompleto) tampoco debe leerse como documento no transmitido."""
    ed = (estado_dte or "").strip().upper()
    sello = (sello_recepcion or "").strip()
    tiene_oficial = bool((codigo_generacion or "").strip() or (numero_control or "").strip())

    if sello and ed in ("TRANSMITIDO", "ACEPTADOMH"):
        return sello
    if ed in ("RECHAZADO", "RECHAZADOMH"):
        return "Rechazado por MH — Ver mensaje de error"
    if ed == "CONTINGENCIA" or "CONTINGENCIA" in ed:
        return "Emitido en contingencia — Pendiente de transmisión al MH"
    if sello:
        return sello
    if ed == "ACEPTADOMH" and not sello:
        return (
            "Aceptado por MH — DTE con validez tributaria. "
            "Use consulta pública o AgilDTE si el sello aún no figura en este comprobante."
        )
    if tiene_oficial and ed in (
        "GENERADO",
        "ENVIADO",
        "PENDIENTEENVIO",
        "BORRADOR",
        "ERRORENVIO",
    ):
        etiqueta = (estado_dte or "").strip() or "—"
        return (
            f"DTE registrado en AgilDTE — Estado: {etiqueta}. "
            "Transmisión/registro en MH puede estar en proceso o asíncrono."
        )
    if tiene_oficial:
        etiqueta = (estado_dte or "").strip() or "—"
        return (
            f"DTE electrónico (código y número control asignados por AgilDTE/MH). Estado: {etiqueta}. "
            "Use la consulta pública MH con el código de generación para validar."
        )
    return "Documento de respaldo — sin transmisión electrónica al MH"


def _resolver_empresa_emisor_comprobante(
    cur, empresa_id_preferida: int, venta_id: int, empresa_fallback_sesion: int | None
):
    """
    Fila de empresa para ticket/factura. Evita 404 si ventas.empresa_id apunta a id inexistente
    o si hay que usar la empresa de la sesión como respaldo.
    """
    for eid in (empresa_id_preferida, empresa_fallback_sesion):
        if eid is None:
            continue
        row = empresas_repo.get_empresa(cur, int(eid))
        if row:
            return row
    try:
        cur.execute("SELECT empresa_id FROM ventas WHERE id = %s", (venta_id,))
        vr = cur.fetchone()
        if vr and vr[0] is not None:
            row = empresas_repo.get_empresa(cur, int(vr[0]))
            if row:
                return row
    except Exception:
        pass
    try:
        cur.execute("SELECT MIN(id) FROM empresas")
        mr = cur.fetchone()
        if mr and mr[0] is not None:
            return empresas_repo.get_empresa(cur, int(mr[0]))
    except Exception:
        pass
    return None


def _fecha_emision_iso_venta(cur, venta_id: int) -> str | None:
    """Fecha de emisión (YYYY-MM-DD) para parámetro fechaEmi en consulta pública MH / QR."""
    try:
        cur.execute("SELECT fecha_registro::date FROM ventas WHERE id = %s", (venta_id,))
        r = cur.fetchone()
        if r and r[0] is not None:
            fd = r[0]
            if hasattr(fd, "isoformat"):
                return fd.isoformat()[:10]
            return str(fd)[:10]
    except Exception:
        pass
    return None


def _tpl_comprobante_venta(
    cur,
    venta_id: int,
    empresa_id: int,
    formato: str,
    copias: int,
    empresa_fallback_sesion: int | None = None,
) -> tuple[str | None, dict | None]:
    """Retorna (nombre_plantilla, contexto) o (None, None) si no existe.
    empresa_id es la empresa del emisor (datos fiscales); la venta se carga por id sin filtrar por sesión."""
    venta = ventas_repo.get_venta(cur, venta_id, empresa_id=None)
    if not venta:
        return None, None
    detalles = ventas_repo.get_detalles(cur, venta_id) or []
    empresa = _resolver_empresa_emisor_comprobante(cur, empresa_id, venta_id, empresa_fallback_sesion)
    if not empresa:
        return None, None
    fecha_emi = _fecha_emision_iso_venta(cur, venta_id)
    tcomp = str(venta[4] or "TICKET").strip().upper() if len(venta) > 4 else "TICKET"
    copias = min(max(int(copias or 1), 1), 3)
    codigo_gen = (venta[14] or "").strip() if len(venta) > 14 else ""
    numero_ctrl = (venta[15] or "").strip() if len(venta) > 15 else ""
    sello_rec = (venta[16] or "").strip() if len(venta) > 16 else ""
    estado_dte = (venta[17] or "RESPALDO").strip() if len(venta) > 17 else "RESPALDO"
    if tcomp in ("FACTURA", "CREDITO_FISCAL"):
        receptor = {
            "nombre": (venta[8] if len(venta) > 8 and venta[8] else venta[3]) or "Consumidor Final",
            "documento": (venta[6] or "") if len(venta) > 6 else "",
            "tipo_documento": (venta[7] or "NIT").strip() if len(venta) > 7 and venta[7] else "NIT",
            "nrc": "",
            "actividad": "",
            "direccion": "",
            "telefono": "",
            "correo": "",
            "nombre_comercial": "",
        }
        if venta[5]:
            cl = clientes_repo.get_cliente(cur, venta[5])
            if cl:
                cod_act = (cl[11] if len(cl) > 11 else cl[10] if len(cl) > 10 else "") or ""
                cod_act = str(cod_act).strip() if cod_act else ""
                act_desc = ""
                if cod_act:
                    try:
                        act_desc = actividades_repo.get_descripcion_por_codigo(cur, cod_act) or ""
                    except Exception:
                        pass
                direccion_val = (cl[9] or "") if len(cl) > 9 else ""
                telefono_val = (cl[10] or "") if len(cl) > 10 else ""
                receptor = {
                    "nombre": (cl[3] or "").strip() or "Consumidor Final",
                    "documento": (cl[5] or "").strip(),
                    "tipo_documento": (cl[4] or "NIT").strip() or "NIT",
                    "nrc": "",
                    "actividad": act_desc,
                    "direccion": str(direccion_val).strip() if direccion_val is not None else "",
                    "telefono": str(telefono_val).strip() if telefono_val is not None else "",
                    "correo": (cl[6] or "").strip(),
                    "nombre_comercial": (cl[3] or "").strip(),
                }
        total = float(venta[2])
        retencion_iva = float(venta[11]) if len(venta) > 11 else 0
        descuento = float(venta[12]) if len(venta) > 12 else 0
        total_bruto = float(venta[13]) if len(venta) > 13 else total
        total_a_pagar = total - retencion_iva
        sello_texto = _texto_sello_recepcion(
            estado_dte,
            sello_rec,
            codigo_generacion=codigo_gen,
            numero_control=numero_ctrl,
        )
        qr_b64 = (
            generar_qr_dte_base64(codigo_gen, tamano=8, fecha_emi=fecha_emi) if codigo_gen else None
        )
        consulta_url = url_consulta_publica_dte(codigo_gen, fecha_emi) if codigo_gen else None
        empresa_fiscal = _empresa_fiscal_por_fila(empresa)
        ctx = {
            "venta": venta,
            "detalles": detalles,
            "empresa": empresa,
            "empresa_fiscal": empresa_fiscal,
            "emisor": _emisor_desde_empresa(empresa),
            "receptor": receptor,
            "codigo_generacion": codigo_gen or "—",
            "numero_control": numero_ctrl or "—",
            "valor_letras": numero_a_letras_dolares(total_a_pagar if retencion_iva > 0 else total),
            "descuento": descuento,
            "total_bruto": total_bruto,
            "copias": copias,
            "sello_recepcion_texto": sello_texto,
            "qr_base64": qr_b64,
            "consulta_dte_url": consulta_url,
            "fecha_emision_dte": fecha_emi,
            "estado_dte": estado_dte,
        }
        if formato == "ticket":
            ctx["retencion_iva"] = retencion_iva
            ctx["total_a_pagar"] = total_a_pagar
            return "ticket_dte_print.html", ctx
        return "comprobante_sv_print.html", ctx
    ctx_ticket: dict = {"venta": venta, "detalles": detalles, "empresa": empresa, "copias": copias}
    codigo_gen_t = (venta[14] or "").strip() if len(venta) > 14 else ""
    numero_ctrl_t = (venta[15] or "").strip() if len(venta) > 15 else ""
    sello_rec_t = (venta[16] or "").strip() if len(venta) > 16 else ""
    estado_dte_t = (venta[17] or "RESPALDO").strip() if len(venta) > 17 else "RESPALDO"
    consulta_ticket = None
    qr_ticket = None
    if codigo_gen_t:
        consulta_ticket = url_consulta_publica_dte(codigo_gen_t, fecha_emi)
        qr_ticket = generar_qr_dte_base64(codigo_gen_t, tamano=8, fecha_emi=fecha_emi)
    ctx_ticket["empresa_fiscal"] = _empresa_fiscal_por_fila(empresa)
    if codigo_gen_t or numero_ctrl_t or sello_rec_t:
        ctx_ticket["codigo_generacion"] = codigo_gen_t or "—"
        ctx_ticket["numero_control"] = numero_ctrl_t or "—"
        ctx_ticket["sello_recepcion_texto"] = _texto_sello_recepcion(
            estado_dte_t,
            sello_rec_t,
            codigo_generacion=codigo_gen_t,
            numero_control=numero_ctrl_t,
        )
        ctx_ticket["estado_dte"] = estado_dte_t
        ctx_ticket["qr_base64"] = qr_ticket
        ctx_ticket["consulta_dte_url"] = consulta_ticket
        ctx_ticket["fecha_emision_dte"] = fecha_emi
    return "ticket_print.html", ctx_ticket


@bp.route("/imprimir_ticket/<int:venta_id>")
@rol_requerido("GERENTE", "CAJERO")
def imprimir_ticket(venta_id: int):
    sess_emp = int(session.get("empresa_id") or 1)
    formato = (request.args.get("formato") or "").strip().lower()
    copias = int(request.args.get("copias", 1) or 1)
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        existe, venta_emp = ventas_repo.venta_existe_y_empresa_id(cur, venta_id)
        if not existe:
            return (
                f"No se encontró la venta #{venta_id}. No hay ningún registro con ese id en la base de datos "
                f"(enlace antiguo, venta anulada o, si ocurría un error al guardar, la transacción pudo no haberse confirmado).",
                404,
            )
        rol = (session.get("rol") or "").strip().upper()
        puede_otra_empresa = rol in ("ADMIN", "SUPERADMIN")
        if venta_emp is not None and venta_emp != sess_emp and not puede_otra_empresa:
            return "No tiene permiso para imprimir este comprobante.", 403
        emp_ctx = venta_emp if venta_emp is not None else sess_emp
        tpl, ctx = _tpl_comprobante_venta(
            cur, venta_id, emp_ctx, formato, copias, empresa_fallback_sesion=sess_emp
        )
        if not tpl:
            if not ventas_repo.get_venta(cur, venta_id, empresa_id=None):
                return "Ticket no encontrado (la venta no existe).", 404
            return (
                "No se pudo cargar la empresa emisora. Revise que exista la empresa en "
                "Configuración y que la venta tenga empresa_id correcto.",
                503,
            )
        return render_template(tpl, **ctx)
    finally:
        cur.close()
        conn.close()


@bp.route("/publico/comprobante/<int:venta_id>")
def publico_comprobante_venta(venta_id: int):
    """Comprobante imprimible con token firmado (enlace WhatsApp). Sin sesión."""
    from azdigital.utils.ticket_publico_token import verificar_acceso_publico_venta

    token = (request.args.get("t") or "").strip()
    data = verificar_acceso_publico_venta(current_app.secret_key, token)
    if not data:
        return "Enlace inválido o vencido.", 403
    vid, eid = data
    if vid != venta_id:
        return "Enlace no válido.", 403
    formato = (request.args.get("formato") or "").strip().lower()
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        tpl, ctx = _tpl_comprobante_venta(
            cur, venta_id, eid, formato, 1, empresa_fallback_sesion=eid
        )
        if not tpl:
            if not ventas_repo.get_venta(cur, venta_id, empresa_id=None):
                return "Comprobante no encontrado.", 404
            return "No se pudo cargar datos del emisor para este comprobante.", 503
        return render_template(tpl, **ctx)
    finally:
        cur.close()
        conn.close()


@bp.route("/publico/dte_json/<int:venta_id>")
def publico_dte_json_venta(venta_id: int):
    """JSON estructura MH (orientativa) con token firmado."""
    from azdigital.services.dte_json_venta_mh import construir_json_dte_mh_venta
    from azdigital.utils.ticket_publico_token import verificar_acceso_publico_venta

    token = (request.args.get("t") or "").strip()
    data = verificar_acceso_publico_venta(current_app.secret_key, token)
    if not data:
        return jsonify({"error": "Enlace inválido o vencido"}), 403
    vid, eid = data
    if vid != venta_id:
        return jsonify({"error": "Enlace no válido"}), 403
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        payload = construir_json_dte_mh_venta(cur, venta_id, eid)
        if not payload:
            return jsonify({"error": "No encontrado"}), 404
        return jsonify(payload)
    finally:
        cur.close()
        conn.close()


def _sucursal_session_int() -> int | None:
    suc_u = session.get("sucursal_id")
    try:
        return int(suc_u) if suc_u is not None and str(suc_u).strip().isdigit() else None
    except (TypeError, ValueError):
        return None


@bp.route("/pos/favoritos", methods=["GET"])
@rol_requerido("GERENTE", "CAJERO", "BODEGUERO")
def pos_favoritos_get():
    """Favoritos del POS compartidos por empresa + sucursal (sesión)."""
    emp_id = int(session.get("empresa_id") or 1)
    suc_id = _sucursal_session_int()
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        if not pos_favoritos_repo.tabla_existe(cur):
            return jsonify({"ok": True, "favoritos": [], "sync": False, "motivo": "tabla_pendiente"})
        favs = pos_favoritos_repo.obtener_favoritos_lista(cur, emp_id, suc_id)
        return jsonify(
            {
                "ok": True,
                "favoritos": favs,
                "sync": True,
                "sucursal_key": pos_favoritos_repo.sucursal_key(suc_id),
            }
        )
    finally:
        cur.close()
        conn.close()


@bp.route("/pos/favoritos", methods=["POST"])
@rol_requerido("GERENTE", "CAJERO", "BODEGUERO")
def pos_favoritos_post():
    emp_id = int(session.get("empresa_id") or 1)
    suc_id = _sucursal_session_int()
    uid = session.get("user_id")
    datos = request.get_json(silent=True) or {}
    items = datos.get("favoritos")
    if items is None:
        items = []
    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        if not pos_favoritos_repo.tabla_existe(cur):
            return jsonify({"ok": False, "msg": "Ejecute: python scripts/alter_pos_favoritos_sucursal.py", "favoritos": []}), 503
        limpio, err = pos_favoritos_repo.guardar_favoritos_lista(cur, emp_id, suc_id, items, uid)
        if err:
            return jsonify({"ok": False, "msg": err, "favoritos": limpio}), 400
        conn.commit()
        return jsonify(
            {
                "ok": True,
                "favoritos": limpio,
                "sucursal_key": pos_favoritos_repo.sucursal_key(suc_id),
            }
        )
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "msg": str(e), "favoritos": []}), 500
    finally:
        cur.close()
        conn.close()

