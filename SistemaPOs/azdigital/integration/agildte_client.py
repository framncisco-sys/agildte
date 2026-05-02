# Programador: Oscar Amaya Romero
"""
Cliente HTTP para el backend central Django REST (AgilDTE / prefijo /api/).

Configuración (variables de entorno; sin credenciales en código):
  - AGILDTE_BASE_URL o VITE_AGILDTE_BASE_URL: URL base HTTPS (sin barra final).
    Ej.: https://api.midominio.com
  - En peticiones HTTP con sesión Flask: si el usuario entró vía SSO AgilDTE, se usa el JWT
    guardado en sesión (agildte_access_token) y empresa_id del mismo usuario (multi-empresa).
  - AGILDTE_USERNAME / AGILDTE_PASSWORD: opcional; fallback para workers sin sesión o automatización.

Autenticación:
  - POST {BASE}/api/auth/login/ con JSON {"username"|"email", "password"}
  - Cabecera Authorization: Bearer <access>
  - Renovación: POST {BASE}/api/token/refresh/ con {"refresh": "<refresh>"}

Multi-empresa:
  - empresa_id proviene del login (empresa_default.id) o de la selección del usuario.
  - En cada petición se envía en query (?empresa_id=) o en el cuerpo (empresa / empresa_id)
    según el endpoint; este cliente no usa X-Company-ID.

Equivale en frontend (Vite) a axios/fetch con interceptores de request/response:
  - request: adjuntar Bearer y, donde aplique, empresa_id.
  - response: si 401, intentar refresh y repetir una vez; si 403, empresa no permitida.

---------------------------------------------------------------------------
POST /api/ventas/crear-con-detalles/ — cuerpo JSON esperado (plantilla)

  El serializer real del backend puede nombrar campos distinto; ajuste
  `build_crear_venta_con_detalles_payload()` o el dict que le pasen tras
  validar contra el código Django (VentaCrearConDetallesSerializer o similar).

  Campos que suelen ser obligatorios en integraciones DTE El Salvador:

  empresa_id (int)
      Obligatorio. Debe coincidir con una empresa asignada al usuario JWT.

  tipo_dte (str)
      Código MH del documento, p. ej. "01" factura consumidor final, "03" crédito fiscal.

  tipo_pago (str)
      Ej. "EFECTIVO", "TARJETA", "TRANSFERENCIA" (según catálogo del backend).

  detalles (list[dict])
      Líneas de venta. Por ítem, el backend suele exigir al menos:
      - producto o producto_id (int): FK al catálogo central.
      - cantidad (number)
      - precio_unitario (number)
      - subtotal (number) o importe gravado según redondeo del serializer

  Cliente / receptor (según reglas del backend):
  - cliente (int, opcional): PK en /api/clientes/ del servidor central.
    Los IDs del POS local solo sirven si el catálogo es el mismo servidor.
  - O campos planos de receptor: nombre_receptor, tipo_documento, numero_documento,
    direccion, correo, telefono, nrc (si aplica CCF), etc.

  totales:
  - total (number), opcional descuento (number), total_bruto (number)

  Otros que algunos serializers exigen:
  - fecha_emision (ISO date), sucursal_id, observaciones, moneda ("USD"), etc.

  Tras crear la venta, el backend encola o ejecuta facturación (MH). Para inspeccionar JSON DTE:
  GET /api/ventas/<id>/generar-dte/?empresa_id=<id>

CORS: si el POS es navegador, el administrador del backend debe añadir el origen
en CORS_ALLOWED_ORIGINS. Apps nativas o este cliente Python no usan CORS.
---------------------------------------------------------------------------
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin

import httpx

# Prefijo API del backend central
API_PREFIX = "/api"

_logger = logging.getLogger(__name__)


def _datetime_el_salvador() -> datetime:
    """
    Reloj «oficial» para facturación SV: America/El_Salvador (UTC−6, sin DST desde 2021).
    Si falla zoneinfo (imagen mínima sin tzdata), usa UTC−6 fijo — mismo resultado práctico.
    """
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/El_Salvador"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=-6)))


def _fecha_hora_periodo_para_agildte(
    fecha_emision: str | None,
    periodo_aplicado: str | None,
) -> tuple[str, str, str]:
    """
    Devuelve (fecha_emision YYYY-MM-DD, hora_emision HH:MM:SS, periodo_aplicado YYYY-MM).
    Coincide con lo que exige el modelo Venta en AgilDTE; la fecha/periodo siguen el calendario
    de El Salvador aunque el servidor POS esté en otra zona.
    """
    dt_sv = _datetime_el_salvador()
    hora = dt_sv.strftime("%H:%M:%S")
    if fecha_emision and str(fecha_emision).strip():
        fe = str(fecha_emision).strip()[:10]
    else:
        fe = dt_sv.date().isoformat()
    if periodo_aplicado and str(periodo_aplicado).strip():
        pa = str(periodo_aplicado).strip()[:7]
    else:
        pa = fe[:7] if len(fe) >= 7 and fe[4:5] == "-" else dt_sv.strftime("%Y-%m")
    return fe, hora, pa


class AgilDTEAPIError(Exception):
    """Error HTTP o cuerpo no JSON del backend."""

    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class AgilDTEUnauthorizedError(AgilDTEAPIError):
    """401: token inválido o expirado; requiere login de nuevo."""


class AgilDTEForbiddenError(AgilDTEAPIError):
    """403: empresa no permitida u otro permiso denegado."""


class AgilDTEAuthError(AgilDTEAPIError):
    """Fallo en login o refresh."""


def resolve_agildte_base_url() -> str:
    """
    Lee la URL base desde entorno. Prioridad:
    AGILDTE_BASE_URL, luego VITE_AGILDTE_BASE_URL (mismo nombre que en Vite),
    luego VITE_AGILDTE_API_URL por compatibilidad.
    """
    for key in ("AGILDTE_BASE_URL", "VITE_AGILDTE_BASE_URL", "VITE_AGILDTE_API_URL"):
        v = (os.environ.get(key) or "").strip().rstrip("/")
        if v:
            return v
    return ""


@dataclass
class LoginProfile:
    """Perfil tras login: tokens y empresa por defecto (PerfilUsuario)."""

    access: str
    refresh: str | None
    empresa_default_id: int | None
    empresas_ids: list[int] = field(default_factory=list)
    raw_user: dict[str, Any] = field(default_factory=dict)


def _parse_empresa_from_login_user(user: dict[str, Any]) -> tuple[int | None, list[int]]:
    empresas_ids: list[int] = []
    default_id: int | None = None
    ed = user.get("empresa_default")
    if isinstance(ed, dict) and ed.get("id") is not None:
        try:
            default_id = int(ed["id"])
        except (TypeError, ValueError):
            default_id = None
    elif ed is not None and not isinstance(ed, dict):
        try:
            default_id = int(ed)
        except (TypeError, ValueError):
            default_id = None

    for key in ("empresas", "empresas_asignadas", "mis_empresas"):
        raw = user.get(key)
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and item.get("id") is not None:
                    try:
                        empresas_ids.append(int(item["id"]))
                    except (TypeError, ValueError):
                        pass
                else:
                    try:
                        empresas_ids.append(int(item))
                    except (TypeError, ValueError):
                        pass
            break

    if default_id is not None and default_id not in empresas_ids:
        empresas_ids.insert(0, default_id)
    return default_id, empresas_ids


def _parse_empresa_lists_from_root(data: dict[str, Any]) -> tuple[int | None, list[int]]:
    """
    AgilDTE devuelve `empresa_default` y a veces `empresas` en la raíz del JSON de login,
    no dentro de `user`.
    """
    default_id: int | None = None
    ed = data.get("empresa_default")
    if isinstance(ed, dict) and ed.get("id") is not None:
        try:
            default_id = int(ed["id"])
        except (TypeError, ValueError):
            default_id = None

    empresas_ids: list[int] = []
    for key in ("empresas", "empresas_asignadas", "mis_empresas"):
        raw = data.get(key)
        if not isinstance(raw, list):
            continue
        for item in raw:
            if isinstance(item, dict) and item.get("id") is not None:
                try:
                    empresas_ids.append(int(item["id"]))
                except (TypeError, ValueError):
                    pass
            else:
                try:
                    empresas_ids.append(int(item))
                except (TypeError, ValueError):
                    pass
        break

    if default_id is not None and default_id not in empresas_ids:
        empresas_ids.insert(0, default_id)
    return default_id, empresas_ids


def _merge_empresa_login_context(data: dict[str, Any], user: dict[str, Any]) -> tuple[int | None, list[int]]:
    """Combina empresa desde objeto `user` y desde la raíz de la respuesta (formato AgilDTE)."""
    d_user, ids_user = _parse_empresa_from_login_user(user)
    d_root, ids_root = _parse_empresa_lists_from_root(data)
    default_eid = d_user if d_user is not None else d_root
    merged: list[int] = []
    seen: set[int] = set()
    for eid in ids_user + ids_root:
        if eid not in seen:
            seen.add(eid)
            merged.append(eid)
    if default_eid is not None and default_eid not in seen:
        merged.insert(0, default_eid)
    return default_eid, merged


def map_tipo_comprobante_pos_a_tipo_dte(tipo_comp: str) -> str:
    """Mapeo POS local (Flask) → código tipo DTE MH común."""
    tc = (tipo_comp or "").strip().upper()
    if tc == "CREDITO_FISCAL":
        return "03"
    if tc == "FACTURA":
        return "01"
    # TICKET u otros: muchos backends usan factura CF o documento interno; ajustar si su API exige otro código.
    return "01"


def map_tipo_comprobante_pos_a_tipo_venta(tipo_comp: str) -> str:
    """POS (Flask) → Venta.tipo_venta del backend (CF / CCF), alineado con tipo_dte MH."""
    tc = (tipo_comp or "").strip().upper()
    if tc == "CREDITO_FISCAL":
        return "CCF"
    return "CF"


def receptor_anidado_a_campos_serializer(receptor: dict[str, Any] | None) -> dict[str, Any]:
    """
    Convierte el dict anidado del POS a campos que consume VentaConDetallesSerializer
    (nombre_receptor, documento_receptor, receptor_correo, etc.).
    """
    if not receptor or not isinstance(receptor, dict):
        return {}
    out: dict[str, Any] = {}
    nombre = (receptor.get("nombre") or "").strip()
    if nombre:
        out["nombre_receptor"] = nombre
    tipo_doc = (receptor.get("tipo_documento") or "").strip().upper() or "NIT"
    out["tipo_doc_receptor"] = tipo_doc
    num = (receptor.get("numero_documento") or "").strip()
    if num:
        out["documento_receptor"] = num
        out["nit_receptor"] = num
    nrc = (receptor.get("nrc") or "").strip()
    if nrc:
        out["nrc_receptor"] = nrc
    correo = (receptor.get("correo") or "").strip()
    if correo:
        out["receptor_correo"] = correo
    direccion = (receptor.get("direccion") or "").strip()
    if direccion:
        out["receptor_direccion"] = direccion
    telefono = (receptor.get("telefono") or "").strip()
    if telefono:
        out["receptor_telefono"] = telefono
    return out


class AgilDTEClient:
    """
    Cliente síncrono con Bearer, refresh ante 401 y empresa_id en listados/escrituras.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 60.0,
        empresa_id: int | None = None,
    ):
        self.base_url = (base_url or resolve_agildte_base_url()).rstrip("/")
        if not self.base_url:
            raise AgilDTEAuthError("Falta AGILDTE_BASE_URL (o VITE_AGILDTE_BASE_URL) en el entorno.")
        self.timeout = timeout
        self._access: str | None = None
        self._refresh: str | None = None
        self._profile: LoginProfile | None = None
        self._empresa_id_explicit: int | None = empresa_id

    @property
    def empresa_id(self) -> int | None:
        if self._empresa_id_explicit is not None:
            return self._empresa_id_explicit
        if self._profile and self._profile.empresa_default_id is not None:
            return self._profile.empresa_default_id
        return None

    def set_empresa_id(self, empresa_id: int | None) -> None:
        """Fija tenant para peticiones (p. ej. usuario eligió otra empresa)."""
        self._empresa_id_explicit = empresa_id

    def _url(self, path: str) -> str:
        p = path if path.startswith("/") else f"/{path}"
        return urljoin(self.base_url + "/", p.lstrip("/"))

    def login(self, username_or_email: str, password: str) -> LoginProfile:
        """POST /api/auth/login/"""
        payload: dict[str, str] = {}
        u = (username_or_email or "").strip()
        if "@" in u:
            payload["email"] = u
        else:
            payload["username"] = u
        payload["password"] = password
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(self._url(f"{API_PREFIX}/auth/login/"), json=payload)
        if r.status_code >= 400:
            raise AgilDTEAuthError(
                f"Login fallido ({r.status_code}): {r.text[:500]}",
                status_code=r.status_code,
                body=_safe_json(r),
            )
        data = r.json() if r.content else {}
        access = data.get("access") or data.get("token")
        refresh = data.get("refresh")
        if not access:
            raise AgilDTEAuthError("Respuesta de login sin access/token JWT.", body=data)
        user = data.get("user") or data.get("usuario") or data.get("perfil") or {}
        if not isinstance(user, dict):
            user = {}
        default_eid, empresas = _merge_empresa_login_context(data, user)
        self._access = access
        self._refresh = refresh
        self._profile = LoginProfile(
            access=access,
            refresh=refresh,
            empresa_default_id=default_eid,
            empresas_ids=empresas,
            raw_user=user,
        )
        if self._empresa_id_explicit is None and default_eid is not None:
            self._empresa_id_explicit = default_eid
        return self._profile

    def _refresh_access(self) -> bool:
        if not self._refresh:
            return False
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(
                self._url(f"{API_PREFIX}/token/refresh/"),
                json={"refresh": self._refresh},
            )
        if r.status_code >= 400:
            return False
        data = r.json() if r.content else {}
        new_access = data.get("access")
        if not new_access:
            return False
        self._access = new_access
        if self._profile:
            self._profile.access = new_access
        return True

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        data: Any = None,
        _retry_on_401: bool = True,
        timeout: float | None = None,
    ) -> httpx.Response:
        if not self._access:
            raise AgilDTEUnauthorizedError("No autenticado: llame a login() primero.")
        headers = {"Authorization": f"Bearer {self._access}"}
        url = self._url(path)
        effective_timeout = self.timeout if timeout is None else timeout
        with httpx.Client(timeout=effective_timeout) as c:
            r = c.request(
                method.upper(),
                url,
                params=params,
                json=json_body,
                data=data,
                headers=headers,
            )
        if r.status_code == 401 and _retry_on_401:
            if self._refresh_access():
                return self.request(
                    method,
                    path,
                    params=params,
                    json_body=json_body,
                    data=data,
                    _retry_on_401=False,
                    timeout=timeout,
                )
            raise AgilDTEUnauthorizedError(
                "401: sesión expirada o token inválido; vuelva a autenticarse.",
                status_code=401,
                body=_safe_json(r),
            )
        if r.status_code == 403:
            raise AgilDTEForbiddenError(
                "403: sin permiso para esta empresa u operación.",
                status_code=403,
                body=_safe_json(r),
            )
        return r

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        r = self.request("GET", path, params=params)
        if r.status_code >= 400:
            _raise_for_status(r)
        return r.json() if r.content else None

    def post_json(self, path: str, json_body: Any, params: dict[str, Any] | None = None) -> Any:
        r = self.request("POST", path, params=params, json_body=json_body)
        if r.status_code >= 400:
            _raise_for_status(r)
        return r.json() if r.content else None

    def post_json_timeout(
        self,
        path: str,
        json_body: Any,
        *,
        params: dict[str, Any] | None = None,
        timeout: float = 600.0,
    ) -> Any:
        """POST con timeout extendido (p. ej. procesar contingencia completa en AgilDTE)."""
        r = self.request("POST", path, params=params, json_body=json_body, timeout=timeout)
        if r.status_code >= 400:
            _raise_for_status(r)
        return r.json() if r.content else None

    def procesar_contingencia_completa_agildte(
        self,
        empresa_id: int,
        body: dict[str, Any] | None = None,
        *,
        timeout: float = 600.0,
    ) -> Any:
        """
        Igual que el botón «Desactivar y enviar pendientes» / modal en AgilDTE (frontend-saas):
        POST /api/empresas/{id}/procesar-contingencia-completa/
        Body opcional: { tipoContingencia: 1-5, motivo: "..." }
        """
        eid = int(empresa_id)
        payload = dict(body or {})
        return self.post_json_timeout(
            f"{API_PREFIX}/empresas/{eid}/procesar-contingencia-completa/",
            json_body=payload,
            timeout=timeout,
        )

    def merge_empresa_params(self, params: dict[str, Any] | None) -> dict[str, Any]:
        """Añade empresa_id a query params si falta y hay tenant conocido."""
        out = dict(params or {})
        eid = self.empresa_id
        if eid is not None and "empresa_id" not in out and "empresa" not in out:
            out["empresa_id"] = eid
        return out

    def list_productos(self, extra_params: dict[str, Any] | None = None) -> Any:
        return self.get_json(f"{API_PREFIX}/productos/", params=self.merge_empresa_params(extra_params))

    def list_clientes(self, extra_params: dict[str, Any] | None = None) -> Any:
        return self.get_json(f"{API_PREFIX}/clientes/", params=self.merge_empresa_params(extra_params))

    def create_cliente(self, body: dict[str, Any]) -> Any:
        b = dict(body)
        eid = self.empresa_id
        if eid is not None:
            b.setdefault("empresa_id", eid)
            b.setdefault("empresa", eid)
        return self.post_json(f"{API_PREFIX}/clientes/", json_body=b)

    def crear_venta_con_detalles(self, body: dict[str, Any]) -> Any:
        b = dict(body)
        eid = self.empresa_id
        if eid is not None:
            b.setdefault("empresa_id", eid)
            b.setdefault("empresa", eid)
        return self.post_json(f"{API_PREFIX}/ventas/crear-con-detalles/", json_body=b)

    def procesar_venta_pos(self, body: dict[str, Any]) -> Any:
        """
        POST /api/pos/procesar-venta/ — mismo cuerpo que crear-con-detalles;
        respuesta normalizada { ok, mensaje, venta } para el POS.
        Timeout largo (AgilDTE espera respuesta MH en modo síncrono).
        """
        b = dict(body)
        eid = self.empresa_id
        if eid is not None:
            b.setdefault("empresa_id", eid)
            b.setdefault("empresa", eid)
        raw = (os.environ.get("AGILDTE_POS_VENTA_TIMEOUT") or "180").strip() or "180"
        try:
            to = max(30.0, float(raw))
        except ValueError:
            to = 180.0
        return self.post_json_timeout(
            f"{API_PREFIX}/pos/procesar-venta/", json_body=b, timeout=to
        )

    def generar_dte_venta(self, venta_id: int, extra_params: dict[str, Any] | None = None) -> Any:
        """
        GET /api/ventas/{id}/generar-dte/ — JSON DTE (diagnóstico o ya firmado).
        La facturación ante MH se dispara al crear la venta con crear-con-detalles.
        """
        params = self.merge_empresa_params(extra_params)
        return self.get_json(
            f"{API_PREFIX}/ventas/{int(venta_id)}/generar-dte/",
            params=params,
        )


