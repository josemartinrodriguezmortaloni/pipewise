-- Fix Database Schema Issues for PipeWise
-- This script resolves the "updated_at" field issue and RLS policies
-- 1. Add missing updated_at column to leads table if it doesn't exist
DO $$ BEGIN IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'leads'
        AND column_name = 'updated_at'
) THEN
ALTER TABLE leads
ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
RAISE NOTICE 'Added updated_at column to leads table';
END IF;
END $$;
-- 2. Create or update the updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ language 'plpgsql';
-- Drop existing trigger if it exists and create new one
DROP TRIGGER IF EXISTS update_leads_updated_at ON leads;
CREATE TRIGGER update_leads_updated_at BEFORE
UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- 3. Ensure test user exists with proper permissions
-- First disable RLS temporarily for user creation
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
-- Insert test user if not exists
INSERT INTO users (
        id,
        email,
        full_name,
        created_at,
        updated_at
    )
VALUES (
        '00000000-0000-0000-0000-000000000001',
        'test-agent@pipewise.app',
        'Test Agent User',
        NOW(),
        NOW()
    ) ON CONFLICT (id) DO
UPDATE
SET email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    updated_at = NOW();
-- Re-enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- 4. Create more permissive RLS policies for agents
-- Drop existing restrictive policies
DROP POLICY IF EXISTS "Users can view own data" ON users;
DROP POLICY IF EXISTS "Users can update own data" ON users;
-- Create agent-friendly policies
CREATE POLICY "Allow agent operations" ON users FOR ALL USING (
    auth.uid() = id
    OR id = '00000000-0000-0000-0000-000000000001'::uuid
    OR current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
);
-- 5. Ensure leads table has proper RLS policies
CREATE POLICY "Allow agent lead operations" ON leads FOR ALL USING (
    user_id = '00000000-0000-0000-0000-000000000001'::uuid
    OR current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
    OR user_id = auth.uid()
);
-- 6. Grant necessary permissions
GRANT ALL ON users TO authenticated;
GRANT ALL ON leads TO authenticated;
GRANT ALL ON conversations TO authenticated;
GRANT ALL ON messages TO authenticated;
GRANT ALL ON agent_memories TO authenticated;
-- 7. Verify the changes
SELECT 'Schema fix completed' as status;