# Programador: Oscar Amaya Romero
"""Tablas de proveedores y compras (facturas) vinculadas a inventario y lista de compras."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v

import psycopg2

from database import ConexionDB

cfg = ConexionDB().config
conn = psycopg2.connect(**cfg)
cur = conn.cursor()
try:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS proveedores (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            nombre VARCHAR(200) NOT NULL,
            nit VARCHAR(20),
            nrc VARCHAR(20),
            direccion VARCHAR(255),
            telefono VARCHAR(50),
            correo VARCHAR(120),
            contacto VARCHAR(120),
            activo BOOLEAN DEFAULT TRUE,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_proveedores_empresa ON proveedores(empresa_id)"
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS compras (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            proveedor_id INTEGER NOT NULL REFERENCES proveedores(id) ON DELETE RESTRICT,
            numero_factura VARCHAR(80),
            fecha DATE NOT NULL DEFAULT CURRENT_DATE,
            total NUMERIC(16, 4) DEFAULT 0,
            notas TEXT,
            usuario_id INTEGER REFERENCES usuarios(id),
            creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_compras_empresa ON compras(empresa_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_compras_proveedor ON compras(proveedor_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_compras_fecha ON compras(fecha)")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS compra_detalles (
            id SERIAL PRIMARY KEY,
            compra_id INTEGER NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
            producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
            cantidad NUMERIC(16, 4) NOT NULL,
            costo_unitario NUMERIC(16, 4) NOT NULL,
            subtotal NUMERIC(16, 4) NOT NULL
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_compra_detalles_compra ON compra_detalles(compra_id)")
    conn.commit()
    print("OK: tablas proveedores, compras y compra_detalles creadas.")
finally:
    cur.close()
    conn.close()
