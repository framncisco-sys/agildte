# Programador: Oscar Amaya Romero
from __future__ import annotations

from werkzeug.security import check_password_hash


def verificar_password(stored_hash_or_plain: str, password_input: str) -> bool:
    stored = (stored_hash_or_plain or "").strip()
    if not stored:
        return False
    ok = False
    try:
        ok = check_password_hash(stored, password_input)
    except Exception:
        ok = False
    return ok

