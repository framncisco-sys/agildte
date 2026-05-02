-- Tablas núcleo POS (PostgreSQL) para rutas: Punto de venta, Corte/Cierre de caja, Clientes.
-- Ejecutar después de schema_bootstrap_min.sql (empresas, usuarios).

CREATE TABLE IF NOT EXISTS sucursales (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    nombre VARCHAR(500) NOT NULL DEFAULT 'Principal',
    codigo_hacienda VARCHAR(80),
    direccion TEXT,
    telefono VARCHAR(120)
);

CREATE INDEX IF NOT EXISTS idx_sucursales_empresa ON sucursales(empresa_id);

CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    sucursal_id INTEGER REFERENCES sucursales(id) ON DELETE SET NULL,
    nombre_cliente VARCHAR(500) NOT NULL,
    tipo_documento VARCHAR(40),
    numero_documento VARCHAR(120),
    correo VARCHAR(255),
    es_contribuyente BOOLEAN DEFAULT FALSE,
    es_gran_contribuyente BOOLEAN DEFAULT FALSE,
    direccion TEXT,
    telefono VARCHAR(120),
    codigo_actividad_economica VARCHAR(80)
);

CREATE INDEX IF NOT EXISTS idx_clientes_empresa ON clientes(empresa_id);

CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE CASCADE,
    sucursal_id INTEGER REFERENCES sucursales(id) ON DELETE SET NULL,
    nombre VARCHAR(500) NOT NULL,
    precio_unitario NUMERIC(14, 4) DEFAULT 0,
    codigo_barra VARCHAR(120),
    promocion_tipo VARCHAR(40),
    promocion_valor NUMERIC(14, 4) DEFAULT 0,
    fraccionable BOOLEAN DEFAULT FALSE,
    unidades_por_caja INTEGER,
    unidades_por_docena INTEGER DEFAULT 12,
    mh_codigo_unidad VARCHAR(20),
    stock_actual NUMERIC(14, 4) DEFAULT 0,
    impuesto NUMERIC(8, 4)
);

CREATE INDEX IF NOT EXISTS idx_productos_empresa ON productos(empresa_id);

CREATE TABLE IF NOT EXISTS producto_stock_sucursal (
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    sucursal_id INTEGER NOT NULL REFERENCES sucursales(id) ON DELETE CASCADE,
    cantidad NUMERIC(14, 4) DEFAULT 0,
    PRIMARY KEY (producto_id, sucursal_id)
);

CREATE TABLE IF NOT EXISTS ventas (
    id SERIAL PRIMARY KEY,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_pagar NUMERIC(14, 4) NOT NULL DEFAULT 0,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    cliente_nombre VARCHAR(500),
    tipo_pago VARCHAR(40),
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE SET NULL,
    sucursal_id INTEGER REFERENCES sucursales(id) ON DELETE SET NULL,
    tipo_comprobante VARCHAR(32),
    cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
    retencion_iva NUMERIC(14, 4) DEFAULT 0,
    estado_cobro VARCHAR(40) DEFAULT 'COBRADO',
    descuento NUMERIC(14, 4) DEFAULT 0,
    total_bruto NUMERIC(14, 4),
    codigo_generacion VARCHAR(80),
    numero_control VARCHAR(80),
    estado_dte VARCHAR(40) DEFAULT 'RESPALDO',
    sello_recepcion TEXT,
    causa_contingencia INTEGER,
    estado VARCHAR(32) DEFAULT 'ACTIVO'
);

CREATE INDEX IF NOT EXISTS idx_ventas_empresa_fecha ON ventas(empresa_id, fecha_registro);
CREATE INDEX IF NOT EXISTS idx_ventas_usuario ON ventas(usuario_id);

CREATE TABLE IF NOT EXISTS venta_detalles (
    id SERIAL PRIMARY KEY,
    venta_id INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad NUMERIC(14, 4) NOT NULL,
    precio_unitario NUMERIC(14, 4) NOT NULL,
    subtotal NUMERIC(14, 4) NOT NULL,
    texto_cantidad TEXT,
    presentacion_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_venta_detalles_venta ON venta_detalles(venta_id);

CREATE TABLE IF NOT EXISTS cierre_caja (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL,
    sucursal_id INTEGER,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha_apertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TIMESTAMP,
    monto_apertura NUMERIC(12, 2) DEFAULT 0,
    ventas_efectivo NUMERIC(12, 2) DEFAULT 0,
    ventas_tarjeta NUMERIC(12, 2) DEFAULT 0,
    ventas_credito NUMERIC(12, 2) DEFAULT 0,
    ventas_otro NUMERIC(12, 2) DEFAULT 0,
    salidas_efectivo NUMERIC(12, 2) DEFAULT 0,
    monto_esperado NUMERIC(12, 2),
    monto_real NUMERIC(12, 2),
    diferencia NUMERIC(12, 2),
    estado VARCHAR(16) DEFAULT 'ABIERTO'
);

CREATE INDEX IF NOT EXISTS idx_cierre_caja_empresa ON cierre_caja(empresa_id);
CREATE INDEX IF NOT EXISTS idx_cierre_caja_usuario ON cierre_caja(usuario_id);
CREATE INDEX IF NOT EXISTS idx_cierre_caja_fecha ON cierre_caja(fecha_apertura);

INSERT INTO sucursales (empresa_id, nombre, codigo_hacienda, direccion, telefono)
SELECT e.id, 'Principal', '', '', ''
FROM empresas e
WHERE NOT EXISTS (SELECT 1 FROM sucursales s WHERE s.empresa_id = e.id);

SELECT setval(
    pg_get_serial_sequence('sucursales', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 1) FROM sucursales), 1)
);

SELECT setval(
    pg_get_serial_sequence('productos', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 1) FROM productos), 1)
);

SELECT setval(
    pg_get_serial_sequence('ventas', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 1) FROM ventas), 1)
);
