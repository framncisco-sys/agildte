# Programador: Oscar Amaya Romero
"""Fecha y hora según calendario de El Salvador (America/El_Salvador, UTC−6)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


def ahora_sv() -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("America/El_Salvador"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=-6)))


def hoy_sv() -> date:
    return ahora_sv().date()


def hoy_sv_str() -> str:
    return hoy_sv().isoformat()


def ahora_sv_naive() -> datetime:
    """Timestamp naive para PostgreSQL: siempre hora local de El Salvador."""
    return ahora_sv().replace(tzinfo=None)


def fecha_hora_desde_registro(dt: datetime | date | None) -> tuple[str, str, str]:
    """
    (fecha YYYY-MM-DD, hora HH:MM:SS, periodo YYYY-MM) en calendario SV.
    Los valores naive en BD se interpretan como hora local de El Salvador.
    """
    ahora = ahora_sv()
    if dt is None:
        return ahora.date().isoformat(), ahora.strftime("%H:%M:%S"), ahora.strftime("%Y-%m")
    if isinstance(dt, datetime):
        fe = dt.date().isoformat()
        hora = dt.strftime("%H:%M:%S")
        return fe, hora, fe[:7]
    fe = dt.isoformat()
    return fe, "12:00:00", fe[:7]


def formatear_fecha_hora_ticket(dt: datetime | date | None) -> str:
    """Formato DD/MM/YYYY HH:MI AM para tickets (calendario SV)."""
    if dt is None:
        dt = ahora_sv_naive()
    elif isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.strftime("%d/%m/%Y") + " 12:00 PM"
    hora_12 = dt.strftime("%I:%M %p").lstrip("0")
    return f"{dt.strftime('%d/%m/%Y')} {hora_12}"
