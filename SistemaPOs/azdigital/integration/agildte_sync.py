# Programador: Oscar Amaya Romero
"""
Sincronización opcional de ventas del POS local hacia el backend central AgilDTE.

Activar con AGILDTE_SYNC_ENABLED=1 (o true/yes). Requiere AGILDTE_BASE_URL; la autenticación
usa el JWT del usuario en sesión (SSO AgilDTE) o, si no hay sesión, AGILDTE_USERNAME/PASSWORD.

La venta ya debe estar persistida en la base local (commit hecho). Si la API remota falla,
por defecto no se revierte la venta local (AGILDTE_SYNC_FAIL_SOFT=1, predeterminado).
"""
from __future__ import annotations

import os
from typing import Any

from azdigital.integration.agildte_client import (
    AgilDTEAPIError,
    AgilDTEAuthError,
    AgilDTEClient,
    AgilDTEForbiddenError,
    AgilDTEUnauthorizedError,
    build_crear_venta_con_detalles_payload,
    login_client_from_request_or_env,
)
from azdigital.repositories import ventas_repo


def _truthy_env(name: str, default: bool = False) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def _extraer_id_venta_remota(resp: Any) -> int | None:
    if resp is None:
        return None
    if isinstance(resp, dict):
        for key in ("id", "venta_id", "pk", "venta"):
            v = resp.get(key)
            if isinstance(v, dict) and v.get("id") is not None:
                try:
                    return int(v["id"])
                except (TypeError, ValueError):
                    pass
            if v is not None and not isinstance(v, dict):
                try:
                    return int(v)
                except (TypeError, ValueError):
                    pass
    return None


def _receptor_desde_cliente_row(cl: tuple | list | None) -> dict[str, Any] | None:
    if not cl:
        return None
    # get_cliente: (id, empresa_id, sucursal_id, nombre, tipo_doc, num_doc, correo, contrib, gran, dir, tel, cod_act)
    try:
        nombre = (cl[3] or "").strip() if len(cl) > 3 else ""
        tipo = (cl[4] or "NIT").strip() if len(cl) > 4 else "NIT"
        num = (cl[5] or "").strip() if len(cl) > 5 else ""
        correo = (cl[6] or "").strip() if len(cl) > 6 else ""
        direccion = (cl[8] or "").strip() if len(cl) > 8 else ""
        telefono = (cl[9] or "").strip() if len(cl) > 9 else ""
        nrc = ""
        return {
            "nombre": nombre or "Consumidor Final",
            "tipo_documento": tipo,
            "numero_documento": num,
            "correo": correo,
            "direccion": direccion,
            "telefono": telefono,
            "nrc": nrc,
        }
    except Exception:
        return None


def sync_venta_a_agildte(
    *,
    cur,
    empresa_id_local: int,
    venta_id_local: int,
    tipo_comprobante: str,
    tipo_pago: str,
    lineas: list[Any],
    total_neto: float,
    total_bruto: float,
    descuento: float,
    cliente_id: int | None,
    cliente_nombre_ticket: str,
    cliente: AgilDTEClient | None = None,
) -> dict[str, Any]:
    """
    Crea venta remota con POST /api/ventas/crear-con-detalles/ (encola o procesa DTE en AgilDTE).

    No llama a generar-dte después: el backend ya dispara facturación al crear la venta.

    Retorna dict serializable para incluir en la respuesta JSON del POS (agildte_sync).
    """
    cli = cliente
    try:
        if cli is None:
            cli = login_client_from_request_or_env()
        if cli.empresa_id is None:
            cli.set_empresa_id(empresa_id_local)
        eid = int(cli.empresa_id or empresa_id_local)

        receptor = None
        if cliente_id:
            from azdigital.repositories import clientes_repo

            cl = clientes_repo.get_cliente(cur, int(cliente_id))
            receptor = _receptor_desde_cliente_row(cl)

        body = build_crear_venta_con_detalles_payload(
            empresa_id=eid,
            tipo_comprobante_pos=tipo_comprobante,
            tipo_pago=tipo_pago,
            lineas=lineas,
            total_neto=total_neto,
            total_bruto=total_bruto,
            descuento=descuento,
            cliente_id=cliente_id,
            cliente_nombre_ticket=cliente_nombre_ticket,
            receptor=receptor,
            venta_local_id=venta_id_local,
        )
        creado = cli.procesar_venta_pos(body)
        venta_payload = creado.get("venta") if isinstance(creado, dict) else None
        remote_id = _extraer_id_venta_remota(venta_payload if venta_payload is not None else creado)
        ok = True
        if isinstance(creado, dict):
            ok = bool(creado.get("ok", True))

        dte_persistido = False
        if ok and isinstance(venta_payload, dict):
            try:
                dte_persistido = ventas_repo.actualizar_dte_desde_respuesta_agildte(
                    cur, venta_id_local, empresa_id_local, venta_payload
                )
            except Exception:
                dte_persistido = False

        out: dict[str, Any] = {
            "ok": ok,
            "venta_remota_id": remote_id,
            "crear_respuesta": creado,
            "mensaje_agildte": (creado.get("mensaje") if isinstance(creado, dict) else None),
            "facturacion": "Respuesta desde /api/pos/procesar-venta/ (AgilDTE).",
            "dte_persistido": dte_persistido,
        }

        if _truthy_env("AGILDTE_FETCH_DTE_JSON", default=False) and remote_id:
            try:
                out["dte_json_preview"] = cli.generar_dte_venta(remote_id)
            except AgilDTEAPIError as e:
                out["dte_json_preview"] = None
                out["dte_json_error"] = str(e)

        return out
    except AgilDTEUnauthorizedError as e:
        return {"ok": False, "error": "unauthorized", "mensaje": str(e), "detalle": e.body}
    except AgilDTEForbiddenError as e:
        return {"ok": False, "error": "forbidden", "mensaje": str(e), "detalle": e.body}
    except AgilDTEAuthError as e:
        return {"ok": False, "error": "auth", "mensaje": str(e), "detalle": e.body}
    except AgilDTEAPIError as e:
        try:
            from azdigital.integration.agildte_client import _format_api_error_body as _fmt_err

            texto_plano = _fmt_err(e.body)
        except Exception:
            texto_plano = ""
        mu = (texto_plano or "").strip() or str(e)
        return {
            "ok": False,
            "error": "api",
            "mensaje": str(e),
            "mensaje_usuario": mu,
            "detalle": e.body,
            "status": e.status_code,
        }
    except Exception as e:
        return {"ok": False, "error": "interno", "mensaje": str(e)}


def intentar_sync_venta_si_habilitado(
    *,
    cur,
    empresa_id_local: int,
    venta_id_local: int,
    tipo_comprobante: str,
    tipo_pago: str,
    lineas: list[Any],
    total_neto: float,
    total_bruto: float,
    descuento: float,
    cliente_id: int | None,
    cliente_nombre_ticket: str,
) -> dict[str, Any] | None:
    """Si AGILDTE_SYNC_ENABLED, ejecuta sync y retorna resultado; si no, None."""
    if not _truthy_env("AGILDTE_SYNC_ENABLED"):
        return None
    return sync_venta_a_agildte(
        cur=cur,
        empresa_id_local=empresa_id_local,
        venta_id_local=venta_id_local,
        tipo_comprobante=tipo_comprobante,
        tipo_pago=tipo_pago,
        lineas=lineas,
        total_neto=total_neto,
        total_bruto=total_bruto,
        descuento=descuento,
        cliente_id=cliente_id,
        cliente_nombre_ticket=cliente_nombre_ticket,
    )
