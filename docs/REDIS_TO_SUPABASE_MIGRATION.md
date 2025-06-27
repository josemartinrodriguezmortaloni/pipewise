# Migración de Redis a Supabase - Guía Completa

## Resumen

Esta guía documenta la migración completa del sistema de autenticación y caché de Redis a Supabase en el proyecto PipeWise. La migración reemplaza toda la funcionalidad de Redis con tablas y funciones de Supabase PostgreSQL.

## ¿Por qué migrar a Supabase?

### Ventajas de usar Supabase en lugar de Redis:

1. **Simplicidad de infraestructura**: Un solo servicio (Supabase) en lugar de Redis + PostgreSQL
2. **Persistencia nativa**: Los datos se almacenan en PostgreSQL de forma permanente
3. **Row Level Security (RLS)**: Seguridad a nivel de base de datos
4. **Funciones SQL**: Lógica de limpieza y estadísticas en la base de datos
5. **Escalabilidad**: PostgreSQL es más escalable para datos estructurados
6. **Menos dependencias**: Elimina la necesidad de Redis y Celery
7. **Costo reducido**: Un servicio menos que mantener

## Cambios Realizados

### 1. Archivos Creados

#### `app/auth/supabase_auth_client.py`
- **Propósito**: Cliente de autenticación basado en Supabase
- **Reemplaza**: `app/auth/redis_client.py`
- **Funcionalidades**:
  - Sesiones temporales 2FA
  - Rate limiting
  - Cache de sesiones de usuario
  - Tokens de reset de contraseña
  - Bloqueo temporal de usuarios
  - Estadísticas de autenticación

#### `app/scripts/create_auth_tables.sql`
- **Propósito**: Script SQL para crear tablas en Supabase
- **Tablas creadas**:
  - `auth_temp_sessions`: Sesiones temporales de autenticación
  - `rate_limits`: Registros para rate limiting
- **Incluye**: Índices, funciones, políticas RLS

#### `app/scripts/migrate_redis_to_supabase.py`
- **Propósito**: Script automatizado de migración
- **Funciones**:
  - Verificación de conexión
  - Creación de tablas
  - Tests de funcionalidad
  - Reporte de migración

### 2. Archivos Modificados

#### `app/api/main.py`
- ✅ Importaciones actualizadas de Redis a Supabase
- ✅ Referencias en startup_checks, cleanup_tasks, y metrics
- ✅ Rate limiting middleware (comentado)

#### `app/core/dependencies.py`
- ✅ `get_redis_client()` → `get_supabase_auth_client()`
- ✅ Rate limiting usando Supabase

#### `pyproject.toml`
- ✅ Removidas dependencias: `celery[redis]`, `redis[hiredis]`
- ✅ Mantenida dependencia: `supabase>=2.15.3`

#### `tests/conftest.py`
- ✅ `mock_redis_client` → `mock_supabase_auth_client`
- ✅ Variables de entorno actualizadas

#### `tests/unit/test_dependencies.py`
- ✅ Tests de rate limiting actualizados

### 3. Funcionalidades Migradas

| Funcionalidad Redis | Equivalente Supabase | Estado |
|---------------------|---------------------|---------|
| Sesiones 2FA temporales | `auth_temp_sessions` table | ✅ Migrado |
| Configuración 2FA pendiente | `auth_temp_sessions` table | ✅ Migrado |
| Rate limiting | `rate_limits` table | ✅ Migrado |
| Cache de sesiones | `auth_temp_sessions` table | ✅ Migrado |
| Tokens reset password | `auth_temp_sessions` table | ✅ Migrado |
| Bloqueo temporal usuarios | `auth_temp_sessions` table | ✅ Migrado |
| Estadísticas de auth | Función SQL `get_auth_stats()` | ✅ Migrado |
| Limpieza automática | Función SQL `cleanup_expired_auth_data()` | ✅ Migrado |

## Pasos de Implementación

### 1. Preparación

```bash
# Instalar dependencias actualizadas
uv sync

# Verificar que Supabase está configurado
echo $SUPABASE_URL
echo $SUPABASE_KEY
```

### 2. Crear Tablas en Supabase

1. Ir a Supabase Dashboard → SQL Editor
2. Ejecutar el contenido de `app/scripts/create_auth_tables.sql`
3. Verificar que las tablas se crearon correctamente

### 3. Ejecutar Script de Migración

```bash
cd app/scripts
python migrate_redis_to_supabase.py
```

### 4. Actualizar Variables de Entorno

#### Remover:
```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

#### Mantener/Verificar:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
OPENAI_API_KEY=your-openai-key
SECRET_KEY=your-secret-key
ENVIRONMENT=production
```

