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
    public_sync_result,
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
    # get_cliente: 0 id … 11 cod_act, 12 nrc, 13 departamento, 14 municipio
    try:
        nombre = (cl[3] or "").strip() if len(cl) > 3 else ""
        tipo = (cl[4] or "NIT").strip() if len(cl) > 4 else "NIT"
        num = (cl[5] or "").strip() if len(cl) > 5 else ""
        correo = (cl[6] or "").strip() if len(cl) > 6 else ""
        direccion = (cl[9] or "").strip() if len(cl) > 9 else ""
        telefono = (cl[10] or "").strip() if len(cl) > 10 else ""
        cod_act = (cl[11] or "").strip() if len(cl) > 11 else ""
        nrc = (cl[12] or "").strip() if len(cl) > 12 else ""
        if not nrc and tipo.upper() == "NRC" and num:
            nrc = num
        departamento = (cl[13] or "06").strip() if len(cl) > 13 else "06"
        municipio = (cl[14] or "14").strip() if len(cl) > 14 else "14"
        out = {
            "nombre": nombre or "Consumidor Final",
            "tipo_documento": tipo,
            "numero_documento": num,
            "correo": correo,
            "direccion": direccion,
            "telefono": telefono,
            "nrc": nrc,
            "codigo_actividad_economica": cod_act,
        }
        if departamento:
            out["departamento"] = departamento
        if municipio:
            out["municipio"] = municipio
        return out
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
            cli = login_client_from_request_or_env(trust_request_bearer=False)
        if cli.empresa_id is None:
            cli.set_empresa_id(empresa_id_local)
        eid = int(cli.empresa_id or empresa_id_local)

        receptor = None
        if cliente_id:
            from azdigital.repositories import clientes_repo

            cl = clientes_repo.get_cliente(cur, int(cliente_id))
            receptor = _receptor_desde_cliente_row(cl)
            tc = (tipo_comprobante or "").strip().upper()
            if tc == "CREDITO_FISCAL" and receptor:
                nrc = (receptor.get("nrc") or "").strip()
                if not nrc:
                    return public_sync_result(
                        {
                            "ok": False,
                            "error": "cliente_sin_nrc",
                            "mensaje_usuario": (
                                "Para Crédito Fiscal el cliente debe tener NRC en el formulario "
                                "(campo NRC, no solo tipo de documento). Edite el cliente y guárdelo."
                            ),
                        }
                    ) or {"ok": False, "error": "cliente_sin_nrc"}
                num_doc = (receptor.get("numero_documento") or "").strip()
                nrc_d = "".join(c for c in nrc if c.isdigit())
                doc_d = "".join(c for c in num_doc if c.isdigit())
                if doc_d and nrc_d and (nrc_d == doc_d or nrc_d in doc_d):
                    return public_sync_result(
                        {
                            "ok": False,
                            "error": "nrc_igual_documento",
                            "mensaje_usuario": (
                                "El NRC del cliente no puede ser el mismo número que el DUI/NIT. "
                                "Ingrese el NRC oficial del contribuyente en Hacienda."
                            ),
                        }
                    ) or {"ok": False, "error": "nrc_igual_documento"}

        # No enviar cliente_id local: el PK de PosAgil no existe en AgilDTE (provoca "Cliente no encontrado").
        body = build_crear_venta_con_detalles_payload(
            empresa_id=eid,
            tipo_comprobante_pos=tipo_comprobante,
            tipo_pago=tipo_pago,
            lineas=lineas,
            total_neto=total_neto,
            total_bruto=total_bruto,
            descuento=descuento,
            cliente_id=None,
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

        return public_sync_result(out) or out
    except AgilDTEUnauthorizedError:
        return public_sync_result(
            {
                "ok": False,
                "error": "unauthorized",
                "mensaje_usuario": "Sesión AgilDTE expirada. Vuelva a abrir el POS desde el portal.",
            }
        ) or {"ok": False, "error": "unauthorized"}
    except AgilDTEForbiddenError:
        return public_sync_result(
            {
                "ok": False,
                "error": "forbidden",
                "mensaje_usuario": "Sin permiso para facturar en AgilDTE con esta empresa.",
            }
        ) or {"ok": False, "error": "forbidden"}
    except AgilDTEAuthError:
        return public_sync_result(
            {
                "ok": False,
                "error": "auth",
                "mensaje_usuario": "No hay sesión AgilDTE. Abra el POS desde el portal o configure credenciales de servicio.",
            }
        ) or {"ok": False, "error": "auth"}
    except AgilDTEAPIError as e:
        try:
            from azdigital.integration.agildte_client import _format_api_error_body as _fmt_err

            texto_plano = _fmt_err(e.body)
        except Exception:
            texto_plano = ""
        mu = (texto_plano or "").strip() or "No se pudo sincronizar la venta con AgilDTE."
        return public_sync_result(
            {"ok": False, "error": "api", "mensaje_usuario": mu[:500]}
        ) or {"ok": False, "error": "api"}
    except Exception:
        return public_sync_result(
            {
                "ok": False,
                "error": "interno",
                "mensaje_usuario": "Error interno al sincronizar con AgilDTE.",
            }
        ) or {"ok": False, "error": "interno"}


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
