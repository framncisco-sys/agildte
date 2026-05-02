# Programador: Oscar Amaya Romero
import os

from flask import Flask, request, session
from werkzeug.middleware.proxy_fix import ProxyFix

from azdigital.routes.admin import bp as admin_bp
from azdigital.routes.auth import bp as auth_bp
from azdigital.routes.core import bp as core_bp
from azdigital.routes.pos import bp as pos_bp
from azdigital.utils.env_config import get_public_base_url, is_production_mode, trust_proxy
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.exceptions import InternalServerError


def _load_dotenv(path: str = ".env") -> None:
    """
    Carga variables desde un archivo .env simple (KEY=VALUE).
    Solo setea variables que no existan ya en el entorno.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f.readlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if not k:
                    continue
                if k not in os.environ or os.environ.get(k, "") == "":
                    os.environ[k] = v
    except FileNotFoundError:
        return


def create_app() -> Flask:
    _load_dotenv()
    app = Flask(__name__)
    secret = os.environ.get("AZ_SECRET_KEY", "dev-insecure-change-me")
    if secret == "dev-insecure-change-me" and os.environ.get("AZ_DEBUG", "0") != "1":
        import warnings
        warnings.warn("AZ_SECRET_KEY no configurado. Configure AZ_SECRET_KEY en .env para producción.", UserWarning)
    app.secret_key = secret

    es_produccion = is_production_mode()
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=es_produccion,
        TEMPLATES_AUTO_RELOAD=True,
    )
    if es_produccion:
        app.config["PREFERRED_URL_SCHEME"] = os.environ.get("AZ_PREFERRED_URL_SCHEME", "https")
    else:
        app.config["PREFERRED_URL_SCHEME"] = os.environ.get("AZ_PREFERRED_URL_SCHEME", "http")
    # Tras balanceador/proxy (DigitalOcean, nginx): HTTPS y host correctos para url_for / cookies.
    if trust_proxy():
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    # Logging a archivo para diagnosticar 500 en Windows/background
    log_path = os.environ.get("AZ_LOG_FILE", "server.log")
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    @app.errorhandler(404)
    def _pagina_no_encontrada(err):
        """Muestra página amigable cuando la URL no existe."""
        from flask import request
        url_intentada = request.url
        return (
            f'<!doctype html><html lang="es"><head><meta charset="utf-8">'
            f'<title>Página no encontrada</title>'
            f'<style>body{{font-family:sans-serif;max-width:500px;margin:60px auto;padding:20px;}}'
            f'a{{color:#2563eb;}} ul{{line-height:2;}}</style></head><body>'
            f'<h1>Página no encontrada</h1>'
            f'<p>La dirección que intentaste abrir no existe:</p>'
            f'<p><code>{url_intentada}</code></p>'
            f'<p>Enlaces que sí funcionan:</p>'
            f'<ul>'
            f'<li><a href="/">Inicio</a></li>'
            f'<li><a href="/login">Iniciar sesión</a></li>'
            f'<li><a href="/ventas_pos">Punto de venta</a></li>'
            f'<li><a href="/inventario">Inventario</a></li>'
            f'<li><a href="/clientes">Clientes</a></li>'
            f'<li><a href="/configuracion">Configuración</a></li>'
            f'</ul>'
            f'</body></html>',
            404,
        )

    @app.errorhandler(InternalServerError)
    def _internal_server_error(err: InternalServerError):  # type: ignore[override]
        original = getattr(err, "original_exception", None)
        if original:
            app.logger.exception("Unhandled error: %s", original)
        else:
            app.logger.exception("InternalServerError: %s", err)
        return (
            "<!doctype html><html lang=en><title>500 Internal Server Error</title>"
            "<h1>Internal Server Error</h1><p>Ocurrió un error interno.</p>",
            500,
        )

    @app.after_request
    def _headers_seguridad(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "SAMEORIGIN"
        resp.headers["X-XSS-Protection"] = "1; mode=block"
        return resp

    @app.before_request
    def _csrf_origin_check():
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return None
        if request.path in ("/login", "/logout"):
            return None
        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")
        if not (origin or referer):
            return None
        from urllib.parse import urlparse

        def _mismo_origen(url: str) -> bool:
            try:
                p = urlparse(url)
                return p.netloc == request.host and p.scheme in ("http", "https")
            except Exception:
                return False

        candidato = origin or referer
        if candidato and not _mismo_origen(candidato):
            return "Origen no permitido", 403
        return None

    # Blueprints principales (sin prefijo)
    app.register_blueprint(auth_bp)
    app.register_blueprint(core_bp)
    app.register_blueprint(pos_bp)
    app.register_blueprint(admin_bp)

    @app.before_request
    def _sync_agildte_role_from_token():
        """Actualiza usuarios.rol desde /api/auth/me/ si hay JWT en sesión (promoción cajero→admin en AgilDTE)."""
        from flask import request, session

        from azdigital.integration.agildte_role_sync import sync_role_from_session_if_due

        sync_role_from_session_if_due(session, request.path or "")
        return None

    @app.before_request
    def ensure_empresa_id():
        if session.get("username") and "empresa_id" not in session:
            session["empresa_id"] = 1
        if session.get("username") and "empresa_nombre" not in session:
            session["empresa_nombre"] = "Empresa"
        if session.get("user_id") and "rol" not in session:
            session["rol"] = "CAJERO"
        if session.get("rol") and isinstance(session["rol"], str):
            session["rol"] = session["rol"].strip().upper()
        # Evitar que empresa_id sea None (forzar int)
        if session.get("empresa_id") is None:
            session["empresa_id"] = 1
        # Refrescar rol desde BD para que SUPERADMIN se actualice sin cerrar sesión
        if session.get("user_id"):
            try:
                import psycopg2
                from database import ConexionDB
                db = ConexionDB()
                conn = psycopg2.connect(**db.config)
                cur = conn.cursor()
                cur.execute("SELECT rol FROM usuarios WHERE id = %s AND activo = TRUE", (session["user_id"],))
                r = cur.fetchone()
                cur.close()
                conn.close()
                if r and r[0]:
                    session["rol"] = str(r[0]).strip().upper()
            except Exception:
                pass

    @app.before_request
    def validar_suscripcion():
        if not session.get("user_id"):
            return None
        if session.get("rol") in ("ADMIN", "SUPERADMIN"):
            return None  # Superusuario puede acceder a todo sin validar suscripción
        path = request.path.rstrip("/") or "/"
        if path in ("/login", "/logout"):
            return None
        if path == "/suscripcion_expirada":
            return None
        try:
            import psycopg2
            from azdigital.repositories import empresas_repo
            from database import ConexionDB
            db = ConexionDB()
            conn = psycopg2.connect(**db.config)
            cur = conn.cursor()
            detalle = empresas_repo.get_suscripcion_detalle(cur, session.get("empresa_id", 1))
            cur.close()
            conn.close()
            if not detalle["vigente"]:
                from flask import redirect, url_for
                return redirect(url_for("core.suscripcion_expirada"))
        except Exception:
            pass
        return None

    @app.context_processor
    def inject_contexto():
        from azdigital.decorators import (
            puede_ver_ventas,
            puede_ver_inventario,
            puede_ver_reportes_contables,
            puede_ver_administracion,
            puede_gestionar_ventas,
        )
        ctx = {
            "alertas_inventario": [],
            "suscripcion": None,
            "rol_actual": session.get("rol"),
            "puede_ver_ventas": False,
            "puede_ver_inventario": False,
            "puede_ver_reportes_contables": False,
            "puede_ver_administracion": False,
            "puede_gestionar_ventas": False,
            "es_super": False,
        }
        if not session.get("username"):
            return ctx
        # Obtener rol desde BD primero (crítico para SUPERADMIN)
        uid = session.get("user_id")
        if uid:
            try:
                import psycopg2
                from database import ConexionDB
                db = ConexionDB()
                conn = psycopg2.connect(**db.config)
                cur = conn.cursor()
                cur.execute("SELECT rol FROM usuarios WHERE id = %s AND activo = TRUE", (uid,))
                r = cur.fetchone()
                cur.close()
                conn.close()
                if r and r[0]:
                    ctx["rol_actual"] = str(r[0]).strip().upper()
                    session["rol"] = ctx["rol_actual"]
            except Exception:
                pass
        rol = ctx.get("rol_actual") or ""
        ctx["puede_ver_ventas"] = puede_ver_ventas(rol)
        ctx["puede_ver_inventario"] = puede_ver_inventario(rol)
        ctx["puede_ver_reportes_contables"] = puede_ver_reportes_contables(rol)
        ctx["puede_ver_administracion"] = puede_ver_administracion(rol)
        ctx["puede_gestionar_ventas"] = puede_gestionar_ventas(rol)
        ctx["es_super"] = rol in ("ADMIN", "SUPERADMIN")
        try:
            import psycopg2
            from database import ConexionDB
            from azdigital.repositories import empresas_repo, productos_repo
            db = ConexionDB()
            conn = psycopg2.connect(**db.config)
            cur = conn.cursor()
            emp_id = session.get("empresa_id", 1)
            ctx["suscripcion"] = empresas_repo.get_suscripcion_detalle(cur, emp_id)
            try:
                ctx["alertas_inventario"] = productos_repo.productos_stock_bajo(cur, umbral=5, empresa_id=emp_id) or []
            except Exception:
                ctx["alertas_inventario"] = []
            cur.close()
            conn.close()
        except Exception:
            ctx["suscripcion"] = {"vigente": True, "dias_restantes": 0, "vencimiento": None, "activa": True}
        return ctx

    @app.context_processor
    def inject_public_base_url():
        """Plantillas: {{ PUBLIC_BASE_URL }} para enlaces absolutos (evitar 127.0.0.1 en producción)."""
        return {"PUBLIC_BASE_URL": get_public_base_url()}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("AZ_HOST", "127.0.0.1"),
        port=int(os.environ.get("AZ_PORT", os.environ.get("PORT", "5000"))),
        debug=(os.environ.get("AZ_DEBUG", "0") == "1"),
    )