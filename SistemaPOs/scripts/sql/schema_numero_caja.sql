-- Numeración de caja por ambiente (ticket/factura POS) + ambiente MH local (sync AgilDTE)
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS numero_caja INTEGER;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS ambiente_mh VARCHAR(2) DEFAULT '01';

CREATE TABLE IF NOT EXISTS pos_secuencia_comprobante (
    empresa_id INTEGER NOT NULL,
    tipo VARCHAR(32) NOT NULL,
    ambiente_emision VARCHAR(2) NOT NULL,
    anio INTEGER NOT NULL,
    ultimo INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (empresa_id, tipo, ambiente_emision, anio)
);