def _safe_json(r: httpx.Response) -> Any:
    try:
        return r.json()
    except Exception:
        return (r.text or "")[:2000]


def _format_api_error_body(body: Any) -> str:
    """Texto legible para mostrar en el POS (Django: detail, serializer errors, pos/procesar-venta, MH)."""
    if body is None:
        return ""

    def _mh_desde_venta(v: dict[str, Any]) -> str | None:
        """Extrae mensajes de rechazo / observaciones MH del objeto venta serializado."""
        if not isinstance(v, dict):
            return None
        partes: list[str] = []
        m = v.get("mensaje")
        if m is not None and str(m).strip():
            partes.append(str(m).strip())
        omh = v.get("observaciones_mh")
        if isinstance(omh, dict):
            cod = omh.get("codigo")
            desc = omh.get("descripcion")
            obs = omh.get("observaciones") or []
            if cod is not None or desc:
                partes.append(f"MH: código={cod} — {desc or ''}".strip())
            if isinstance(obs, list) and obs:
                partes.append("Observaciones MH: " + "; ".join(str(x) for x in obs[:12]))
            elif obs and not isinstance(obs, list):
                partes.append(f"Observaciones MH: {obs}")
        elif omh is not None and str(omh).strip():
            partes.append(str(omh).strip())
        estado = (v.get("estado_dte") or "").strip()
        if estado in ("RechazadoMH", "ErrorEnvio"):
            partes.append(f"Estado DTE: {estado}")
        return " | ".join(p for p in partes if p)[:2000] if partes else None

    if isinstance(body, dict):
        # POST /api/pos/procesar-venta/ con ok=false (400) — mensaje puede venir vacío
        if body.get("ok") is False:
            top = body.get("mensaje")
            if top is not None and str(top).strip():
                return str(top).strip()[:2000]
            venta = body.get("venta")
            nested = _mh_desde_venta(venta) if isinstance(venta, dict) else None
            if nested:
                return nested
            if top is not None:
                return str(top)[:2000]
        if "detail" in body and body["detail"] is not None:
            d = body["detail"]
            return str(d)[:2000] if not isinstance(d, (dict, list)) else json.dumps(d, ensure_ascii=False)[:2000]
        if "mensaje" in body and body["mensaje"] is not None and str(body["mensaje"]).strip():
            return str(body["mensaje"]).strip()[:2000]
        if "error" in body and body["error"] is not None:
            return str(body["error"])[:2000]
        # Errores de serializer anidados (detalles[0].producto_id, …)
        try:
            return json.dumps(body, ensure_ascii=False)[:2000]
        except Exception:
            return str(body)[:2000]
    if isinstance(body, str):
        return body.strip()[:2000]
    if isinstance(body, (list, tuple)):
        try:
            return json.dumps(body, ensure_ascii=False)[:2000]
        except Exception:
            return str(body)[:2000]
    return str(body)[:2000]


