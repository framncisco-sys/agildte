# Programador: Oscar Amaya Romero
"""Token firmado (time-limited) para ver comprobante / JSON DTE sin iniciar sesión."""
from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SALT = "az-ticket-publico-v1"
MAX_AGE_SEGUNDOS = 60 * 60 * 24 * 7  # 7 días


def firmar_acceso_publico_venta(secret_key: str, venta_id: int, empresa_id: int) -> str:
    s = URLSafeTimedSerializer(str(secret_key), salt=SALT)
    return s.dumps({"v": int(venta_id), "e": int(empresa_id)})


def verificar_acceso_publico_venta(
    secret_key: str, token: str, max_age: int = MAX_AGE_SEGUNDOS
) -> tuple[int, int] | None:
    s = URLSafeTimedSerializer(str(secret_key), salt=SALT)
    try:
        data = s.loads(token, max_age=max_age)
        return int(data["v"]), int(data["e"])
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        return None
