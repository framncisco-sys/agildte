"""
Validación opcional del JSON DTE contra schemas oficiales MH (svfe-json-schemas).

Uso: antes de firmar/enviar, detectar errores estructurales locales.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMAS_ROOT = Path(__file__).resolve().parents[1] / 'schemas' / 'mh'

# tipoDte -> ruta relativa al schema oficial local
SCHEMA_BY_TIPO = {
    '01': 'v2/fe-f-v2.json',
    '03': 'v4/fe-ccf-v4.json',
    '05': 'v4/fe-nc-v4.json',
    '06': 'v4/fe-nd-v4.json',
    '07': 'v2/fe-cr-v2.json',
    '08': 'v2/fe-cl-v2.json',
    '09': 'v2/fe-dcl-v2.json',
    '11': 'v3/fe-fex-v3.json',
    '14': 'v2/fe-fse-v2.json',
    '15': 'v2/fe-cd-v2.json',
}


class MhSchemaValidationError(ValueError):
    """JSON DTE no cumple el schema oficial MH local."""

    def __init__(self, message: str, *, errores: list[str] | None = None):
        super().__init__(message)
        self.errores = errores or []


def _floats_a_decimal(obj: Any) -> Any:
    """
    jsonschema + multipleOf 0.01 falla con floats binarios (ej. 39.55).
    Convertimos floats del DTE a Decimal; los enteros se dejan intactos.
    """
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _floats_a_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_floats_a_decimal(v) for v in obj]
    return obj


@lru_cache(maxsize=16)
def _cargar_schema(rel_path: str) -> dict[str, Any]:
    path = SCHEMAS_ROOT / rel_path
    if not path.is_file():
        raise FileNotFoundError(f'Schema MH no encontrado: {path}')
    with path.open(encoding='utf-8') as fh:
        # multipleOf como Decimal evita la ruta float de jsonschema (39.55 % 0.01).
        return json.load(fh, parse_float=Decimal)


def resolver_schema_path(tipo_dte: str) -> str | None:
    tipo = str(tipo_dte or '').strip().zfill(2)
    return SCHEMA_BY_TIPO.get(tipo)


def validar_dte_contra_schema(
    json_dte: dict[str, Any],
    *,
    tipo_dte: str | None = None,
    strict: bool = True,
) -> list[str]:
    """
    Valida el DTE contra el schema oficial local.

    Returns:
        Lista de errores legibles (vacía si OK).

    Raises:
        MhSchemaValidationError si strict=True y hay errores.
        ImportError si falta la dependencia jsonschema.
    """
    try:
        from jsonschema import Draft7Validator
    except ImportError as exc:
        msg = (
            'Falta dependencia jsonschema. Instale con: pip install jsonschema'
        )
        if strict:
            raise MhSchemaValidationError(msg) from exc
        logger.warning(msg)
        return [msg]

    tipo = str(
        tipo_dte
        or (json_dte.get('identificacion') or {}).get('tipoDte')
        or ''
    ).strip().zfill(2)
    rel = resolver_schema_path(tipo)
    if not rel:
        msg = f'No hay schema local registrado para tipoDte={tipo}'
        if strict:
            raise MhSchemaValidationError(msg, errores=[msg])
        return [msg]

    schema = _cargar_schema(rel)
    validator = Draft7Validator(schema)
    instancia = _floats_a_decimal(json_dte)
    errores: list[str] = []
    for err in sorted(validator.iter_errors(instancia), key=lambda e: list(e.path)):
        ruta = '.'.join(str(p) for p in err.path) or '(raíz)'
        errores.append(f'{ruta}: {err.message}')
        if len(errores) >= 25:
            errores.append('… (más errores omitidos)')
            break

    if errores and strict:
        raise MhSchemaValidationError(
            f'DTE {tipo} no cumple schema MH ({rel}): {errores[0]}',
            errores=errores,
        )
    return errores