def _raise_for_status(r: httpx.Response) -> None:
    code = r.status_code
    raw_text = (getattr(r, "text", None) or "")[:4000]
    body = _safe_json(r)
    detail = _format_api_error_body(body)
    if not (detail or "").strip() and raw_text.strip():
        detail = raw_text.strip()[:2000]
    if detail:
        msg = f"Error API ({code}): {detail}"
    else:
        msg = f"Error API ({code})"
    if code == 401:
        raise AgilDTEUnauthorizedError(msg, status_code=code, body=body)
    if code == 403:
        raise AgilDTEForbiddenError(msg, status_code=code, body=body)
    raise AgilDTEAPIError(msg, status_code=code, body=body)


def _nombre_cf_ticket_default() -> str:
    """Nombre receptor para Ticket (FCF anónimo) — configurable vía POSAGIL_NOMBRE_CF_TICKET."""
    v = (os.environ.get("POSAGIL_NOMBRE_CF_TICKET") or "").strip()
    return v or "Cliente de contado"


def build_crear_venta_con_detalles_payload(
    *,
    empresa_id: int,
    tipo_comprobante_pos: str,
    tipo_pago: str,
    lineas: list[Any],
    total_neto: float,
    total_bruto: float,
    descuento: float,
    cliente_id: int | None,
    cliente_nombre_ticket: str,
    receptor: dict[str, Any] | None = None,
    venta_local_id: int | None = None,
    fecha_emision: str | None = None,
    periodo_aplicado: str | None = None,
) -> dict[str, Any]:
    """
    Construye el JSON para POST /api/ventas/crear-con-detalles/.

    `lineas` puede ser lista de LineaVenta (ventas_service) o dicts con
    producto_id, cantidad, precio_unitario, subtotal.

    `receptor`: datos del comprador si el backend no usa solo cliente_id.
    Si no se pasa y hay cliente_id, se envía cliente=<id> para el catálogo central.

    Incluye referencia_externa con el id local de venta para trazabilidad (ignorable por el backend).

    fecha_emision / periodo_aplicado: opcionales (YYYY-MM-DD y YYYY-MM). Por defecto se usan
    fecha y mes según America/El_Salvador (no la zona del servidor), para MH/libros contables.
    """
    tc_pos = (tipo_comprobante_pos or "").strip().upper()
    es_ticket = tc_pos == "TICKET"
    tipo_dte = map_tipo_comprobante_pos_a_tipo_dte(tipo_comprobante_pos)
    tipo_venta = map_tipo_comprobante_pos_a_tipo_venta(tipo_comprobante_pos)
    detalles: list[dict[str, Any]] = []
    for ln in lineas:
        if hasattr(ln, "producto_id"):
            pid = int(ln.producto_id)
            cant = float(ln.cantidad)
            pu = float(ln.precio_unitario)
            st = float(ln.subtotal)
        elif isinstance(ln, dict):
            pid = int(ln.get("producto_id") or ln.get("producto") or ln.get("id"))
            cant = float(ln.get("cantidad", 0))
            pu = float(ln.get("precio_unitario", 0))
            st = float(ln.get("subtotal", cant * pu))
        else:
            continue
        detalles.append(
            {
                "producto_id": pid,
                "cantidad": cant,
                "precio_unitario": round(pu, 8),
                "subtotal": round(st, 2),
            }
        )

    # Ticket en POS = Factura Consumidor Final (DTE 01) en AgilDTE; sin cliente de catálogo = receptor genérico
    # sin documento (el serializer Django aplica CASO CF sin cliente_id).
    if es_ticket and cliente_id is None:
        nombre_rec = _nombre_cf_ticket_default()
    elif es_ticket:
        nombre_rec = (cliente_nombre_ticket or _nombre_cf_ticket_default()).strip() or _nombre_cf_ticket_default()
    else:
        nombre_rec = (cliente_nombre_ticket or "Consumidor Final").strip() or "Consumidor Final"

    fe_iso, hora_sv, periodo = _fecha_hora_periodo_para_agildte(fecha_emision, periodo_aplicado)

    body: dict[str, Any] = {
        "empresa_id": empresa_id,
        "empresa": empresa_id,
        "tipo_dte": tipo_dte,
        "tipo_venta": tipo_venta,
        "tipo_pago": (tipo_pago or "EFECTIVO").strip().upper(),
        "detalles": detalles,
        "total": round(float(total_neto), 2),
        "total_bruto": round(float(total_bruto), 2),
        "descuento": round(float(descuento or 0), 2),
        "nombre_receptor": nombre_rec,
        "fecha_emision": fe_iso,
        "periodo_aplicado": periodo,
        "hora_emision": hora_sv,
    }
    if cliente_id is not None:
        body["cliente"] = int(cliente_id)
        body["cliente_id"] = int(cliente_id)
    # Receptor anidado solo con cliente de catálogo; para CF anónimo no enviar NIT/DUI vacíos.
    if receptor:
        body.update(receptor_anidado_a_campos_serializer(receptor))
    if venta_local_id is not None:
        body["referencia_externa"] = f"pos-local-{venta_local_id}"
    return body


