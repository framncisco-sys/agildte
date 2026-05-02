# Programador: Oscar Amaya Romero
"""
Contingencia MH vía AgilDTE (mismo flujo que frontend-saas:
POST /api/empresas/{id}/procesar-contingencia-completa/).
"""
from __future__ import annotations

from typing import Any

from azdigital.integration.agildte_client import (
    AgilDTEAPIError,
    AgilDTEAuthError,
    AgilDTEForbiddenError,
    AgilDTEUnauthorizedError,
    login_client_from_request_or_env,
)


def procesar_contingencia_completa_remoto(
    empresa_id_local: int,
    *,
    tipo_contingencia: int | None = None,
    motivo: str | None = None,
) -> dict[str, Any]:
    """
    Ejecuta en el backend central el proceso completo (reporte + envíos), como el modal de Configuración en AgilDTE.

    Returns:
        dict con claves al menos: ok (bool), respuesta (data API) o error/mensaje.
    """
    try:
        cli = login_client_from_request_or_env()
        eid = int(cli.empresa_id or empresa_id_local)
        if cli.empresa_id is None:
            cli.set_empresa_id(eid)
        body: dict[str, Any] = {}
        if tipo_contingencia is not None:
            body["tipoContingencia"] = int(tipo_contingencia)
        if motivo and str(motivo).strip():
            body["motivo"] = str(motivo).strip()
        data = cli.procesar_contingencia_completa_agildte(eid, body=body or None, timeout=600.0)
        return {"ok": True, "respuesta": data}
    except AgilDTEUnauthorizedError as e:
        return {"ok": False, "error": "unauthorized", "mensaje": str(e), "detalle": e.body}
    except AgilDTEForbiddenError as e:
        return {"ok": False, "error": "forbidden", "mensaje": str(e), "detalle": e.body}
    except AgilDTEAuthError as e:
        return {"ok": False, "error": "auth", "mensaje": str(e), "detalle": e.body}
    except AgilDTEAPIError as e:
        return {
            "ok": False,
            "error": "api",
            "mensaje": str(e),
            "detalle": e.body,
            "status": e.status_code,
        }
    except Exception as e:
        return {"ok": False, "error": "interno", "mensaje": str(e)}
