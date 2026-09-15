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
    login_client_tras_sesion_expirada,
    public_sync_result,
    _credenciales_servicio_validas,
)
from azdigital.repositories import ventas_repo
from azdigital.utils.fecha_sv import fecha_hora_desde_registro


def _truthy_env(name: str, default: bool = False) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "on")


def _id_entero(val: Any) -> int | None:
    if isinstance(val, int):
        return val
    if isinstance(val, str) and val.isdigit():
        return int(val)
    return None


def _extraer_resultados_listar(payload: Any) -> list:
    if isinstance(payload, dict):
        results = payload.get("results")
        if isinstance(results, list):
            return results
        if isinstance(payload.get("ventas"), list):
            return payload.get("ventas")
    if isinstance(payload, list):
        return payload
    return []


def resolver_id_venta_agildte(
    cli: Any,
    *,
    empresa_id: int,
    codigo_generacion: str,
    numero_control: str,
) -> int | None:
    """
    ID de la venta en AgilDTE (backend Django), no el ID local del POS.

    Nunca usar el id de PosÁgil como fallback: son secuencias distintas
    (POS 827 ≠ AgilDTE 827) y abrirían un DTE ajeno.
    """
    def _buscar_exacto(search_txt: str) -> int | None:
        q = (search_txt or "").strip()
        if not q:
            return None
        data = cli.get_json(
            "/api/ventas/listar/",
            params={"empresa_id": empresa_id, "search": q, "page": 1, "page_size": 20},
        )
        q_upper = q.upper()
        for it in _extraer_resultados_listar(data):
            if not isinstance(it, dict):
                continue
            cg = str(it.get("codigo_generacion") or "").strip().upper()
            nc = str(it.get("numero_control") or "").strip().upper()
            if q_upper and (cg == q_upper or nc == q_upper):
                return _id_entero(it.get("id"))
        return None

    return _buscar_exacto(codigo_generacion) or _buscar_exacto(numero_control)


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
    # get_cliente: … 11 cod_act, 12 nrc, 13 depto, 14 muni, 15 distrito, 16 nom_com, 17 desc_act
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
        municipio = (cl[14] or "23").strip() if len(cl) > 14 else "23"
        distrito = (cl[15] or "14").strip() if len(cl) > 15 else "14"
        nombre_comercial = (cl[16] or "").strip() if len(cl) > 16 else ""
        desc_actividad = (cl[17] or "").strip() if len(cl) > 17 else ""
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
        if distrito:
            out["distrito"] = distrito
        if nombre_comercial:
            out["nombre_comercial"] = nombre_comercial
        if desc_actividad:
            out["desc_actividad"] = desc_actividad
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
    _reintento_auth: bool = False,
) -> dict[str, Any]:
    """
    Crea venta remota con POST /api/ventas/crear-con-detalles/ (encola o procesa DTE en AgilDTE).

    No llama a generar-dte después: el backend ya dispara facturación al crear la venta.

    Retorna dict serializable para incluir en la respuesta JSON del POS (agildte_sync).
    Si el JWT de sesión caducó, reintenta una vez con AGILDTE_USERNAME/PASSWORD.
    """
    cli = cliente
    try:
        if cli is None:
            cli = login_client_from_request_or_env(trust_request_bearer=False)
        # Siempre alinear tenant con la empresa de la venta POS (no el default del login).
        cli.set_empresa_id(int(empresa_id_local))
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
        fr = ventas_repo.get_fecha_registro(cur, venta_id_local)
        fe_iso, hora_sv, periodo = fecha_hora_desde_registro(fr)
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
            fecha_emision=fe_iso,
            hora_emision=hora_sv,
            periodo_aplicado=periodo,
        )
        creado = cli.procesar_venta_pos(body)
        venta_payload = creado.get("venta") if isinstance(creado, dict) else None
        remote_id = _extraer_id_venta_remota(venta_payload if venta_payload is not None else creado)
        ok = True
        if isinstance(creado, dict):
            ok = bool(creado.get("ok", True))

        dte_persistido = False
        # Persistir código/sello siempre que vengan en la respuesta (aunque ok=False p.ej. rechazo).
        if isinstance(venta_payload, dict):
            try:
                dte_persistido = ventas_repo.actualizar_dte_desde_respuesta_agildte(
                    cur, venta_id_local, empresa_id_local, venta_payload
                )
            except Exception:
                dte_persistido = False
            # Fallback: a veces el cuerpo viene aplanado (sin anidar en «venta»).
            if not dte_persistido and isinstance(creado, dict):
                try:
                    dte_persistido = ventas_repo.actualizar_dte_desde_respuesta_agildte(
                        cur, venta_id_local, empresa_id_local, creado
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
                extra = {}
                if isinstance(venta_payload, dict):
                    extra["codigo_generacion"] = venta_payload.get("codigo_generacion")
                    extra["numero_control"] = venta_payload.get("numero_control")
                out["dte_json_preview"] = cli.generar_dte_venta(remote_id, extra)
            except AgilDTEAPIError as e:
                out["dte_json_preview"] = None
                out["dte_json_error"] = str(e)

        return public_sync_result(out) or out
    except AgilDTEUnauthorizedError:
        # JWT de cajero caducó: reentrar con usuario/clave de servicio (misma cuenta AgilDTE).
        if cliente is None and not _reintento_auth and _credenciales_servicio_validas():
            try:
                cli_svc = login_client_tras_sesion_expirada()
                # Dejar tokens frescos en sesión para las siguientes ventas del turno.
                try:
                    from flask import has_request_context, session as flask_session

                    if has_request_context() and getattr(cli_svc, "_access", None):
                        flask_session["agildte_access_token"] = cli_svc._access
                        if getattr(cli_svc, "_refresh", None):
                            flask_session["agildte_refresh_token"] = cli_svc._refresh
                except Exception:
                    pass
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
                    cliente=cli_svc,
                    _reintento_auth=True,
                )
            except (AgilDTEUnauthorizedError, AgilDTEAuthError):
                pass
        return public_sync_result(
            {
                "ok": False,
                "error": "unauthorized",
                "mensaje_usuario": (
                    "Sesión AgilDTE expirada. Se intentó reentrar con credenciales de servicio; "
                    "si el fallo continúa, vuelva a abrir el POS desde el portal."
                ),
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


def remitir_venta_existente(
    *,
    cur,
    empresa_id_local: int,
    venta_id_local: int,
) -> dict[str, Any]:
    """
    Emite en AgilDTE una venta ya cobrada en el POS (fecha y cajero se conservan).

    Pendiente: primera emisión.
    Rechazado: corrige y crea un DTE nuevo (nuevo correlativo). Si Hacienda acepta,
    el estado local pasa a Corregido.
    """
    from azdigital.utils.estado_emision import (
        CLAVES_EMITIBLES,
        clasificar_estado_emision,
        es_estado_aceptado_mh,
    )

    venta = ventas_repo.get_venta(cur, venta_id_local, empresa_id=empresa_id_local)
    if not venta:
        return {
            "ok": False,
            "error": "no_encontrada",
            "mensaje_usuario": f"Venta #{venta_id_local} no encontrada.",
        }
    cg = str(venta[14] or "").strip() if len(venta) > 14 else ""
    ed = str(venta[17] or "").strip() if len(venta) > 17 else ""
    st = clasificar_estado_emision(cg, ed)
    if st["clave"] not in CLAVES_EMITIBLES:
        return {
            "ok": False,
            "error": "ya_enviada",
            "mensaje_usuario": (
                f"La venta #{venta_id_local} ya está en AgilDTE "
                f"({st['etiqueta']}). No se vuelve a emitir para no duplicar el DTE."
            ),
        }
    es_correccion = st["clave"] == "rechazado"
    lineas_raw = ventas_repo.get_detalles_completos(cur, venta_id_local)
    lineas = [
        {
            "producto_id": ln["producto_id"],
            "cantidad": ln["cantidad"],
            "precio_unitario": ln["precio_unitario"],
            "subtotal": ln["subtotal"],
            "descripcion": ln["nombre"],
        }
        for ln in lineas_raw
        if ln.get("producto_id") and ln.get("cantidad", 0) > 0
    ]
    if not lineas:
        return {
            "ok": False,
            "error": "sin_lineas",
            "mensaje_usuario": f"La venta #{venta_id_local} no tiene líneas para emitir.",
        }
    tipo_comp = str(venta[4] or "TICKET")
    tipo_pago = str(venta[9] or "EFECTIVO") if len(venta) > 9 else "EFECTIVO"
    cliente_id = venta[5] if len(venta) > 5 else None
    try:
        cliente_id = int(cliente_id) if cliente_id is not None else None
    except (TypeError, ValueError):
        cliente_id = None
    nombre = str(venta[3] or "Consumidor Final")
    total = float(venta[2] or 0)
    desc = float(venta[12] or 0) if len(venta) > 12 else 0.0
    bruto = float(venta[13] or total) if len(venta) > 13 else total
    result = sync_venta_a_agildte(
        cur=cur,
        empresa_id_local=empresa_id_local,
        venta_id_local=venta_id_local,
        tipo_comprobante=tipo_comp,
        tipo_pago=tipo_pago,
        lineas=lineas,
        total_neto=total,
        total_bruto=bruto,
        descuento=desc,
        cliente_id=cliente_id,
        cliente_nombre_ticket=nombre,
    )
    if es_correccion and isinstance(result, dict):
        result["reemitido"] = True
        venta_despues = ventas_repo.get_venta(cur, venta_id_local, empresa_id=empresa_id_local)
        ed_nueva = (
            str(venta_despues[17] or "").strip()
            if venta_despues and len(venta_despues) > 17
            else ""
        )
        if result.get("ok") and es_estado_aceptado_mh(ed_nueva):
            if ventas_repo.marcar_estado_dte_local(
                cur, venta_id_local, "CORREGIDO", empresa_id=empresa_id_local
            ):
                result["corregido"] = True
                result["dte_persistido"] = True
    return result


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
