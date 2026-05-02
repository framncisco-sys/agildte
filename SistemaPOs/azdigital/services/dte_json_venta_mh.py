# Programador: Oscar Amaya Romero
"""
JSON orientado al esquema DTE MH (El Salvador) a partir de una venta guardada.
Referencia: PLAN_INTEGRACION_MH.md — ajustar campos finos al XSD oficial.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from azdigital.utils.conversion_venta import cantidad_para_dte
from azdigital.utils.dte_item_json import item_dte_desde_linea
from azdigital.utils.mh_cat003_unidades import normalizar_codigo_mh

_ZONA_SV = timezone(timedelta(hours=-6))

_TRIBUTO_IVA = [{"codigo": "20", "descripcion": "Impuesto al Valor Agregado (13%)", "valor": 13.0}]


def _map_tipo_doc_mh(tipo_doc: str | None) -> str:
    t = (tipo_doc or "").strip().upper()
    if t in ("NIT",):
        return "36"
    if t in ("DUI", "DU", "DUI/DU"):
        return "13"
    if t in ("PASAPORTE", "PAS"):
        return "03"
    return "36"


def _fecha_emision_iso(cur, venta_id: int, empresa_id: int) -> str:
    cur.execute(
        """
        SELECT fecha_registro FROM ventas
        WHERE id = %s AND (empresa_id IS NULL OR empresa_id = %s)
        """,
        (venta_id, empresa_id),
    )
    row = cur.fetchone()
    if not row or not row[0]:
        return datetime.now(_ZONA_SV).isoformat(timespec="seconds")
    dt = row[0]
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_ZONA_SV)
        return dt.isoformat(timespec="seconds")
    return datetime.now(_ZONA_SV).isoformat(timespec="seconds")


def construir_json_dte_mh_venta(cur, venta_id: int, empresa_id: int) -> dict[str, Any] | None:
    from azdigital.repositories import empresas_repo, ventas_repo

    venta = ventas_repo.get_venta(cur, venta_id, empresa_id=empresa_id)
    if not venta:
        return None
    empresa = empresas_repo.get_empresa(cur, empresa_id)
    if not empresa:
        return None

    tcomp = str(venta[4] or "TICKET").strip().upper()
    if tcomp == "CREDITO_FISCAL":
        tipo_dte = "03"
    elif tcomp == "FACTURA":
        tipo_dte = "01"
    else:
        tipo_dte = "00"

    codigo_gen = (venta[14] or "").strip() if len(venta) > 14 else ""
    numero_ctrl = (venta[15] or "").strip() if len(venta) > 15 else ""
    estado_dte = (venta[17] or "RESPALDO").strip() if len(venta) > 17 else "RESPALDO"
    total = float(venta[2] or 0)
    total_bruto = float(venta[13] or total) if len(venta) > 13 else total
    descuento = float(venta[12] or 0) if len(venta) > 12 else 0
    retencion = float(venta[11] or 0) if len(venta) > 11 else 0

    nombre_em = (empresa[1] or "").strip() if len(empresa) > 1 else "Emisor"
    nit_em = (empresa[2] or "").strip() if len(empresa) > 2 else ""
    nrc_em = (empresa[3] or "").strip() if len(empresa) > 3 else ""
    act_em = (empresa[4] or "").strip() if len(empresa) > 4 else ""
    dir_em = (empresa[5] or "").strip() if len(empresa) > 5 else ""
    tel_em = (empresa[6] or "").strip() if len(empresa) > 6 else ""
    mail_em = (empresa[7] or "").strip() if len(empresa) > 7 else ""
    cod_act_em = ""
    try:
        cur.execute(
            "SELECT COALESCE(codigo_actividad_economica, '') FROM empresas WHERE id = %s",
            (empresa_id,),
        )
        rca = cur.fetchone()
        if rca:
            cod_act_em = str(rca[0] or "").strip()
    except Exception:
        pass

    doc_rec = (venta[6] or "").strip() if len(venta) > 6 else ""
    tipo_doc_rec = (venta[7] or "NIT").strip() if len(venta) > 7 else "NIT"
    nombre_rec = (venta[8] or venta[3] or "Consumidor Final").strip() if len(venta) > 8 else (venta[3] or "Consumidor Final")
    tel_rec = None
    mail_rec = None
    cliente_pk = venta[5] if len(venta) > 5 else None
    if cliente_pk:
        from azdigital.repositories import clientes_repo

        cl = clientes_repo.get_cliente(cur, int(cliente_pk))
        if cl:
            if len(cl) > 10:
                tel_rec = (cl[10] or "").strip() or None
            if len(cl) > 6:
                mail_rec = (cl[6] or "").strip() or None

    cur.execute(
        """
        SELECT p.codigo_barra, p.nombre, COALESCE(NULLIF(TRIM(p.mh_codigo_unidad), ''), '59'),
               dv.cantidad, dv.precio_unitario, dv.subtotal
        FROM venta_detalles dv
        JOIN productos p ON p.id = dv.producto_id
        WHERE dv.venta_id = %s
        ORDER BY dv.id
        """,
        (venta_id,),
    )
    filas = cur.fetchall() or []

    cuerpo: list[dict[str, Any]] = []
    nlinea = 0
    for row in filas:
        codigo, nombre, mh_u, cant, punit, sub = row[0], row[1], row[2], float(row[3] or 0), float(row[4] or 0), float(row[5] or 0)
        nlinea += 1
        cod_bar = (codigo or "").strip() or f"SKU{nlinea}"
        item_base = item_dte_desde_linea(
            (nombre or "")[:200],
            cant,
            punit,
            str(mh_u),
            tributos=_TRIBUTO_IVA,
        )
        cant_str = item_base.get("cantidad", cantidad_para_dte(cant))
        venta_grav = round(sub / 1.13, 8) if tcomp in ("FACTURA", "CREDITO_FISCAL") else round(sub, 8)
        linea: dict[str, Any] = {
            "numeroLinea": nlinea,
            "tipoItem": 1,
            "numeroDocumento": None,
            "codigo": cod_bar[:200],
            "descripcion": item_base.get("descripcion", ""),
            "cantidad": cant_str,
            "uniMedida": item_base.get("uniMedida", 59),
            "codigoUnidadMedida": normalizar_codigo_mh(str(mh_u)),
            "precioUnidad": round(punit, 8),
            "montoDescu": 0.0,
            "montoPagar": round(sub, 8),
            "ventasNoSujetas": 0.0,
            "ventasExentas": 0.0,
            "ventasGravadas": venta_grav,
            "tributos": item_base.get("tributos"),
        }
        if tcomp in ("FACTURA", "CREDITO_FISCAL"):
            linea["ivaItem"] = round(sub - sub / 1.13, 8)
        cuerpo.append(linea)

    gravada = round(total_bruto / 1.13, 2) if tcomp in ("FACTURA", "CREDITO_FISCAL") else round(total_bruto, 2)
    iva_tot = round(total_bruto - total_bruto / 1.13, 2) if tcomp in ("FACTURA", "CREDITO_FISCAL") else 0.0

    fec_emi = _fecha_emision_iso(cur, venta_id, empresa_id)
    identificacion: dict[str, Any] = {
        "codigoGeneracion": codigo_gen or None,
        "tipoDte": tipo_dte,
        "numeroControl": numero_ctrl or None,
        "tipoModelo": 1,
        "tipoOperacion": 1,
        "tipoContingencia": 1 if estado_dte == "CONTINGENCIA" else None,
        "motivoContin": "No disponibilidad sistema MH" if estado_dte == "CONTINGENCIA" else None,
        "fechaEmision": fec_emi,
        "tipoMoneda": "USD",
    }
    if tcomp == "TICKET":
        identificacion["notaUsoInternoAzDigital"] = "Ticket / respaldo interno (no sustituye DTE MH)"

    payload: dict[str, Any] = {
        "identificacion": identificacion,
        "documentoRelacionado": None,
        "emisor": {
            "nit": nit_em,
            "nrc": nrc_em,
            "nombre": nombre_em,
            "codActividad": cod_act_em or None,
            "descActividad": act_em or None,
            "direccion": {"complemento": dir_em[:150] if dir_em else "—"},
            "telefono": tel_em or None,
            "correo": mail_em or None,
        },
        "receptor": {
            "tipoDocumento": _map_tipo_doc_mh(tipo_doc_rec),
            "numDocumento": doc_rec or None,
            "nrc": None,
            "nombre": nombre_rec[:250],
            "codActividad": None,
            "descActividad": None,
            "direccion": {"complemento": "—"},
            "telefono": tel_rec,
            "correo": mail_rec,
        },
        "cuerpoDocumento": cuerpo,
        "resumen": {
            "totalNoSuj": 0.0,
            "totalExenta": 0.0,
            "totalGravada": gravada,
            "subTotalVentas": round(total_bruto, 2),
            "descuNoSuj": 0.0,
            "descuExenta": 0.0,
            "descuGravada": round(descuento, 2),
            "porcentajeDescuento": 0.0,
            "totalDescu": round(descuento, 2),
            "tributos": [{"codigo": "20", "descripcion": "IVA 13%", "valor": iva_tot}] if tcomp in ("FACTURA", "CREDITO_FISCAL") else [],
            "subTotal": round(total_bruto - descuento, 2),
            "ivaRete1": round(retencion, 2),
            "reteRenta": 0.0,
            "montoTotalOperacion": round(total, 2),
            "totalNoGravado": 0.0,
            "totalPagar": round(total - retencion, 2),
            "totalLetras": None,
            "saldoFavor": 0.0,
            "condicionOperacion": 1,
            "pagos": [{"codigo": "01", "montoPago": round(total - retencion, 2), "referencia": None}],
            "numPagoElectronico": None,
        },
        "extension": None,
        "apendice": None,
        "estadoDteAzDigital": estado_dte,
        "ventaIdInterno": venta_id,
    }
    return payload
