-- Ambiente de emisión por venta (00=producción, 01=pruebas MH) — sync AgilDTE
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS ambiente_emision VARCHAR(2) DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_ventas_ambiente_emision ON ventas (empresa_id, ambiente_emision);
