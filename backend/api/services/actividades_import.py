"""
Importación del catálogo MH de actividades económicas (CSV ; o Excel).
Formato MH habitual: CÓDIGO;ACTIVIDADES ECONÓMICAS
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import BinaryIO

from django.db import transaction

from api.models import ActividadEconomica


def codigo_es_numerico(val) -> bool:
    if val is None:
        return False
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return False
    return bool(re.match(r"^[\d.]+$", s))


def _normalizar_fila(row: list) -> tuple[str, str] | None:
    if len(row) < 2:
        return None
    codigo_raw = (row[0] or "").strip()
    descripcion = (row[1] or "").strip()
    if not codigo_es_numerico(codigo_raw):
        return None
    codigo = codigo_raw.replace(".", "")[:10]
    if not codigo:
        return None
    if not descripcion:
        descripcion = codigo
    return codigo, descripcion[:255]


def _leer_csv_texto(content: str) -> list[list[str]]:
    """Prueba delimitador ; (MH) y luego ,."""
    sample = content[:4096]
    delim = ";" if sample.count(";") >= sample.count(",") else ","
    return list(csv.reader(io.StringIO(content), delimiter=delim))


def parse_rows_from_bytes(content: bytes, filename: str = "") -> list[list[str]]:
    """Devuelve filas [codigo, descripcion] ya filtradas de encabezados."""
    nombre = (filename or "").lower()
    rows_raw: list[list[str]] = []

    if nombre.endswith(".xlsx") or nombre.endswith(".xls"):
        try:
            import pandas as pd
        except ImportError as e:
            raise ValueError("Falta pandas/openpyxl para leer Excel. Use CSV del MH o instale dependencias.") from e
        df = pd.read_excel(io.BytesIO(content), header=None, dtype=str)
        for _, row in df.iterrows():
            rows_raw.append([
                str(row.iloc[0]) if len(row) > 0 else "",
                str(row.iloc[1]) if len(row) > 1 else "",
            ])
    else:
        text = None
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            raise ValueError("No se pudo decodificar el archivo CSV.")
        rows_raw = _leer_csv_texto(text)

    out: list[list[str]] = []
    for row in rows_raw:
        par = _normalizar_fila(row)
        if par:
            out.append([par[0], par[1]])
    return out


def parse_rows_from_path(path: str | Path) -> list[list[str]]:
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {p}")
    return parse_rows_from_bytes(p.read_bytes(), p.name)


def import_actividades_rows(rows: list[list[str]]) -> dict[str, int]:
    """Persiste filas [[codigo, descripcion], ...]. Idempotente (update_or_create)."""
    created = 0
    updated = 0
    skipped = 0
    with transaction.atomic():
        for row in rows:
            if len(row) < 2:
                skipped += 1
                continue
            codigo = (row[0] or "").strip()
            descripcion = (row[1] or "").strip()
            if not codigo_es_numerico(codigo):
                skipped += 1
                continue
            codigo = codigo.replace(".", "")[:10]
            if not descripcion:
                descripcion = codigo
            _, was_created = ActividadEconomica.objects.update_or_create(
                codigo=codigo,
                defaults={"descripcion": descripcion[:255]},
            )
            if was_created:
                created += 1
            else:
                updated += 1
    total = ActividadEconomica.objects.count()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "processed": created + updated,
        "total_en_bd": total,
    }


def import_actividades_from_fileobj(fileobj: BinaryIO, filename: str = "") -> dict[str, int]:
    content = fileobj.read()
    rows = parse_rows_from_bytes(content, filename)
    if not rows:
        raise ValueError(
            "No se encontraron filas válidas. Use el CSV del MH (delimitador ;), "
            "columnas: código y descripción."
        )
    stats = import_actividades_rows(rows)
    stats["filas_validas"] = len(rows)
    return stats
