# Programador: Oscar Amaya Romero
"""
Configuración desde entorno para producción (DigitalOcean, VPS, etc.).

- DATABASE_URL / AZ_DATABASE_URL: cadena PostgreSQL (Heroku/DO). Evita HOST=127.0.0.1 en el servidor.
- PUBLIC_BASE_URL / AZ_PUBLIC_BASE_URL: URL HTTPS pública (sin barra final) para enlaces y WhatsApp.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


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


def trust_proxy() -> bool:
    """Detrás de nginx/DO App Platform con X-Forwarded-*: definir AZ_TRUST_PROXY=1."""
    return _truthy("AZ_TRUST_PROXY")


def postgres_connection_kwargs() -> dict[str, Any]:
    """
    Parámetros para psycopg2.connect(**kwargs).

    Prioridad:
    1) DATABASE_URL o AZ_DATABASE_URL (postgresql:// o postgres://)
    2) Variables AZ_DB_NAME, AZ_DB_USER, AZ_DB_PASSWORD, AZ_DB_HOST, AZ_DB_PORT
    """
    raw_url = (os.environ.get("DATABASE_URL") or os.environ.get("AZ_DATABASE_URL") or "").strip()
    client_encoding = os.environ.get("AZ_DB_CLIENT_ENCODING", "UTF8")
    options = os.environ.get("AZ_DB_OPTIONS", f"-c client_encoding={client_encoding}")

    if raw_url:
        url = raw_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        parsed = urlparse(url)
        path = (parsed.path or "").lstrip("/")
        q = parse_qs(parsed.query)
        config: dict[str, Any] = {
            "dbname": path or "postgres",
            "user": unquote(parsed.username or "") or "postgres",
            "password": unquote(parsed.password or "") if parsed.password else "",
            "host": parsed.hostname or "127.0.0.1",
            "port": str(parsed.port or 5432),
            "options": options,
        }
        sslmode = (q.get("sslmode") or [None])[0]
        if sslmode:
            config["sslmode"] = sslmode
        return config

    return {
        "dbname": os.environ.get("AZ_DB_NAME", "saas_facturacion"),
        "user": os.environ.get("AZ_DB_USER", "postgres"),
        "password": os.environ.get("AZ_DB_PASSWORD", ""),
        "host": os.environ.get("AZ_DB_HOST", "127.0.0.1"),
        "port": os.environ.get("AZ_DB_PORT", "5432"),
        "options": options,
    }
