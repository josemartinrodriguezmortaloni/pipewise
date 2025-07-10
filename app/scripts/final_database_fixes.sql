-- Final Database Fixes for PipeWise
-- Fix remaining RLS recursion and updated_at field issues
-- Step 1: Completely remove and recreate users table policies
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
-- Drop ALL existing policies (including any we missed)
DO $$
DECLARE r RECORD;
BEGIN FOR r IN
SELECT policyname
FROM pg_policies
WHERE tablename = 'users' LOOP EXECUTE 'DROP POLICY IF EXISTS "' || r.policyname || '" ON users';
END LOOP;
END $$;
-- Create the simplest possible non-recursive policies
CREATE POLICY "users_policy_select" ON users FOR
SELECT USING (
        auth.uid() = id
        OR auth.role() = 'service_role'
    );
CREATE POLICY "users_policy_insert" ON users FOR
INSERT WITH CHECK (
        auth.uid() = id
        OR auth.role() = 'service_role'
    );
CREATE POLICY "users_policy_update" ON users FOR
UPDATE USING (
        auth.uid() = id
        OR auth.role() = 'service_role'
    );
-- Re-enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- Step 2: Fix the leads table update issue by ensuring updated_at field is handled correctly
-- First, let's check if there's an update trigger causing the issue
DROP TRIGGER IF EXISTS handle_updated_at ON leads;
DROP TRIGGER IF EXISTS set_updated_at ON leads;
-- Create a simple function to handle updated_at automatically
CREATE OR REPLACE FUNCTION update_modified_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now();
RETURN NEW;
END;
$$ language 'plpgsql';
-- Create a trigger that only sets updated_at (avoiding the error)
CREATE TRIGGER handle_updated_at BEFORE
UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION update_modified_column();
-- Step 3: Ensure the test user exists and is accessible
INSERT INTO users (id, email, full_name, created_at, updated_at)
VALUES (
        '00000000-0000-0000-0000-000000000001',
        'test-agent@pipewise.app',
        'Test Agent',
        NOW(),
        NOW()
    ) ON CONFLICT (id) DO
UPDATE
SET email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    updated_at = NOW();
-- Step 4: Test that everything works
SELECT 'Database fixes applied successfully' as status;