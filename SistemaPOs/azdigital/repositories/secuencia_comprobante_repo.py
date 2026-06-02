# Programador: Oscar Amaya Romero
"""Numeración de ticket/factura en caja por empresa, tipo y ambiente."""
from __future__ import annotations

from azdigital.utils.fecha_sv import hoy_sv


def asegurar_tabla(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pos_secuencia_comprobante (
            empresa_id INTEGER NOT NULL,
            tipo VARCHAR(32) NOT NULL,
            ambiente_emision VARCHAR(2) NOT NULL,
            anio INTEGER NOT NULL,
            ultimo INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (empresa_id, tipo, ambiente_emision, anio)
        )
        """
    )


def siguiente_numero(
    cur,
    empresa_id: int,
    tipo_comprobante: str,
    ambiente_emision: str,
) -> int:
    asegurar_tabla(cur)
    anio = hoy_sv().year
    tipo = (tipo_comprobante or "TICKET").strip().upper()[:32]
    amb = (ambiente_emision or "01").strip()[:2]
    cur.execute(
        """
        INSERT INTO pos_secuencia_comprobante (empresa_id, tipo, ambiente_emision, anio, ultimo)
        VALUES (%s, %s, %s, %s, 1)
        ON CONFLICT (empresa_id, tipo, ambiente_emision, anio)
        DO UPDATE SET ultimo = pos_secuencia_comprobante.ultimo + 1
        RETURNING ultimo
        """,
        (int(empresa_id), tipo, amb, anio),
    )
    row = cur.fetchone()
    return int(row[0]) if row else 1


def reiniciar_ambiente(cur, empresa_id: int, ambiente_emision: str = "00") -> int:
    """Reinicia contadores de caja del ambiente (p. ej. al pasar a producción)."""
    asegurar_tabla(cur)
    amb = (ambiente_emision or "00").strip()[:2]
    cur.execute(
        """
        UPDATE pos_secuencia_comprobante
        SET ultimo = 0
        WHERE empresa_id = %s AND ambiente_emision = %s
        """,
        (int(empresa_id), amb),
    )
    return int(cur.rowcount or 0)
