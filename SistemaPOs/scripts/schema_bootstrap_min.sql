-- Esquema mínimo PosAgil (PostgreSQL) para BD vacía.
-- Se ejecuta en docker-entrypoint-initdb.d la primera vez, o con: python scripts/bootstrap_bd.py

CREATE TABLE IF NOT EXISTS empresas (
    id SERIAL PRIMARY KEY,
    nombre_comercial VARCHAR(500),
    nombre VARCHAR(500),
    nit VARCHAR(80),
    nrc VARCHAR(80),
    actividad_economica TEXT,
    giro TEXT,
    direccion TEXT,
    telefono VARCHAR(120),
    correo VARCHAR(255),
    suscripcion_activa BOOLEAN DEFAULT TRUE,
    fecha_vencimiento DATE,
    codigo_actividad_economica VARCHAR(80),
    es_gran_contribuyente BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    rol VARCHAR(50) NOT NULL DEFAULT 'CAJERO',
    sucursal_id INTEGER,
    empresa_id INTEGER REFERENCES empresas(id) ON DELETE SET NULL,
    activo BOOLEAN DEFAULT TRUE
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_username_lower ON usuarios (LOWER(TRIM(username)));

-- Empresa por defecto (id=1) si la tabla está vacía (compatibilidad instalaciones antiguas)
INSERT INTO empresas (id, nombre_comercial, nit, nrc, actividad_economica, giro, suscripcion_activa)
SELECT 1, 'Empresa principal', '0614-000001-000-1', '000001-1', 'General', 'General', TRUE
WHERE NOT EXISTS (SELECT 1 FROM empresas LIMIT 1);

SELECT setval(
    pg_get_serial_sequence('empresas', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 1) FROM empresas), 1)
);
