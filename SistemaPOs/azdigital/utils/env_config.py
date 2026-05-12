# Programador: Oscar Amaya Romero
"""
Configuración desde entorno para producción (DigitalOcean, VPS, etc.).

- DATABASE_URL / AZ_DATABASE_URL: cadena PostgreSQL (Heroku/DO). Evita HOST=127.0.0.1 en el servidor.
- PUBLIC_BASE_URL / AZ_PUBLIC_BASE_URL: URL HTTPS pública (sin barra final) para enlaces y WhatsApp.
- POSAGIL_URL_PREFIX / APPLICATION_ROOT: ruta bajo la que se publica el POS (ej. /pos). Si falta, se infiere del path de PUBLIC_BASE_URL.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse


def _truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def is_production_mode() -> bool:
    return os.environ.get("AZ_DEBUG", "0") != "1"


def get_public_base_url() -> str:
    """URL pública https://dominio.com sin barra final; vacío si no está definida."""
    for key in ("PUBLIC_BASE_URL", "AZ_PUBLIC_BASE_URL"):
        v = (os.environ.get(key) or "").strip().rstrip("/")
        if v:
            return v
    return ""


def get_application_url_prefix() -> str:
    """
    Prefijo de ruta bajo el que el navegador ve el POS (ej. /pos para https://dominio.com/pos).
    Usar en window.open / enlaces absolutos para no caer en la SPA de AgilDTE en la raíz.
    """
    raw = (os.environ.get("POSAGIL_URL_PREFIX") or os.environ.get("APPLICATION_ROOT") or "").strip()
    if raw:
        p = raw.rstrip("/")
        return p if p.startswith("/") else f"/{p}"
    base = get_public_base_url()
    if not base:
        return ""
    path = (urlparse(base).path or "").strip().rstrip("/")
    return path if path else ""


def trust_proxy() -> bool:
    """Detrás de nginx/DO App Platform con X-Forwarded-*: definir AZ_TRUST_PROXY=1."""
    return _truthy("AZ_TRUST_PROXY")


def _unquote_url_userinfo(fragment: str | None) -> str:
    """Decodifica user/password del URI; tolera fragmentos codificados en Latin-1 (Windows)."""
    if not fragment:
        return ""
    for enc in ("utf-8", "latin-1"):
        try:
            return unquote(fragment, encoding=enc, errors="strict")
        except UnicodeDecodeError:
            continue
    return unquote(fragment, encoding="utf-8", errors="replace")


def _pg_dsn_uri(
    *,
    user: str,
    password: str,
    host: str,
    port: str | int,
    dbname: str,
    options: str | None = None,
    sslmode: str | None = None,
) -> str:
    """
    Cadena única para psycopg2.connect(dsn=...).
    Evita UnicodeDecodeError en Windows cuando user/password tienen acentos u otros no ASCII:
    todo el componente sensible va percent-encoded (UTF-8) como exige el formato URI.
    """
    u = quote(str(user or "postgres"), safe="")
    p = quote(str(password or ""), safe="")
    d = quote(str(dbname or "postgres"), safe="")
    h = (str(host).strip() or "127.0.0.1").replace("%", "%25")
    if ":" in h and not h.startswith("["):
        h = f"[{h}]"
    pr = str(port) if isinstance(port, int) else (str(int(port)) if str(port).strip().isdigit() else str(port))
    uri = f"postgresql://{u}:{p}@{h}:{pr}/{d}"
    qparts: list[str] = []
    if sslmode:
        qparts.append(f"sslmode={quote(str(sslmode), safe='')}")
    if options:
        qparts.append(f"options={quote(str(options), safe='')}")
    if qparts:
        uri += "?" + "&".join(qparts)
    return uri


def postgres_connection_kwargs() -> dict[str, Any]:
    """
    Parámetros para psycopg2.connect(**kwargs).

    Siempre devuelve ``{"dsn": "<postgresql://...>"}`` para que libpq reciba un URI ASCII
    (user/password/db codificados), evitando fallos de decodificación UTF-8 en Windows.

    Prioridad:
    1) DATABASE_URL o AZ_DATABASE_URL (postgresql:// o postgres://)
    2) Variables AZ_DB_NAME, AZ_DB_USER, AZ_DB_PASSWORD, AZ_DB_HOST, AZ_DB_PORT
    """
    raw_url = (os.environ.get("DATABASE_URL") or os.environ.get("AZ_DATABASE_URL") or "").strip()
    client_encoding = os.environ.get("AZ_DB_CLIENT_ENCODING", "UTF8")
    opts_default = f"-c client_encoding={client_encoding}"
    options = (os.environ.get("AZ_DB_OPTIONS") or "").strip() or opts_default

    if raw_url:
        url = raw_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        parsed = urlparse(url)
        path = (parsed.path or "").lstrip("/")
        dbname = path or "postgres"
        user = _unquote_url_userinfo(parsed.username) or "postgres"
        password = _unquote_url_userinfo(parsed.password) if parsed.password else ""
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 5432
        q = parse_qs(parsed.query)
        sslmode = (q.get("sslmode") or [None])[0]
        sslmode_s = str(sslmode) if sslmode else None
        return {
            "dsn": _pg_dsn_uri(
                user=user,
                password=password,
                host=host,
                port=port,
                dbname=dbname,
                options=options,
                sslmode=sslmode_s,
            )
        }

    return {
        "dsn": _pg_dsn_uri(
            user=os.environ.get("AZ_DB_USER", "postgres") or "postgres",
            password=os.environ.get("AZ_DB_PASSWORD", "") or "",
            host=os.environ.get("AZ_DB_HOST", "127.0.0.1") or "127.0.0.1",
            port=os.environ.get("AZ_DB_PORT", "5432") or "5432",
            dbname=os.environ.get("AZ_DB_NAME", "saas_facturacion") or "saas_facturacion",
            options=options,
            sslmode=None,
        )
    }
