-- Códigos de barras por presentación (mismo producto_id, varios EAN / factores).
-- Ejecutar en pgAdmin o: psql -U postgres -d TU_BD -f scripts/sql/add_producto_presentacion_codigo_barra.sql

ALTER TABLE producto_presentacion
    ADD COLUMN IF NOT EXISTS codigo_barra VARCHAR(64) NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_producto_presentacion_codigo_barra
    ON producto_presentacion (upper(trim(codigo_barra)))
    WHERE codigo_barra IS NOT NULL AND length(trim(codigo_barra)) > 0;
