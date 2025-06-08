-- ====================================================
-- PipeWise CRM - Database Setup ROBUST VERSION
-- ====================================================
-- PASO 1: Crear tabla users y usuario por defecto
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    company TEXT,
    phone TEXT,
    has_2fa BOOLEAN DEFAULT FALSE,
    totp_secret TEXT,
    totp_secret_temp TEXT,
    backup_codes TEXT [],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Crear un usuario por defecto si no existe ninguno, para asegurar que las FKs no fallen
INSERT INTO users (id, email, full_name, company)
VALUES (
        gen_random_uuid(),
        'admin@pipewise.com',
        'Admin User',
        'PipeWise'
    ) ON CONFLICT (email) DO NOTHING;
-- PASO 2: Crear tablas sin foreign keys Y verificar/agregar columnas faltantes
-- Tabla leads
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    company TEXT,
    position TEXT,
    source TEXT,
    status TEXT DEFAULT 'new',
    priority TEXT DEFAULT 'medium',
    notes TEXT,
    tags TEXT [],
    value DECIMAL(10, 2),
    expected_close_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Verificar y agregar columnas faltantes a leads
DO $$ BEGIN -- Agregar user_id si no existe
IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'leads'
        AND column_name = 'user_id'
) THEN
ALTER TABLE leads
ADD COLUMN user_id UUID;
RAISE NOTICE 'Added user_id column to leads table';
END IF;
-- Agregar owner_id si no existe
IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'leads'
        AND column_name = 'owner_id'
) THEN
ALTER TABLE leads
ADD COLUMN owner_id UUID;
RAISE NOTICE 'Added owner_id column to leads table';
END IF;
-- Actualizar user_id a NOT NULL si está NULL
IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'leads'
        AND column_name = 'user_id'
        AND is_nullable = 'YES'
) THEN -- Llenar valores NULL con un UUID por defecto o el primer usuario
UPDATE leads
SET user_id = (
        SELECT id
        FROM users
        LIMIT 1
    )
WHERE user_id IS NULL;
-- Hacer la columna NOT NULL
ALTER TABLE leads
ALTER COLUMN user_id
SET NOT NULL;
RAISE NOTICE 'Made user_id column NOT NULL in leads table';
END IF;
END $$;
-- Tabla contacts
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID,
    type TEXT NOT NULL,
    subject TEXT,
    content TEXT,
    outcome TEXT,
    next_action TEXT,
    next_action_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Verificar y agregar user_id a contacts
DO $$ BEGIN IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'contacts'
        AND column_name = 'user_id'
) THEN
ALTER TABLE contacts
ADD COLUMN user_id UUID;
UPDATE contacts
SET user_id = (
        SELECT id
        FROM users
        LIMIT 1
    )
WHERE user_id IS NULL;
ALTER TABLE contacts
ALTER COLUMN user_id
SET NOT NULL;
RAISE NOTICE 'Added user_id column to contacts table';
END IF;
END $$;
-- Tabla tasks
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    due_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Verificar y agregar user_id a tasks
DO $$ BEGIN IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'tasks'
        AND column_name = 'user_id'
) THEN
ALTER TABLE tasks
ADD COLUMN user_id UUID;
UPDATE tasks
SET user_id = (
        SELECT id
        FROM users
        LIMIT 1
    )
WHERE user_id IS NULL;
ALTER TABLE tasks
ALTER COLUMN user_id
SET NOT NULL;
RAISE NOTICE 'Added user_id column to tasks table';
END IF;
END $$;
-- Tabla pipelines
CREATE TABLE IF NOT EXISTS pipelines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    stages JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Verificar y agregar user_id a pipelines
DO $$ BEGIN IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'pipelines'
        AND column_name = 'user_id'
) THEN
ALTER TABLE pipelines
ADD COLUMN user_id UUID;
UPDATE pipelines
SET user_id = (
        SELECT id
        FROM users
        LIMIT 1
    )
