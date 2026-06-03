-- Baja lógica de productos (no DELETE): ocultos en inventario/POS, visibles en reporte.
ALTER TABLE productos ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE;
ALTER TABLE productos ADD COLUMN IF NOT EXISTS motivo_baja TEXT;
ALTER TABLE productos ADD COLUMN IF NOT EXISTS fecha_baja TIMESTAMP;
ALTER TABLE productos ADD COLUMN IF NOT EXISTS usuario_baja_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE productos ADD COLUMN IF NOT EXISTS usuario_baja_username VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_productos_activo ON productos(activo) WHERE activo = FALSE;
