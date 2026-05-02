-- Compras y proveedores (PostgreSQL). Depende de: empresas, usuarios, productos (schema_bootstrap_pos_extensions.sql).
-- Rutas: /compras, /compras/nueva, inventario (listado usa costo_unitario en productos).

ALTER TABLE productos ADD COLUMN IF NOT EXISTS costo_unitario NUMERIC(14, 4) DEFAULT 0;

CREATE TABLE IF NOT EXISTS proveedores (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre VARCHAR(500) NOT NULL,
    nit VARCHAR(80),
    nrc VARCHAR(80),
    direccion TEXT,
    telefono VARCHAR(120),
    correo VARCHAR(255),
    contacto VARCHAR(255),
    activo BOOLEAN DEFAULT TRUE,
    tipo_documento VARCHAR(20) DEFAULT 'NIT',
    giro_actividad TEXT,
    clasificacion_contribuyente VARCHAR(20) DEFAULT 'PEQUEÑO',
    es_gran_contribuyente BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_proveedores_empresa ON proveedores(empresa_id);

CREATE TABLE IF NOT EXISTS compras (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(id) ON DELETE RESTRICT,
    numero_factura VARCHAR(120),
    fecha DATE,
    total NUMERIC(14, 4) DEFAULT 0,
    notas TEXT,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    codigo_generacion VARCHAR(80),
    sello_recepcion TEXT,
    retencion_iva NUMERIC(14, 4) DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_compras_empresa ON compras(empresa_id);
CREATE INDEX IF NOT EXISTS idx_compras_fecha ON compras(fecha);

CREATE TABLE IF NOT EXISTS compra_detalles (
    id SERIAL PRIMARY KEY,
    compra_id INTEGER NOT NULL REFERENCES compras(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad NUMERIC(14, 4) NOT NULL,
    costo_unitario NUMERIC(14, 4) NOT NULL,
    subtotal NUMERIC(14, 4) NOT NULL,
    cantidad_recibida_presentacion NUMERIC(14, 4),
    factor_conversion NUMERIC(14, 6),
    presentacion_nombre VARCHAR(200)
);

CREATE INDEX IF NOT EXISTS idx_compra_detalles_compra ON compra_detalles(compra_id);

SELECT setval(
    pg_get_serial_sequence('proveedores', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 1) FROM proveedores), 1)
);

SELECT setval(
    pg_get_serial_sequence('compras', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 1) FROM compras), 1)
);