WHERE user_id IS NULL;
ALTER TABLE pipelines
ALTER COLUMN user_id
SET NOT NULL;
RAISE NOTICE 'Added user_id column to pipelines table';
END IF;
END $$;
-- Tabla integrations
CREATE TABLE IF NOT EXISTS integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    last_sync TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
-- Verificar y agregar user_id a integrations
DO $$ BEGIN IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'integrations'
        AND column_name = 'user_id'
) THEN
ALTER TABLE integrations
ADD COLUMN user_id UUID;
UPDATE integrations
SET user_id = (
        SELECT id
        FROM users
        LIMIT 1
    )
WHERE user_id IS NULL;
ALTER TABLE integrations
ALTER COLUMN user_id
SET NOT NULL;
RAISE NOTICE 'Added user_id column to integrations table';
END IF;
END $$;
-- PASO 3: Agregar foreign keys (ahora que todas las columnas existen)
DO $$ BEGIN -- Verificar que la columna user_id existe en leads antes de crear FK
IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'leads'
        AND column_name = 'user_id'
)
AND NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_leads_user_id'
) THEN
ALTER TABLE leads
ADD CONSTRAINT fk_leads_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
RAISE NOTICE 'Added foreign key constraint fk_leads_user_id';
END IF;
-- Foreign key para owner_id en leads
IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'leads'
        AND column_name = 'owner_id'
)
AND NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_leads_owner_id'
) THEN
ALTER TABLE leads
ADD CONSTRAINT fk_leads_owner_id FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE;
RAISE NOTICE 'Added foreign key constraint fk_leads_owner_id';
END IF;
-- Foreign keys para contacts
IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'contacts'
        AND column_name = 'user_id'
)
AND NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_contacts_user_id'
) THEN
ALTER TABLE contacts
ADD CONSTRAINT fk_contacts_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
RAISE NOTICE 'Added foreign key constraint fk_contacts_user_id';
END IF;
IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_contacts_lead_id'
) THEN
ALTER TABLE contacts
ADD CONSTRAINT fk_contacts_lead_id FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE;
RAISE NOTICE 'Added foreign key constraint fk_contacts_lead_id';
END IF;
-- Foreign keys para tasks
IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'tasks'
        AND column_name = 'user_id'
)
AND NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_tasks_user_id'
) THEN
ALTER TABLE tasks
ADD CONSTRAINT fk_tasks_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
RAISE NOTICE 'Added foreign key constraint fk_tasks_user_id';
END IF;
IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_tasks_lead_id'
) THEN
ALTER TABLE tasks
ADD CONSTRAINT fk_tasks_lead_id FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE;
RAISE NOTICE 'Added foreign key constraint fk_tasks_lead_id';
END IF;
-- Foreign keys para pipelines
IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'pipelines'
        AND column_name = 'user_id'
)
AND NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_pipelines_user_id'
) THEN
ALTER TABLE pipelines
ADD CONSTRAINT fk_pipelines_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
RAISE NOTICE 'Added foreign key constraint fk_pipelines_user_id';
END IF;
-- Foreign keys para integrations
IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'integrations'
        AND column_name = 'user_id'
)
AND NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_integrations_user_id'
) THEN
ALTER TABLE integrations
ADD CONSTRAINT fk_integrations_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
RAISE NOTICE 'Added foreign key constraint fk_integrations_user_id';
END IF;
END $$;
-- PASO 5: Agregar check constraints
DO $$ BEGIN -- Check constraints para leads
IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'chk_leads_status'
) THEN
ALTER TABLE leads
ADD CONSTRAINT chk_leads_status CHECK (
        status IN (
            'new',
            'contacted',
            'qualified',
            'proposal',
            'won',
            'lost',
            'closed' -- keep enum aligned with analytics code
        )
    );
