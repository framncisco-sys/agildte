-- Presentaciones de venta por producto (UMB, docena, caja, tiras, etc.)
CREATE TABLE IF NOT EXISTS producto_presentacion (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    nombre VARCHAR(80) NOT NULL,
    factor_umb NUMERIC(18,6) NOT NULL CHECK (factor_umb > 0),
    es_umb BOOLEAN NOT NULL DEFAULT FALSE,
    orden SMALLINT DEFAULT 0,
    codigo_barra VARCHAR(64) NULL,
    cantidad_desde NUMERIC(18,6) NULL,
    cantidad_hasta NUMERIC(18,6) NULL,
    precio_regla NUMERIC(18,6) NULL
);

DROP INDEX IF EXISTS uq_producto_presentacion_umb;

CREATE UNIQUE INDEX IF NOT EXISTS uq_producto_presentacion_umb
    ON producto_presentacion (producto_id)
    WHERE es_umb;

CREATE UNIQUE INDEX IF NOT EXISTS uq_producto_presentacion_codigo_barra
    ON producto_presentacion (upper(trim(codigo_barra)))
    WHERE codigo_barra IS NOT NULL AND length(trim(codigo_barra)) > 0;

ALTER TABLE venta_detalles
    ADD COLUMN IF NOT EXISTS presentacion_id INTEGER NULL;
