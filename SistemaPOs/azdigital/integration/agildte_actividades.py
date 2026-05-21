"""Catálogo de actividades económicas desde AgilDTE (fuente única con Django), con respaldo local."""
from __future__ import annotations

from typing import Any

from .agildte_client import (
    AgilDTEAPIError,
    AgilDTEAuthError,
    AgilDTEUnauthorizedError,
    login_client_from_request_or_env,
)


def _listar_actividades_local(
    *,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Catálogo en PostgreSQL del POS (tabla actividades_economicas)."""
    import psycopg2

    from azdigital.repositories import actividades_repo
    from database import ConexionDB

    db = ConexionDB()
    conn = psycopg2.connect(**db.config)
    cur = conn.cursor()
    try:
        rows, total = actividades_repo.buscar_actividades(cur, search=search, limit=limit, offset=offset)
    except Exception as e:
        err = str(e).lower()
        if "actividades_economicas" in err and ("does not exist" in err or "no existe" in err):
            return {
                "ok": False,
                "results": [],
                "count": 0,
                "mensaje": (
                    "Sin conexión a AgilDTE y el catálogo local no está instalado. "
                    "Configure AGILDTE_USERNAME y AGILDTE_PASSWORD en .env y reinicie posagil, "
                    "o ejecute: python scripts/seed_actividades_basico.py"
                ),
                "source": "local",
                "error": str(e),
            }
        return {
            "ok": False,
            "results": [],
            "count": 0,
            "mensaje": f"Error al leer catálogo local: {e}",
            "source": "local",
            "error": str(e),
        }
    finally:
        cur.close()
        conn.close()

    if not rows:
        return {
            "ok": False,
            "results": [],
            "count": 0,
            "mensaje": (
                "Catálogo local vacío. Configure AGILDTE_USERNAME/PASSWORD en .env (usuario Django) "
                "o ejecute python scripts/seed_actividades_basico.py en el contenedor posagil."
            ),
            "source": "local",
            "error": "empty",
        }

    results = [{"codigo": str(c or "").strip(), "descripcion": str(d or "").strip()} for c, d in rows if c]
    return {
        "ok": True,
        "results": results,
        "count": total,
        "source": "local",
        "mensaje": "Catálogo local (AgilDTE no disponible). Configure credenciales en .env para sincronizar con el portal.",
    }


def listar_actividades_agildte(
    *,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    GET /api/actividades/ — misma API que el frontend AgilDTE (ActividadEconomica).
    Si falla auth o red, usa tabla local actividades_economicas.

    Retorna { ok, results, count, source, mensaje? }.
    """
    limit = max(1, min(int(limit or 50), 50))
    offset = max(0, int(offset or 0))
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    q = (search or "").strip()
    if q:
        params["search"] = q

    agildte_error: str | None = None
    try:
        cli = login_client_from_request_or_env(trust_request_bearer=False)
        data = cli.get_json("/api/actividades/", params=params)
    except (AgilDTEAuthError, AgilDTEUnauthorizedError) as e:
        agildte_error = str(e)
        local = _listar_actividades_local(search=search, limit=limit, offset=offset)
        if local.get("ok"):
            return local
        return {
            "ok": False,
            "results": [],
            "count": 0,
            "mensaje": (
                "Sesión AgilDTE no disponible. Entre desde el portal «Abrir PosAgil», use el mismo usuario "
                "en /login (con POSAGIL_ALLOW_LOCAL_LOGIN=1), o defina AGILDTE_USERNAME y AGILDTE_PASSWORD en .env."
            ),
            "source": "agildte",
            "error": agildte_error,
        }
    except AgilDTEAPIError as e:
        agildte_error = str(e)
        local = _listar_actividades_local(search=search, limit=limit, offset=offset)
        if local.get("ok"):
            return local
        return {
            "ok": False,
            "results": [],
            "count": 0,
            "mensaje": f"No se pudo cargar el catálogo desde AgilDTE: {e}",
            "source": "agildte",
            "error": agildte_error,
        }
    except Exception as e:
        agildte_error = str(e)
        local = _listar_actividades_local(search=search, limit=limit, offset=offset)
        if local.get("ok"):
            return local
        return {
            "ok": False,
            "results": [],
            "count": 0,
            "mensaje": f"Error al consultar actividades: {e}",
            "source": "agildte",
            "error": agildte_error,
        }

    if isinstance(data, list):
        rows = data
        total = len(rows)
    elif isinstance(data, dict):
        rows = data.get("results") or data.get("data") or []
        total = int(data.get("count") or len(rows))
    else:
        rows = []
        total = 0

    results = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        codigo = str(row.get("codigo") or "").strip()
        if not codigo:
            continue
        results.append({
            "codigo": codigo,
            "descripcion": str(row.get("descripcion") or "").strip(),
        })

    return {
        "ok": True,
        "results": results,
        "count": total,
        "source": "agildte",
        "mensaje": None,
    }
