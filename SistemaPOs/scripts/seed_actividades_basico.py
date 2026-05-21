"""Crea tabla actividades_economicas (si falta) e inserta catálogo básico MH."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import ConexionDB

ACTIVIDADES = [
    ("45201", "Reparación mecánica de automotores"),
    ("45202", "Reparación de carrocerías"),
    ("46100", "Comercio al por mayor a cambio de una retribución"),
    ("47111", "Comercio al por menor en almacenes no especializados"),
    ("47191", "Comercio al por menor en minimercados"),
    ("47210", "Comercio al por menor de productos alimenticios"),
    ("47520", "Comercio al por menor de ferretería y materiales"),
    ("47711", "Comercio al por menor de productos farmacéuticos"),
    ("49110", "Transporte de pasajeros por ferrocarril"),
    ("49211", "Transporte de pasajeros por autobús"),
    ("49410", "Transporte de carga por carretera"),
    ("55110", "Hoteles y alojamientos similares"),
    ("56101", "Restaurantes y puestos de comidas"),
    ("56210", "Servicios de suministro de comidas por encargo"),
    ("62010", "Actividades de programación informática"),
    ("62020", "Actividades de consultoría informática"),
    ("70201", "Actividades de consultoría de gestión"),
    ("70202", "Actividades de relaciones públicas"),
    ("71110", "Actividades de arquitectura e ingeniería"),
    ("74100", "Actividades de diseño especializado"),
    ("74901", "Actividades de fotografía"),
    ("77291", "Alquiler de artículos para el hogar"),
    ("85101", "Enseñanza preprimaria"),
    ("85210", "Enseñanza primaria"),
    ("85310", "Enseñanza secundaria"),
    ("86101", "Actividades de hospitales y clínicas"),
    ("86901", "Actividades de odontología"),
    ("86902", "Actividades de laboratorios clínicos"),
    ("96011", "Lavado y limpieza de prendas de tela"),
    ("96021", "Peluquerías y salones de belleza"),
]


def main():
    db = ConexionDB()
    db.ejecutar_sql(
        """
        CREATE TABLE IF NOT EXISTS actividades_economicas (
            codigo VARCHAR(20) PRIMARY KEY,
            descripcion TEXT NOT NULL
        )
        """
    )
    n = 0
    for codigo, descripcion in ACTIVIDADES:
        db.ejecutar_sql(
            """
            INSERT INTO actividades_economicas (codigo, descripcion)
            VALUES (%s, %s)
            ON CONFLICT (codigo) DO UPDATE SET descripcion = EXCLUDED.descripcion
            """,
            (codigo, descripcion),
        )
        n += 1
    print(f"OK: {n} actividades en actividades_economicas")


if __name__ == "__main__":
    main()
