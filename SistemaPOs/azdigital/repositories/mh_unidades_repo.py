# Programador: Oscar Amaya Romero
"""Catálogo MH unidad de medida (tabla mh_unidad_medida).

Los códigos permitidos y su orden viven en azdigital.utils.mh_cat003_unidades;
al guardar productos se usa normalizar_codigo_mh (vía productos_repo).
"""


def tabla_existe(cur) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s",
        ("mh_unidad_medida",),
    )
    return cur.fetchone() is not None


def listar_todas(cur) -> list[tuple[str, str]]:
    """Orden comercial (cat. 003); descripción desde BD si existe, si no la del módulo."""
    from azdigital.utils.mh_cat003_unidades import todas_las_filas_cat003

    if not tabla_existe(cur):
        return _fallback_catalogo()
    cur.execute("SELECT codigo, descripcion FROM mh_unidad_medida")
    db_map = {str(a): str(b) for a, b in (cur.fetchall() or [])}
    return [(c, db_map.get(c, d)) for c, d in todas_las_filas_cat003()]


def _fallback_catalogo() -> list[tuple[str, str]]:
    from azdigital.utils.mh_cat003_unidades import todas_las_filas_cat003

    return todas_las_filas_cat003()
