# Programador: Oscar Amaya Romero
"""SAVEPOINT para consultas opcionales sin abortar toda la transacción PostgreSQL."""
from __future__ import annotations

import uuid
from typing import Callable, TypeVar

T = TypeVar("T")


def _nombre_savepoint(prefix: str = "sp") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def sql_opcional(cur, fn: Callable[[], T], default: T | None = None) -> T | None:
    """
    Ejecuta fn() dentro de un SAVEPOINT.
    Si falla (p. ej. columna inexistente), revierte solo ese bloque y devuelve default.
    Evita «current transaction is aborted, commands ignored until end of transaction block».
    """
    sp = _nombre_savepoint("spopt")
    cur.execute(f"SAVEPOINT {sp}")
    try:
        out = fn()
        cur.execute(f"RELEASE SAVEPOINT {sp}")
        return out
    except Exception:
        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        return default
