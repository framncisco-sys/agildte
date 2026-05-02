# Programador: Oscar Amaya Romero
"""
Sincronización periódica del rol local con GET /api/auth/me/ de AgilDTE.
Así, si en Django pasan de cajero a administrador, el POS actualiza sin volver a abrir el portal
(esperando el intervalo o la próxima petición tras guardar el token en sesión).
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def sync_role_from_session_if_due(session: Any, request_path: str) -> None:
    """
    Si hay JWT en sesión y pasó el intervalo, llama a AgilDTE y ejecuta provision_if_missing.
    No lanza excepciones hacia arriba.
    """
    token = (session.get("agildte_access_token") or "").strip()
    if not token or not session.get("user_id"):
        return
    p = (request_path or "").rstrip("/") or "/"
    if p.startswith("/static"):
        return
    if p in ("/auth/agildte", "/login", "/logout"):
        return

    try:
        interval = int(os.environ.get("AGILDTE_ROLE_SYNC_INTERVAL_SEC", "120"))
    except ValueError:
        interval = 120
    now = time.time()
    try:
        last = float(session.get("_agildte_role_sync_ts") or 0)
    except (TypeError, ValueError):
        last = 0.0
    if interval > 0 and (now - last) < interval:
        return

    from azdigital.integration.agildte_client import resolve_agildte_base_url
    from azdigital.integration.agildte_sso_provision import provision_if_missing

    base = resolve_agildte_base_url()
    if not base:
        return

    try:
        r = httpx.get(
            f"{base.rstrip('/')}/api/auth/me/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=12.0,
        )
    except Exception as exc:
        logger.warning("AgilDTE /api/auth/me/ sync omitido: %s", exc)
        return

    if r.status_code == 401:
        # No borrar el JWT aquí: un 401 puntual (reloj, red, URL mal configurada en Docker)
        # dejaba al usuario sin token y el sync caía a AGILDTE_USERNAME/PASSWORD.
        limpiar = (os.environ.get("AGILDTE_ROLE_SYNC_CLEAR_TOKEN_ON_401") or "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if limpiar:
            session.pop("agildte_access_token", None)
            session.pop("_agildte_role_sync_ts", None)
        else:
            logger.warning(
                "AgilDTE /api/auth/me/ devolvió 401; no se elimina agildte_access_token "
                "(defina AGILDTE_ROLE_SYNC_CLEAR_TOKEN_ON_401=1 para limpiar sesión)."
            )
        return

    if r.status_code != 200:
        return

    try:
        data = r.json() if r.content else {}
    except Exception:
        data = {}

    try:
        import psycopg2
        from database import ConexionDB

        db = ConexionDB()
        conn = psycopg2.connect(**db.config)
        cur = conn.cursor()
        try:
            ok, _err = provision_if_missing(cur, data)
            if ok:
                conn.commit()
                session["_agildte_role_sync_ts"] = now
                cur.execute(
                    "SELECT rol, empresa_id FROM usuarios WHERE id = %s AND activo = TRUE",
                    (session["user_id"],),
                )
                row = cur.fetchone()
                if row and row[0]:
                    session["rol"] = str(row[0]).strip().upper()
                if row and len(row) > 1 and row[1] is not None:
                    session["empresa_id"] = int(row[1])
            else:
                conn.rollback()
        finally:
            cur.close()
            conn.close()
    except Exception as exc:
        logger.warning("sync_role_from_session_if_due BD: %s", exc)
