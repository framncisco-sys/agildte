# Programador: Oscar Amaya Romero
from __future__ import annotations

import json

TABLA = "pos_favoritos_sucursal"
MAX_ITEMS = 14
MAX_JSON_CHARS = 120_000

_KEYS_PERMITIDAS = frozenset(
    {
        "id",
        "nombre",
        "precio",
        "codigo",
        "fraccionable",
        "unidades_por_caja",
        "unidades_por_docena",
        "mh_codigo_unidad",
        "presentaciones",
        "promocion_tipo",
        "promocion_valor",
        "promocion_valor_comprar",
        "promocion_valor_pagar",
        "promocion_descuento_monto",
    }
)


def tabla_existe(cur) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (TABLA,),
    )
    return cur.fetchone() is not None


def sucursal_key(sucursal_id: int | None) -> int:
    """Clave numérica para agrupar favoritos (0 = usuario sin sucursal en sesión)."""
    if sucursal_id is None:
        return 0
    try:
        n = int(sucursal_id)
        return n if n > 0 else 0
    except (TypeError, ValueError):
        return 0


def _producto_pertenece_empresa(cur, producto_id: int, empresa_id: int) -> bool:
    cur.execute(
        "SELECT 1 FROM productos WHERE id = %s AND empresa_id = %s",
        (producto_id, empresa_id),
    )
    return cur.fetchone() is not None


def _sanear_item(raw: dict, empresa_id: int, cur) -> dict | None:
    if not isinstance(raw, dict):
        return None
    try:
        pid = int(raw.get("id"))
    except (TypeError, ValueError):
        return None
    if pid <= 0 or not _producto_pertenece_empresa(cur, pid, empresa_id):
        return None
    out: dict = {"id": pid}
    for k in _KEYS_PERMITIDAS:
        if k == "id":
            continue
        if k not in raw:
            continue
        v = raw[k]
        if k == "nombre" and v is not None:
            out[k] = str(v)[:500]
        elif k == "codigo" and v is not None:
            out[k] = str(v)[:80]
        elif k == "precio":
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                out[k] = 0.0
        elif k == "fraccionable":
            out[k] = bool(v)
        elif k in ("unidades_por_caja", "unidades_por_docena"):
            if v is None:
                out[k] = None
            else:
                try:
                    out[k] = int(v)
                except (TypeError, ValueError):
                    out[k] = None
        elif k == "mh_codigo_unidad" and v is not None:
            out[k] = str(v)[:8]
        elif k == "presentaciones" and isinstance(v, list):
            out[k] = v[:50]
        elif k == "promocion_tipo" and v is not None:
            out[k] = str(v)[:32]
        elif k in ("promocion_valor", "promocion_valor_comprar", "promocion_valor_pagar", "promocion_descuento_monto"):
            try:
                out[k] = float(v) if v is not None else 0.0
            except (TypeError, ValueError):
                out[k] = 0.0
    return out


def obtener_favoritos_lista(cur, empresa_id: int, sucursal_id: int | None) -> list[dict]:
    if not tabla_existe(cur):
        return []
    sk = sucursal_key(sucursal_id)
    cur.execute(
        f"SELECT payload_json FROM {TABLA} WHERE empresa_id = %s AND sucursal_key = %s",
        (empresa_id, sk),
    )
    row = cur.fetchone()
    if not row or not row[0]:
        return []
    try:
        data = json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    vistos: set[int] = set()
    for raw in data[:MAX_ITEMS]:
        if not isinstance(raw, dict):
            continue
        item = _sanear_item(raw, empresa_id, cur)
        if item and item["id"] not in vistos:
            vistos.add(item["id"])
            out.append(item)
    return out


def guardar_favoritos_lista(
    cur,
    empresa_id: int,
    sucursal_id: int | None,
    items: list,
    usuario_id: int | None,
) -> tuple[list[dict], str | None]:
    """
    Valida y persiste favoritos. Retorna (lista_guardada, error_msg).
    """
    if not tabla_existe(cur):
        return [], "tabla_no_instalada"
    if not isinstance(items, list):
        return [], "formato_invalido"
    sk = sucursal_key(sucursal_id)
    limpio: list[dict] = []
    vistos: set[int] = set()
    for raw in items[:MAX_ITEMS]:
        if isinstance(raw, dict):
            item = _sanear_item(raw, empresa_id, cur)
            if item and item["id"] not in vistos:
                vistos.add(item["id"])
                limpio.append(item)
    js = json.dumps(limpio, ensure_ascii=False, separators=(",", ":"))
    if len(js) > MAX_JSON_CHARS:
        return [], "payload_demasiado_grande"
    uid = int(usuario_id) if usuario_id else None
    cur.execute(
        f"""
        INSERT INTO {TABLA} (empresa_id, sucursal_key, payload_json, actualizado_en, actualizado_por)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
        ON CONFLICT (empresa_id, sucursal_key)
        DO UPDATE SET
            payload_json = EXCLUDED.payload_json,
            actualizado_en = CURRENT_TIMESTAMP,
            actualizado_por = EXCLUDED.actualizado_por
        """,
        (empresa_id, sk, js, uid),
    )
    return limpio, None