def client_from_env() -> AgilDTEClient:
    """Instancia cliente con URL de entorno y opcional AGILDTE_EMPRESA_ID para forzar tenant."""
    raw_eid = (os.environ.get("AGILDTE_EMPRESA_ID") or "").strip()
    eid = int(raw_eid) if raw_eid.isdigit() else None
    return AgilDTEClient(empresa_id=eid)


def try_agildte_login_into_session(session_mod: Any, username: str, password: str) -> bool:
    """
    Tras login local en el POS: intenta POST /api/auth/login/ en AgilDTE con las mismas credenciales.
    Si coinciden con Django, guarda access/refresh en sesión (útil sin AGILDTE_USERNAME/PASSWORD en Docker).
    """
    if not resolve_agildte_base_url():
        return False
    u = (username or "").strip()
    p = password or ""
    if not u or not p:
        return False
    try:
        cli = client_from_env()
        prof = cli.login(u, p)
    except (AgilDTEAuthError, AgilDTEAPIError, OSError, ValueError, TypeError) as exc:
        _logger.debug("try_agildte_login_into_session omitido: %s", exc)
        return False
    except Exception as exc:
        _logger.debug("try_agildte_login_into_session error: %s", exc)
        return False
    session_mod["agildte_access_token"] = prof.access
    if prof.refresh:
        session_mod["agildte_refresh_token"] = prof.refresh
    session_mod["_agildte_role_sync_ts"] = time.time()
    if prof.empresa_default_id is not None:
        try:
            session_mod["empresa_id"] = int(prof.empresa_default_id)
        except (TypeError, ValueError):
            pass
    return True


