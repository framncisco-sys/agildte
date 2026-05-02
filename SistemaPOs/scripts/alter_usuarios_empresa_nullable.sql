-- Programador: Oscar Amaya Romero
-- Permite que usuarios superadmin tengan empresa_id NULL (sin empresa asignada)
-- Ejecutar una sola vez si la columna empresa_id tiene restricción NOT NULL

ALTER TABLE usuarios ALTER COLUMN empresa_id DROP NOT NULL;
