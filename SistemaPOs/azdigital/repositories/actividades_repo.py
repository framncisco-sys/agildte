# Programador: Oscar Amaya Romero
"""Catálogo de actividades económicas (El Salvador)."""


def listar_actividades(cur):
    """Retorna [(codigo, descripcion), ...] ordenado por codigo."""
    cur.execute(
        """
        SELECT codigo, descripcion
        FROM actividades_economicas
        ORDER BY codigo
        """
    )
    return cur.fetchall()


def buscar_actividades(cur, search: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[tuple[str, str]], int]:
    """Lista filtrada para el buscador del POS. Retorna (filas, total_aproximado)."""
    limit = max(1, min(int(limit or 50), 50))
    offset = max(0, int(offset or 0))
    q = (search or "").strip()
    if q:
        like = f"%{q}%"
        cur.execute(
            """
            SELECT codigo, descripcion
            FROM actividades_economicas
            WHERE UPPER(codigo) LIKE UPPER(%s) OR UPPER(descripcion) LIKE UPPER(%s)
            ORDER BY codigo
            LIMIT %s OFFSET %s
            """,
            (like, like, limit, offset),
        )
        rows = cur.fetchall() or []
        cur.execute(
            """
            SELECT COUNT(*) FROM actividades_economicas
            WHERE UPPER(codigo) LIKE UPPER(%s) OR UPPER(descripcion) LIKE UPPER(%s)
            """,
            (like, like),
        )
        total = int((cur.fetchone() or [0])[0])
        return rows, total
    cur.execute(
        """
        SELECT codigo, descripcion
        FROM actividades_economicas
        ORDER BY codigo
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )
    rows = cur.fetchall() or []
    try:
        cur.execute("SELECT COUNT(*) FROM actividades_economicas")
        total = int((cur.fetchone() or [0])[0])
    except Exception:
        total = len(rows)
    return rows, total


def get_descripcion_por_codigo(cur, codigo: str) -> str | None:
    if not codigo or not str(codigo).strip():
        return None
    cur.execute(
        "SELECT descripcion FROM actividades_economicas WHERE codigo = %s",
        (str(codigo).strip(),),
    )
    row = cur.fetchone()
    return row[0] if row else None