### 5. Actualizar Configuración de Deployment

#### Docker Compose (si aplica):
```yaml
# Remover servicio Redis
# services:
#   redis:
#     image: redis:7-alpine
#     ports:
#       - "6379:6379"

# Mantener solo los servicios necesarios
services:
  app:
    build: .
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
```

### 6. Testing

```bash
# Ejecutar tests
python -m pytest tests/ -v

# Test específico de autenticación
python -m pytest tests/unit/test_dependencies.py -v

# Test del servidor
uvicorn app.api.main:app --reload
```

## Esquema de Base de Datos

### Tabla `auth_temp_sessions`

```sql
CREATE TABLE auth_temp_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT NOT NULL,
    session_type TEXT NOT NULL CHECK (session_type IN ('2fa_temp', 'pending_2fa', 'user_session', 'password_reset', 'user_block')),
    user_id TEXT NOT NULL,
    data JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla `rate_limits`

```sql
CREATE TABLE rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);
```

## API del SupabaseAuthClient

### Métodos Principales

```python
from app.auth.supabase_auth_client import get_supabase_auth_client

client = await get_supabase_auth_client()

# Sesiones 2FA
await client.store_2fa_temp_session(user_id, token, ip, user_agent)
session = await client.get_2fa_temp_session(token)
await client.cleanup_2fa_temp_session(token)

# Rate Limiting
rate_check = await client.check_rate_limit(identifier, limit, window)

# Cache de sesiones
await client.cache_user_session(session_id, user_data)
cached = await client.get_cached_user_session(session_id)

# Estadísticas
stats = await client.get_auth_stats()
```

## Monitoreo y Mantenimiento

### 1. Limpieza Automática

La función `cleanup_expired_auth_data()` se puede programar para ejecutarse automáticamente:

```sql
-- Programar limpieza cada hora (opcional con pg_cron)
SELECT cron.schedule('cleanup-auth-data', '0 * * * *', 'SELECT cleanup_expired_auth_data();');
```

### 2. Monitoreo de Métricas

```python
# Obtener estadísticas
stats = await client.get_auth_stats()
print(f"Sesiones activas: {stats['stats']['total_sessions']}")
print(f"Rate limits activos: {stats['stats']['active_rate_limits']}")
```

### 3. Queries Útiles para Monitoreo

```sql
-- Ver sesiones activas por tipo
SELECT session_type, COUNT(*) as count
FROM auth_temp_sessions 
WHERE expires_at > NOW() 
GROUP BY session_type;

-- Ver rate limits por identificador
SELECT identifier, COUNT(*) as requests
FROM rate_limits 
WHERE expires_at > NOW() 
GROUP BY identifier 
ORDER BY requests DESC;

-- Limpiar manualmente datos expirados
SELECT cleanup_expired_auth_data();
```

## Rollback (En caso de problemas)

Si necesitas revertir la migración:

1. **Restaurar dependencias Redis**:
```toml
dependencies = [
    # ... otras dependencias
    "celery[redis]>=5.5.3",
    "redis[hiredis]>=5.2.1",
]
```

2. **Restaurar archivos**:
```bash
git checkout HEAD~1 -- app/auth/redis_client.py
git checkout HEAD~1 -- app/api/main.py
git checkout HEAD~1 -- app/core/dependencies.py
```

3. **Restaurar variables de entorno**:
```env
REDIS_URL=redis://localhost:6379/0
```

## Beneficios Obtenidos

1. **Simplicidad**: Un servicio menos que mantener
2. **Persistencia**: Datos guardados permanentemente en PostgreSQL
3. **Seguridad**: Row Level Security automática
4. **Performance**: Consultas SQL optimizadas con índices
5. **Escalabilidad**: PostgreSQL escala mejor que Redis para datos estructurados
6. **Costo**: Reducción en infraestructura y mantenimiento

## Próximos Pasos

1. ✅ Migración de autenticación completada
2. ⏳ Monitorear logs de aplicación post-migración
3. ⏳ Configurar alertas para métricas de autenticación
4. ⏳ Documentar nuevos procesos de deployment
5. ⏳ Actualizar guías de desarrollo del equipo

## Soporte

Si encuentras algún problema durante la migración:

1. Revisa los logs de la aplicación
2. Verifica las conexiones a Supabase
3. Ejecuta el script de migración para diagnóstico
4. Consulta la documentación de Supabase

La migración ha sido diseñada para ser segura y reversible. Todos los datos importantes se mantienen en Supabase PostgreSQL con respaldos automáticos. 