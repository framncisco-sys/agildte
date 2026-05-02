-- Kardex, promociones, contingencia MH, historial de costos. Depende de empresas, usuarios, productos, sucursales.
-- Cubre: /inventario (conteo), /reporte/inventario/*, /promociones, /contingencia, /gestion_ventas (datos ya en ventas).

ALTER TABLE productos ADD COLUMN IF NOT EXISTS unidad_medida VARCHAR(40);
ALTER TABLE productos ADD COLUMN IF NOT EXISTS metodo_valuacion VARCHAR(40) DEFAULT 'PROMEDIO';

CREATE TABLE IF NOT EXISTS inventario_kardex (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    tipo VARCHAR(40) NOT NULL,
    cantidad NUMERIC(18, 6) NOT NULL DEFAULT 0,
    sucursal_id INTEGER REFERENCES sucursales(id) ON DELETE SET NULL,
    sucursal_destino_id INTEGER REFERENCES sucursales(id) ON DELETE SET NULL,
    referencia TEXT,
    notas TEXT,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo_ajuste VARCHAR(40),
    costo_unitario NUMERIC(14, 6),
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_inv_kardex_emp_prod ON inventario_kardex(empresa_id, producto_id);
CREATE INDEX IF NOT EXISTS idx_inv_kardex_creado ON inventario_kardex(creado_en);
CREATE INDEX IF NOT EXISTS idx_inv_kardex_producto ON inventario_kardex(producto_id);

CREATE TABLE IF NOT EXISTS evento_contingencia (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    fecha_inicio TIMESTAMP NOT NULL,
    fecha_fin TIMESTAMP NOT NULL,
    causa INTEGER,
    descripcion_causa VARCHAR(200),
    estado VARCHAR(40) DEFAULT 'PENDIENTE',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evt_cont_empresa ON evento_contingencia(empresa_id);

CREATE TABLE IF NOT EXISTS promociones (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre VARCHAR(500) NOT NULL,
    tipo VARCHAR(40) NOT NULL,
    valor NUMERIC(14, 4) DEFAULT 0,
    fecha_inicio DATE,
    fecha_fin DATE,
    activa BOOLEAN DEFAULT TRUE,
    valor_comprar NUMERIC(14, 4),
    valor_pagar NUMERIC(14, 4),
    descuento_monto NUMERIC(14, 4),
    producto_regalo_id INTEGER REFERENCES productos(id) ON DELETE SET NULL,
    cantidad_min_compra NUMERIC(14, 4) DEFAULT 1,
    cantidad_regalo NUMERIC(14, 4) DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_promociones_empresa ON promociones(empresa_id);

CREATE TABLE IF NOT EXISTS promocion_productos (
    promocion_id INTEGER NOT NULL REFERENCES promociones(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    PRIMARY KEY (promocion_id, producto_id)
);

CREATE TABLE IF NOT EXISTS producto_costos (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    costo NUMERIC(14, 6) NOT NULL,
    cantidad NUMERIC(14, 4) DEFAULT 1,
    tipo VARCHAR(40) DEFAULT 'COMPRA',
    referencia TEXT,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_producto_costos_prod ON producto_costos(producto_id);

SELECT setval(
    pg_get_serial_sequence('inventario_kardex', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 1) FROM inventario_kardex), 1)
);

SELECT setval(
    pg_get_serial_sequence('evento_contingencia', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 1) FROM evento_contingencia), 1)
);

SELECT setval(
    pg_get_serial_sequence('promociones', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 1) FROM promociones), 1)
);

SELECT setval(
    pg_get_serial_sequence('producto_costos', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 1) FROM producto_costos), 1)
);