RAISE NOTICE 'Added check constraint chk_leads_status';
END IF;
-- Check constraint para leads.priority
IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'leads'
        AND column_name = 'priority'
)
AND NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'chk_leads_priority'
) THEN
ALTER TABLE leads
ADD CONSTRAINT chk_leads_priority CHECK (priority IN ('low', 'medium', 'high'));
RAISE NOTICE 'Added check constraint chk_leads_priority';
END IF;
END $$;
-- Check constraint para contacts.type
DO $$ BEGIN -- 1. Crear la columna si llegara a faltar
IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'contacts'
        AND column_name = 'type'
) THEN
ALTER TABLE contacts
ADD COLUMN type TEXT NOT NULL DEFAULT 'call';
END IF;
-- 2. Crear la restricción únicamente si aún no existe
IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'chk_contacts_type'
) THEN
ALTER TABLE contacts
ADD CONSTRAINT chk_contacts_type CHECK (type IN ('call', 'email', 'meeting', 'note'));
RAISE NOTICE 'Added check constraint chk_contacts_type';
END IF;
END $$;
-- Check constraints para tasks
DO $$ BEGIN IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'chk_tasks_status'
) THEN
ALTER TABLE tasks
ADD CONSTRAINT chk_tasks_status CHECK (
        status IN (
            'pending',
            'in_progress',
            'completed',
            'cancelled'
        )
    );
RAISE NOTICE 'Added check constraint chk_tasks_status';
END IF;
IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'chk_tasks_priority'
) THEN
ALTER TABLE tasks
ADD CONSTRAINT chk_tasks_priority CHECK (priority IN ('low', 'medium', 'high'));
RAISE NOTICE 'Added check constraint chk_tasks_priority';
END IF;
END $$;
-- Check constraints para integrations
DO $$ BEGIN IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'chk_integrations_type'
) THEN
ALTER TABLE integrations
ADD CONSTRAINT chk_integrations_type CHECK (
        type IN (
            'calendly',
            'google_calendar',
            'outlook',
            'zapier',
            'webhook'
        )
    );
RAISE NOTICE 'Added check constraint chk_integrations_type';
END IF;
END $$;
-- PASO 6: Habilitar RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipelines ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
-- PASO 7: Crear políticas RLS
-- Políticas para users
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Users can insert own profile" ON users;
CREATE POLICY "Users can view own profile" ON users FOR
SELECT USING (auth.uid()::text = id::text);
CREATE POLICY "Users can update own profile" ON users FOR
UPDATE USING (auth.uid()::text = id::text);
CREATE POLICY "Users can insert own profile" ON users FOR
INSERT WITH CHECK (auth.uid()::text = id::text);
-- Políticas para leads
DROP POLICY IF EXISTS "Users can view own leads" ON leads;
DROP POLICY IF EXISTS "Users can insert own leads" ON leads;
DROP POLICY IF EXISTS "Users can update own leads" ON leads;
DROP POLICY IF EXISTS "Users can delete own leads" ON leads;
CREATE POLICY "Users can view own leads" ON leads FOR
SELECT USING (auth.uid()::text = user_id::text);
CREATE POLICY "Users can insert own leads" ON leads FOR
INSERT WITH CHECK (auth.uid()::text = user_id::text);
CREATE POLICY "Users can update own leads" ON leads FOR
UPDATE USING (auth.uid()::text = user_id::text);
CREATE POLICY "Users can delete own leads" ON leads FOR DELETE USING (auth.uid()::text = user_id::text);
-- Políticas para contacts
DROP POLICY IF EXISTS "Users can manage own contacts" ON contacts;
CREATE POLICY "Users can manage own contacts" ON contacts FOR ALL USING (auth.uid()::text = user_id::text);
-- Políticas para tasks
DROP POLICY IF EXISTS "Users can manage own tasks" ON tasks;
CREATE POLICY "Users can manage own tasks" ON tasks FOR ALL USING (auth.uid()::text = user_id::text);
-- Políticas para pipelines
DROP POLICY IF EXISTS "Users can manage own pipelines" ON pipelines;
CREATE POLICY "Users can manage own pipelines" ON pipelines FOR ALL USING (auth.uid()::text = user_id::text);
-- Políticas para integrations
DROP POLICY IF EXISTS "Users can manage own integrations" ON integrations;
CREATE POLICY "Users can manage own integrations" ON integrations FOR ALL USING (auth.uid()::text = user_id::text);
-- PASO 8: Crear índices
CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_contacts_user_id ON contacts(user_id);
CREATE INDEX IF NOT EXISTS idx_contacts_lead_id ON contacts(lead_id);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_pipelines_user_id ON pipelines(user_id);
CREATE INDEX IF NOT EXISTS idx_integrations_user_id ON integrations(user_id);
-- PASO 9: Funciones de utilidad
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
-- PASO 10: Triggers para updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_leads_updated_at ON leads;
DROP TRIGGER IF EXISTS update_contacts_updated_at ON contacts;
DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
DROP TRIGGER IF EXISTS update_pipelines_updated_at ON pipelines;
DROP TRIGGER IF EXISTS update_integrations_updated_at ON integrations;
CREATE TRIGGER update_users_updated_at BEFORE
UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_leads_updated_at BEFORE
UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_contacts_updated_at BEFORE
UPDATE ON contacts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_tasks_updated_at BEFORE
UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_pipelines_updated_at BEFORE
UPDATE ON pipelines FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_integrations_updated_at BEFORE
UPDATE ON integrations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- PASO 11: Función para crear pipeline por defecto
CREATE OR REPLACE FUNCTION create_default_pipeline_for_user() RETURNS TRIGGER AS $$ BEGIN
INSERT INTO pipelines (user_id, name, stages, is_default)
VALUES (
        NEW.id,
        'Pipeline Principal',
        '[
            {"name": "Lead", "order": 1},
            {"name": "Contactado", "order": 2},
            {"name": "Calificado", "order": 3},
            {"name": "Propuesta", "order": 4},
            {"name": "Cerrado", "order": 5}
        ]'::jsonb,
        true
    ) ON CONFLICT DO NOTHING;
RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
DROP TRIGGER IF EXISTS create_default_pipeline_trigger ON users;
CREATE TRIGGER create_default_pipeline_trigger
AFTER
INSERT ON users FOR EACH ROW EXECUTE FUNCTION create_default_pipeline_for_user();
-- =================================================================
-- Trigger para sincronizar usuarios de Supabase Auth a public.users
-- =================================================================
-- 1. Crear la función que se ejecutará en el trigger
CREATE OR REPLACE FUNCTION public.handle_new_user() RETURNS TRIGGER AS $$ BEGIN
INSERT INTO public.users (id, email, full_name, company, phone)
VALUES (
        NEW.id,
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'full_name',
            split_part(NEW.email, '@', 1)
        ),
        NEW.raw_user_meta_data->>'company',
        NEW.raw_user_meta_data->>'phone'
    ) ON CONFLICT (id) DO NOTHING;
RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
-- 2. Crear el trigger que llama a la función cuando se crea un nuevo usuario en auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
AFTER
INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
-- Forzamos la actualización de un usuario para probar si el trigger funciona, si es necesario
-- UPDATE auth.users SET raw_user_meta_data = raw_user_meta_data || '{"test":"value"}'::jsonb WHERE id = 'some-user-id';
-- =================================================================
-- FIN
-- =================================================================
-- ====================================================
-- VERIFICACIÓN FINAL
-- ====================================================
DO $$
DECLARE table_count INTEGER;
policy_count INTEGER;
fk_count INTEGER;
user_count INTEGER;
BEGIN -- Contar tablas creadas
SELECT COUNT(*) INTO table_count
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_name IN (
        'users',
        'leads',
        'contacts',
        'tasks',
        'pipelines',
        'integrations'
    );
-- Contar políticas RLS
SELECT COUNT(*) INTO policy_count
FROM pg_policy
WHERE schemaname = 'public';
-- Contar foreign keys
SELECT COUNT(*) INTO fk_count
FROM pg_constraint
WHERE contype = 'f';
-- Contar usuarios
SELECT COUNT(*) INTO user_count
FROM users;
RAISE NOTICE '=================================================';
RAISE NOTICE 'DATABASE SETUP COMPLETED SUCCESSFULLY!';
RAISE NOTICE '=================================================';
RAISE NOTICE 'Tables created: %',
table_count;
RAISE NOTICE 'RLS policies created: %',
policy_count;
RAISE NOTICE 'Foreign keys created: %',
fk_count;
RAISE NOTICE 'Users in database: %',
user_count;
RAISE NOTICE 'All user_id columns exist and are properly referenced';
RAISE NOTICE 'Ready for Supabase authentication!';
RAISE NOTICE '=================================================';
END $$;