def client_with_bearer_and_empresa(
    access_token: str,
    empresa_id: int | None,
    *,
    refresh_token: str | None = None,
) -> AgilDTEClient:
    """Cliente con JWT ya emitido (usuario que inició sesión vía portal AgilDTE / SSO)."""
    tok = (access_token or "").strip()
    if not tok:
        raise AgilDTEAuthError("Token AgilDTE vacío.")
    cli = AgilDTEClient(empresa_id=empresa_id)
    cli._access = tok
    cli._refresh = (refresh_token or "").strip() or None
    empresas_ids = [int(empresa_id)] if empresa_id is not None else []
    cli._profile = LoginProfile(
        access=tok,
        refresh=cli._refresh,
        empresa_default_id=empresa_id,
        empresas_ids=empresas_ids,
        raw_user={},
    )
    return cli


def _bearer_desde_cabecera_authorization() -> str | None:
    """Authorization: Bearer <jwt> (API o fetch que envíe el token explícitamente)."""
    try:
        from flask import has_request_context, request
    except ImportError:
        return None
    if not has_request_context():
        return None
    h = (request.headers.get("Authorization") or "").strip()
    if len(h) >= 8 and h[:7].lower() == "bearer ":
        t = h[7:].strip()
        return t or None
    return None


def login_client_from_request_or_env() -> AgilDTEClient:
    """
    Obtiene cliente autenticado contra AgilDTE:
    1) Sesión Flask: agildte_access_token + empresa_id (SSO «Abrir PosAgil»).
    2) Cabecera Authorization: Bearer … (misma sesión u otra integración).
    3) POST /api/auth/login/ con AGILDTE_USERNAME y AGILDTE_PASSWORD (Docker, cron).
    """
    try:
        from flask import has_request_context, session as flask_session
    except ImportError:
        return login_client_from_env()
    if not has_request_context():
        return login_client_from_env()
    token = (flask_session.get("agildte_access_token") or "").strip()
    if not token:
        token = (_bearer_desde_cabecera_authorization() or "").strip()
    if not token:
        return login_client_from_env()
    eid_raw = flask_session.get("empresa_id")
    try:
        eid = int(eid_raw) if eid_raw is not None else None
    except (TypeError, ValueError):
        eid = None
    if eid is None:
        raw_eid = (os.environ.get("AGILDTE_EMPRESA_ID") or "").strip()
        if raw_eid.isdigit():
            try:
                eid = int(raw_eid)
            except (TypeError, ValueError):
                eid = None
    rt = (flask_session.get("agildte_refresh_token") or "").strip() or None
    return client_with_bearer_and_empresa(token, eid, refresh_token=rt)


