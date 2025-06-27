# Agent Memories Setup Guide

Este documento explica cómo configurar la tabla `agent_memories` en Supabase para el almacenamiento persistente de memoria de los agentes.

## 🚀 Ejecución del Script

### Opción 1: Ejecución Directa (Recomendado)

```bash
uv run app/scripts/setup_agent_memories.py
```

El script intentará:
1. **Creación automática** (si `psycopg2` y `DATABASE_URL` están disponibles)
2. **Mostrar comandos SQL** para ejecución manual

### Opción 2: Instalación de Dependencias para Creación Automática

Si quieres que el script cree la tabla automáticamente:

```bash
# Instalar psycopg2 para conexión directa a PostgreSQL
uv add psycopg2-binary

# Asegurarse de que DATABASE_URL esté en el .env
echo "DATABASE_URL=postgresql://user:password@host:port/database" >> .env

# Ejecutar el script
uv run app/scripts/setup_agent_memories.py
```

## 📋 Comandos SQL Manuales

Si prefieres ejecutar los comandos manualmente en el dashboard de Supabase:

### 1. Ir al SQL Editor de Supabase
- URL: `https://supabase.com/dashboard/project/[YOUR-PROJECT]/sql`

### 2. Ejecutar los Comandos SQL

```sql
-- Crear tabla principal
CREATE TABLE IF NOT EXISTS agent_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    content JSONB NOT NULL DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Crear índices para optimización
CREATE INDEX IF NOT EXISTS idx_agent_memories_agent_id ON agent_memories (agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_memories_workflow_id ON agent_memories (workflow_id);
CREATE INDEX IF NOT EXISTS idx_agent_memories_agent_workflow ON agent_memories (agent_id, workflow_id);
CREATE INDEX IF NOT EXISTS idx_agent_memories_created_at ON agent_memories (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_memories_tags ON agent_memories USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_agent_memories_content ON agent_memories USING GIN (content);
CREATE INDEX IF NOT EXISTS idx_agent_memories_metadata ON agent_memories USING GIN (metadata);

-- Funciones auxiliares
CREATE OR REPLACE FUNCTION count_distinct_agents(table_name TEXT)
RETURNS INTEGER AS $$
DECLARE
    result INTEGER;
BEGIN
    EXECUTE format('SELECT COUNT(DISTINCT agent_id) FROM %I', table_name) INTO result;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION count_distinct_workflows(table_name TEXT)
RETURNS INTEGER AS $$
DECLARE
    result INTEGER;
BEGIN
    EXECUTE format('SELECT COUNT(DISTINCT workflow_id) FROM %I', table_name) INTO result;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Trigger para updated_at automático
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_agent_memories_updated_at ON agent_memories;
CREATE TRIGGER update_agent_memories_updated_at
    BEFORE UPDATE ON agent_memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

## 🔍 Verificación

Para verificar que la tabla se creó correctamente:

```bash
uv run app/scripts/setup_agent_memories.py
```

El script mostrará:
- ✅ `Table verification successful` si la tabla existe
- ⚠️ `Table verification failed` si aún no existe

## 📊 Estructura de la Tabla

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | Clave primaria única |
| `agent_id` | TEXT | Identificador del agente |
| `workflow_id` | TEXT | Identificador de la sesión/workflow |
| `content` | JSONB | Contenido de la memoria (flexible) |
| `tags` | TEXT[] | Etiquetas para categorización |
| `metadata` | JSONB | Metadatos adicionales |
| `created_at` | TIMESTAMPTZ | Fecha de creación |
| `updated_at` | TIMESTAMPTZ | Fecha de última actualización |

## 🔐 Seguridad (Row Level Security)

**Opcional**: Para habilitar RLS (Row Level Security):

```sql
-- Habilitar RLS
ALTER TABLE agent_memories ENABLE ROW LEVEL SECURITY;

-- Política para usuarios autenticados
CREATE POLICY "Users can access their tenant memories"
ON agent_memories
FOR ALL
TO authenticated
USING (
    auth.uid()::text = ANY(
        SELECT user_id::text FROM tenants 
        WHERE tenant_id = (metadata->>'tenant_id')::text
    )
);

-- Política para service role
CREATE POLICY "Service role can access all memories"
ON agent_memories
FOR ALL
TO service_role
USING (true);
```

## 🛠️ Troubleshooting

### Error: "No module named 'app'"
**Solución**: Ejecutar desde el directorio raíz del proyecto:
```bash
cd /path/to/pipewise
uv run app/scripts/setup_agent_memories.py
```

### Error: "relation does not exist"
**Solución**: La tabla aún no se ha creado. Ejecutar los comandos SQL manualmente.

### Error: "psycopg2 not installed"
**Solución**: Instalar la dependencia:
```bash
uv add psycopg2-binary
```

## ✅ Éxito

Una vez completada la configuración, los agentes podrán usar la memoria persistente para:
- Recordar conversaciones entre sesiones
- Mantener contexto de leads
- Compartir información entre agentes
- Analizar patrones históricos

¡La tabla `agent_memories` está lista para usar! 🎉 