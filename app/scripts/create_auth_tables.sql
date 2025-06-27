-- Script SQL para crear las tablas necesarias en Supabase
-- Reemplaza la funcionalidad de Redis para autenticación
-- Tabla para sesiones temporales de autenticación
CREATE TABLE IF NOT EXISTS auth_temp_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT NOT NULL,
    session_type TEXT NOT NULL CHECK (
        session_type IN (
            '2fa_temp',
            'pending_2fa',
            'user_session',
            'password_reset',
            'user_block'
        )
    ),
    user_id TEXT NOT NULL,
    data JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
-- Tabla para rate limiting
CREATE TABLE IF NOT EXISTS rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);
-- Índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_auth_temp_sessions_token ON auth_temp_sessions(token);
CREATE INDEX IF NOT EXISTS idx_auth_temp_sessions_user_id ON auth_temp_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_temp_sessions_session_type ON auth_temp_sessions(session_type);
CREATE INDEX IF NOT EXISTS idx_auth_temp_sessions_expires_at ON auth_temp_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_rate_limits_identifier ON rate_limits(identifier);
CREATE INDEX IF NOT EXISTS idx_rate_limits_created_at ON rate_limits(created_at);
CREATE INDEX IF NOT EXISTS idx_rate_limits_expires_at ON rate_limits(expires_at);
-- Función para limpiar automáticamente registros expirados
CREATE OR REPLACE FUNCTION cleanup_expired_auth_data() RETURNS INTEGER AS $$
DECLARE deleted_count INTEGER := 0;
sessions_deleted INTEGER;
rate_limits_deleted INTEGER;
BEGIN -- Limpiar sesiones temporales expiradas
DELETE FROM auth_temp_sessions
WHERE expires_at < NOW();
GET DIAGNOSTICS sessions_deleted = ROW_COUNT;
-- Limpiar rate limits expirados
DELETE FROM rate_limits
WHERE expires_at < NOW();
GET DIAGNOSTICS rate_limits_deleted = ROW_COUNT;
deleted_count := sessions_deleted + rate_limits_deleted;
RAISE NOTICE 'Cleaned up % expired records (% sessions, % rate limits)',
deleted_count,
sessions_deleted,
rate_limits_deleted;
RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
-- Crear extensión para trabajos programados si no existe
CREATE EXTENSION IF NOT EXISTS pg_cron;
-- Programar limpieza automática cada hora (opcional)
-- SELECT cron.schedule('cleanup-auth-data', '0 * * * *', 'SELECT cleanup_expired_auth_data();');
-- Habilitar Row Level Security
ALTER TABLE auth_temp_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY;
-- Políticas de seguridad para auth_temp_sessions
CREATE POLICY "Users can manage their own auth sessions" ON auth_temp_sessions USING (
    user_id = current_setting('request.jwt.claims', true)::json->>'sub'
);
-- Políticas de seguridad para rate_limits (permitir acceso de lectura/escritura para la aplicación)
CREATE POLICY "Application can manage rate limits" ON rate_limits USING (true);
-- Función para obtener estadísticas de autenticación
CREATE OR REPLACE FUNCTION get_auth_stats() RETURNS JSON AS $$
DECLARE stats JSON;
BEGIN
SELECT json_build_object(
        'active_2fa_temp_sessions',
        (
            SELECT COUNT(*)
            FROM auth_temp_sessions
            WHERE session_type = '2fa_temp'
                AND expires_at > NOW()
        ),
        'active_pending_2fa_sessions',
        (
            SELECT COUNT(*)
            FROM auth_temp_sessions
            WHERE session_type = 'pending_2fa'
                AND expires_at > NOW()
        ),
        'active_user_session_sessions',
        (
            SELECT COUNT(*)
            FROM auth_temp_sessions
            WHERE session_type = 'user_session'
                AND expires_at > NOW()
        ),
        'active_password_reset_sessions',
        (
            SELECT COUNT(*)
            FROM auth_temp_sessions
            WHERE session_type = 'password_reset'
                AND expires_at > NOW()
        ),
        'active_user_block_sessions',
        (
            SELECT COUNT(*)
            FROM auth_temp_sessions
            WHERE session_type = 'user_block'
                AND expires_at > NOW()
        ),
        'active_rate_limits',
        (
            SELECT COUNT(*)
            FROM rate_limits
            WHERE expires_at > NOW()
        ),
        'total_sessions',
        (
            SELECT COUNT(*)
            FROM auth_temp_sessions
            WHERE expires_at > NOW()
        ),
        'expired_sessions_count',
        (
            SELECT COUNT(*)
            FROM auth_temp_sessions
            WHERE expires_at <= NOW()
        ),
        'expired_rate_limits_count',
        (
            SELECT COUNT(*)
            FROM rate_limits
            WHERE expires_at <= NOW()
        ),
        'timestamp',
        NOW()
    ) INTO stats;
RETURN stats;
END;
$$ LANGUAGE plpgsql;
-- Comentarios para documentación
COMMENT ON TABLE auth_temp_sessions IS 'Tabla para almacenar sesiones temporales de autenticación, reemplaza Redis';
COMMENT ON TABLE rate_limits IS 'Tabla para rate limiting, reemplaza Redis';
COMMENT ON COLUMN auth_temp_sessions.token IS 'Token único para identificar la sesión';
COMMENT ON COLUMN auth_temp_sessions.session_type IS 'Tipo de sesión: 2fa_temp, pending_2fa, user_session, password_reset, user_block';
COMMENT ON COLUMN auth_temp_sessions.user_id IS 'ID del usuario asociado a la sesión';
COMMENT ON COLUMN auth_temp_sessions.data IS 'Datos de la sesión en formato JSON';
COMMENT ON COLUMN auth_temp_sessions.expires_at IS 'Fecha y hora de expiración de la sesión';
COMMENT ON COLUMN rate_limits.identifier IS 'Identificador para el rate limiting (IP, user_id, etc.)';
COMMENT ON COLUMN rate_limits.created_at IS 'Momento en que se registró la solicitud';
COMMENT ON COLUMN rate_limits.expires_at IS 'Momento en que expira el registro de rate limiting';