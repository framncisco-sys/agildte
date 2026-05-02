-- Programador: Oscar Amaya Romero
-- Permite que el mismo codigo_barra exista en distintas empresas.
-- NO afecta al superusuario: sigue viendo/tocando todo; cada empresa
-- solo debe tener códigos únicos internos.

-- Eliminar la restricción única global (si existe)
ALTER TABLE productos DROP CONSTRAINT IF EXISTS productos_codigo_barra_key;

-- Crear restricción única por empresa (empresa_id + codigo_barra)
ALTER TABLE productos ADD CONSTRAINT productos_empresa_codigo_uniq 
    UNIQUE (empresa_id, codigo_barra);
