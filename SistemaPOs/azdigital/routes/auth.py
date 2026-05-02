# Programador: Oscar Amaya Romero
from __future__ import annotations

import os
import time

import psycopg2
import httpx
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from azdigital.decorators import login_required
from azdigital.services.auth_service import verificar_password
from azdigital.integration.agildte_client import resolve_agildte_base_url
from database import ConexionDB
from azdigital.repositories import historial_usuarios_repo, usuarios_repo

bp = Blueprint("auth", __name__)


def _allow_local_login() -> bool:
    v = (os.environ.get("POSAGIL_ALLOW_LOCAL_LOGIN") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _portal_login_url() -> str:
    return (os.environ.get("AGILDTE_PORTAL_LOGIN_URL") or os.environ.get("AZ_AGILDTE_PORTAL_LOGIN_URL") or "").strip()


def _redirect_after_logout():
    if not _allow_local_login():
        p = _portal_login_url()
        if p:
            return redirect(p)
    return redirect(url_for("auth.login"))


def _bootstrap_session_from_row(db: ConexionDB, u: tuple) -> None:
    user_id, username, _password_hash, rol, sucursal_id, empresa_id = u[:6]
    session.clear()
    session["user_id"] = user_id
    session["username"] = (username or "").strip()
    session["rol"] = str(rol).strip().upper()
    session["sucursal_id"] = sucursal_id
    session["empresa_id"] = int(empresa_id) if empresa_id else 1
    try:
        from azdigital.repositories import empresas_repo
        conn2 = psycopg2.connect(**db.config)
        cur2 = conn2.cursor()
        emp = empresas_repo.get_empresa(cur2, session["empresa_id"])
        session["empresa_nombre"] = (emp[1] or emp[9] or "Empresa") if emp and len(emp) > 9 else "Empresa"
        cur2.close()
        conn2.close()
    except Exception:
        session["empresa_nombre"] = "Empresa"


def _registrar_historial(evento: str, usuario_id=None, username=None, detalle=None):
    """Registra evento en historial. No falla si la tabla no existe."""
    try:
        db = ConexionDB()
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        ip = request.remote_addr if request else None
        ua = (request.user_agent.string[:500] if request and request.user_agent else None)
        historial_usuarios_repo.registrar(
            cur, evento,
            usuario_id=usuario_id, username=username, detalle=detalle,
            ip_address=ip, user_agent=ua,
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


@bp.route("/auth/agildte", methods=["GET"])
def auth_agildte():
    """SSO: valida JWT con /api/auth/me/, crea empresa/usuario local si faltan (lista única = AgilDTE) y abre sesión."""
    token = (request.args.get("access_token") or request.args.get("token") or "").strip()
    if not token:
        flash("Falta el token de AgilDTE. Abra el POS desde el portal (Abrir Pos Agil).", "danger")
        return redirect(url_for("auth.login"))
    base = resolve_agildte_base_url()
    if not base:
        flash("Falta AGILDTE_BASE_URL en el servidor PosAgil.", "danger")
        return redirect(url_for("auth.login"))
    try:
        r = httpx.get(
            f"{base.rstrip('/')}/api/auth/me/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20.0,
        )
    except Exception as exc:
        hint = (
            " Revise AGILDTE_BASE_URL en Docker: debe ser alcanzable desde el contenedor PosAgil "
            "(p. ej. http://backend:8000 si el API es el servicio «backend» en la red agildte_net, "
            "o http://host.docker.internal:8000 si Django corre en el host). "
            "Red: docker network create agildte_net; el backend debe estar conectado a esa red."
        )
        flash(f"No se pudo contactar AgilDTE: {exc}.{hint}", "danger")
        return redirect(url_for("auth.login"))
    if r.status_code != 200:
        flash("Sesión AgilDTE inválida o expirada. Vuelva a iniciar sesión en el portal.", "danger")
        return redirect(url_for("auth.login"))
    try:
        data = r.json() if r.content else {}
    except Exception:
        data = {}
    udj = data.get("user") or {}
    username = (udj.get("username") or "").strip()
    if not username:
        flash("Respuesta de AgilDTE sin usuario.", "danger")
        return redirect(url_for("auth.login"))

    db = ConexionDB()
    conn = None
    try:
        from azdigital.integration.agildte_sso_provision import provision_if_missing

        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        ok, err = provision_if_missing(cur, data)
        if not ok:
            conn.rollback()
            cur.close()
            conn.close()
            flash(err or "No se pudo preparar el usuario en PosAgil.", "danger")
            return redirect(url_for("auth.login"))
        conn.commit()
        u = usuarios_repo.get_usuario_login(cur, username)
        cur.close()
        conn.close()
        conn = None
    except Exception as e:
        if conn:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
        msg = str(e)
        hint = ""
        if "does not exist" in msg and "relation" in msg:
            hint = " Ejecute en el servidor: python scripts/bootstrap_bd.py (crea tablas empresas/usuarios)."
        elif "Connection refused" in msg and ("127.0.0.1" in msg or "localhost" in msg):
            hint = (
                " Si PosAgil corre en Docker, no use AZ_DB_HOST=127.0.0.1 dentro del contenedor; "
                "en docker-compose debe ser host.docker.internal (o el nombre del servicio Postgres)."
            )
        flash(f"Error de base de datos: {msg}{hint}", "danger")
        return redirect(url_for("auth.login"))

    if not u:
        flash(
            "No se pudo cargar el usuario en PosAgil tras el registro automático. "
            "Verifique que el nombre de usuario coincida con AgilDTE.",
            "danger",
        )
        return redirect(url_for("auth.login"))

    _registrar_historial(
        historial_usuarios_repo.EVENTO_LOGIN_OK,
        usuario_id=u[0],
        username=u[1],
        detalle="SSO AgilDTE",
    )
    _bootstrap_session_from_row(db, u)
    # En el momento de «Abrir PosAgil»: rol y empresa desde /api/auth/me/ (fuente de verdad), no solo la fila leída.
    from azdigital.integration.agildte_sso_provision import extract_me_context, map_agildte_role_to_pos_rol

    _uname, emp_me, _nombre_emp, _api_role = extract_me_context(data)
    pos_rol_entrada = map_agildte_role_to_pos_rol(
        udj.get("role"), is_superuser=bool(udj.get("is_superuser"))
    )
    session["rol"] = pos_rol_entrada
    if emp_me is not None:
        try:
            session["empresa_id"] = int(emp_me)
        except (TypeError, ValueError):
            pass
    # Tras session.clear() en bootstrap: guardar JWT para resincronizar rol más tarde si cambia en AgilDTE.
    session["agildte_access_token"] = token
    session["_agildte_role_sync_ts"] = time.time()
    return redirect(url_for("core.index"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if _allow_local_login():
            return render_template("login.html")
        return render_template("login_portal_only.html", portal_url=_portal_login_url())

    if request.method == "POST":
        if not _allow_local_login():
            flash("El acceso con usuario y contraseña está deshabilitado. Use AgilDTE.", "danger")
            return redirect(url_for("auth.login"))

        user_in = request.form.get("usuario", "").strip()
        pass_in = request.form.get("password", "").strip()

        db = ConexionDB()
        conn = None
        try:
            conn = psycopg2.connect(**db.config)
            cur = conn.cursor()
            u = usuarios_repo.get_usuario_login(cur, user_in)
            cur.close()
            conn.close()
        except Exception as e:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            try:
                msg = str(e)
            except Exception:
                msg = repr(e)
            return render_template("login.html", error=f"Error conectando a la base de datos: {msg}")

        if not u:
            _registrar_historial(
                historial_usuarios_repo.EVENTO_LOGIN_FALLO,
                username=user_in,
                detalle="Usuario no encontrado",
            )
            return render_template("login.html", error="Usuario o clave incorrectos")

        user_id, username, password_hash, rol, sucursal_id, empresa_id = u[:6]
        if not verificar_password(password_hash, pass_in):
            _registrar_historial(
                historial_usuarios_repo.EVENTO_LOGIN_FALLO,
                usuario_id=user_id,
                username=username,
                detalle="Contraseña incorrecta",
            )
            return render_template("login.html", error="Usuario o clave incorrectos")

        _registrar_historial(
            historial_usuarios_repo.EVENTO_LOGIN_OK,
            usuario_id=user_id,
            username=username,
        )
        _bootstrap_session_from_row(db, u)
        # Misma clave que en AgilDTE → JWT en sesión (sync DTE sin AGILDTE_USERNAME en Docker).
        try:
            from azdigital.integration.agildte_client import try_agildte_login_into_session

            try_agildte_login_into_session(session, str(username), pass_in)
        except Exception:
            pass
        return redirect(url_for("core.index"))


@bp.route("/logout")
def logout():
    uid = session.get("user_id")
    uname = session.get("username")
    if uid or uname:
        _registrar_historial(
            historial_usuarios_repo.EVENTO_LOGOUT,
            usuario_id=uid,
            username=uname,
        )
    session.clear()
    return _redirect_after_logout()


@bp.route("/cambiar_password", methods=["GET", "POST"])
@login_required
def cambiar_password():
    if request.method == "POST":
        actual = (request.form.get("password_actual") or "").strip()
        nueva = (request.form.get("password_nueva") or "").strip()
        confirmar = (request.form.get("password_confirmar") or "").strip()
        if not actual or not nueva or not confirmar:
            return render_template("cambiar_password.html", error="Complete todos los campos.")
        if nueva != confirmar:
            return render_template("cambiar_password.html", error="La nueva contraseña no coincide.")
        if len(nueva) < 4:
            return render_template("cambiar_password.html", error="La contraseña debe tener al menos 4 caracteres.")
        db = ConexionDB()
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        try:
            u = usuarios_repo.get_usuario_login(cur, session.get("username", ""))
            if not u:
                return render_template("cambiar_password.html", error="Usuario no encontrado.")
            if not verificar_password(u[2], actual):
                return render_template("cambiar_password.html", error="Contraseña actual incorrecta.")
            usuarios_repo.actualizar_password(cur, session["user_id"], generate_password_hash(nueva))
            conn.commit()
            _registrar_historial(
                historial_usuarios_repo.EVENTO_CAMBIO_PASSWORD,
                usuario_id=session["user_id"],
                username=session.get("username"),
                detalle="Contraseña cambiada",
            )
            flash("Contraseña actualizada correctamente.", "success")
            return redirect(url_for("core.index"))
        finally:
            cur.close()
            conn.close()
    return render_template("cambiar_password.html")