def _raise_missing_service_credentials_error() -> None:
    """Faltan credenciales de servicio y no hay JWT en la petición actual."""
    raise AgilDTEAuthError(
        "No hay sesión AgilDTE (JWT). Opciones: (1) Entrar desde el portal «Abrir PosAgil»; "
        "(2) Login local en /login con el mismo usuario y contraseña que en AgilDTE (se guarda el token solo); "
        "(3) Definir AGILDTE_USERNAME y AGILDTE_PASSWORD en el servidor. "
        "Si usa Docker, reconstruya la imagen tras actualizar el código: docker compose build posagil."
    )


def login_client_from_env() -> AgilDTEClient:
    """
    Crea cliente, lee AGILDTE_USERNAME y AGILDTE_PASSWORD, ejecuta login.
    """
    user = (os.environ.get("AGILDTE_USERNAME") or os.environ.get("AGILDTE_USER") or "").strip()
    password = os.environ.get("AGILDTE_PASSWORD") or ""
    if not user or not password:
        _raise_missing_service_credentials_error()
    cli = client_from_env()
    cli.login(user, password)
    return cli


def debe_generar_dte_remoto(tipo_comprobante_pos: str) -> bool:
    """Regla por defecto: documentos fiscalizables en MH (incl. Ticket = FCF DTE-01)."""
    tc = (tipo_comprobante_pos or "").strip().upper()
    return tc in ("FACTURA", "CREDITO_FISCAL", "TICKET")

