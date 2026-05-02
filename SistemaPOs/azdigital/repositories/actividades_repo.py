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


def get_descripcion_por_codigo(cur, codigo: str) -> str | None:
    if not codigo or not str(codigo).strip():
        return None
    cur.execute(
        "SELECT descripcion FROM actividades_economicas WHERE codigo = %s",
        (str(codigo).strip(),),
    )
    row = cur.fetchone()
    return row[0] if row else None
