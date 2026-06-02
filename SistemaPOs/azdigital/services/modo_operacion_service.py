# Programador: Oscar Amaya Romero
"""Modo operación POS: prueba (MH apitest) vs online (producción)."""
from __future__ import annotations

import os


def es_modo_prueba(ambiente: str | None) -> bool:
    return (ambiente or "01").strip() != "00"


def etiqueta_modo(ambiente: str | None) -> str:
    return "Versión prueba" if es_modo_prueba(ambiente) else "Online — producción"


def modo_desde_ambiente(ambiente: str | None) -> str:
    return "prueba" if es_modo_prueba(ambiente) else "online"


def _ambiente_desde_agildte_api(empresa_id: int) -> str | None:
    from azdigital.integration.agildte_client import (
        API_PREFIX,
        login_client_from_request_or_env,
        resolve_agildte_base_url,
    )

    if not resolve_agildte_base_url():
        return None
    try:
        cli = login_client_from_request_or_env(trust_request_bearer=False)
        eid = int(empresa_id)
        if cli.empresa_id is not None:
            eid = int(cli.empresa_id)
        data = cli.get_json(f"{API_PREFIX}/empresas/{eid}/")
        if isinstance(data, dict):
            amb = (data.get("ambiente") or "").strip()
            if amb in ("00", "01"):
                return amb
    except Exception:
        pass
    return None


def obtener_ambiente_empresa(empresa_id: int, cur=None) -> str:
    """Ambiente MH: env → AgilDTE API → caché local empresas.ambiente_mh → pruebas."""
    amb = (os.environ.get("AGILDTE_AMBIENTE") or "").strip()
    if amb in ("00", "01"):
        return amb
    amb = _ambiente_desde_agildte_api(empresa_id)
    if amb in ("00", "01"):
        return amb
    if cur is not None:
        from azdigital.repositories import empresas_repo

        local = empresas_repo.get_ambiente_mh(cur, empresa_id)
        if local in ("00", "01"):
            return local
    else:
        try:
            import psycopg2
            from database import ConexionDB
            from azdigital.repositories import empresas_repo

            conn = psycopg2.connect(**ConexionDB().config)
            c = conn.cursor()
            try:
                local = empresas_repo.get_ambiente_mh(c, empresa_id)
                if local in ("00", "01"):
                    return local
            finally:
                c.close()
                conn.close()
        except Exception:
            pass
    return "01"


def obtener_estado_modo(empresa_id: int, cur=None) -> dict:
    amb = obtener_ambiente_empresa(empresa_id, cur=cur)
    return {
        "ambiente": amb,
        "modo": modo_desde_ambiente(amb),
        "es_modo_prueba": es_modo_prueba(amb),
        "etiqueta": etiqueta_modo(amb),
    }
