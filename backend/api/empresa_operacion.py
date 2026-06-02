# Programador: Oscar Amaya Romero
"""Cambio de modo operación (prueba / online) y reinicio de correlativos DTE."""
from __future__ import annotations

from django.utils import timezone

from .models import Correlativo, Empresa

TIPOS_DTE_CORRELATIVO = ("01", "03", "14", "05", "06", "07", "08", "09", "11", "15")


def modo_desde_ambiente(ambiente: str | None) -> str:
    return "online" if (ambiente or "01").strip() == "00" else "prueba"


def ambiente_desde_modo(modo: str) -> str:
    return "00" if (modo or "").strip().lower() == "online" else "01"


def resetear_correlativos_dte(empresa: Empresa, anio: int | None = None) -> int:
    """Pone en cero los correlativos DTE del año indicado (todos los tipos conocidos)."""
    anio = anio or timezone.localdate().year
    Correlativo.objects.filter(empresa=empresa, anio=anio).update(ultimo_correlativo=0)
    for td in TIPOS_DTE_CORRELATIVO:
        obj, _ = Correlativo.objects.get_or_create(
            empresa=empresa,
            tipo_dte=td,
            anio=anio,
            defaults={"ultimo_correlativo": 0},
        )
        if obj.ultimo_correlativo != 0:
            obj.ultimo_correlativo = 0
            obj.save(update_fields=["ultimo_correlativo", "fecha_actualizacion"])
    return Correlativo.objects.filter(empresa=empresa, anio=anio).count()
