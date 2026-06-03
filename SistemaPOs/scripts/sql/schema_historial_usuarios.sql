-- Historial de accesos y acciones de usuarios (logins, ventas, inventario, etc.)
CREATE TABLE IF NOT EXISTS historial_usuarios (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    username VARCHAR(100),
    evento VARCHAR(50) NOT NULL,
    detalle TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_historial_usuarios_usuario_id
    ON historial_usuarios(usuario_id);

CREATE INDEX IF NOT EXISTS idx_historial_usuarios_created_at
    ON historial_usuarios(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_historial_usuarios_evento
    ON historial_usuarios(evento);
