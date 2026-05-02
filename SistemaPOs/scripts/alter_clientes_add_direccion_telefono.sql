-- Agregar dirección y teléfono a tabla clientes (requisitos MH El Salvador)
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS direccion TEXT;
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telefono VARCHAR(50);
