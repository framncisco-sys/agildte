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
