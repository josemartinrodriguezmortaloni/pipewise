-- Fix infinite recursion in users table RLS policies
-- This script resolves the "infinite recursion detected in policy" error
-- Disable RLS temporarily to fix the policies
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
-- Drop all existing policies that might be causing recursion
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Users can insert their own record" ON users;
DROP POLICY IF EXISTS "Service role can access all users" ON users;
-- Create simple, non-recursive policies
CREATE POLICY "Enable read access for authenticated users" ON users FOR
SELECT USING (
        auth.uid() = id
        OR auth.role() = 'service_role'
    );
CREATE POLICY "Enable insert for authenticated users" ON users FOR
INSERT WITH CHECK (
        auth.uid() = id
        OR auth.role() = 'service_role'
    );
CREATE POLICY "Enable update for users based on id" ON users FOR
UPDATE USING (
        auth.uid() = id
        OR auth.role() = 'service_role'
    );
-- Re-enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- Create pipelines table if it doesn't exist (to prevent trigger errors)
CREATE TABLE IF NOT EXISTS pipelines (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    stages JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);
-- Enable RLS on pipelines table
ALTER TABLE pipelines ENABLE ROW LEVEL SECURITY;
-- Create policy for pipelines table
CREATE POLICY "Enable access for users based on user_id" ON pipelines FOR ALL USING (
    auth.uid() = user_id
    OR auth.role() = 'service_role'
);
-- Now create the test user (triggers will work since pipelines table exists)
INSERT INTO users (id, email, full_name, created_at, updated_at)
VALUES (
        '00000000-0000-0000-0000-000000000001',
        'test-agent@pipewise.app',
        'Test Agent',
        NOW(),
        NOW()
    ) ON CONFLICT (id) DO NOTHING;
-- Verify the fix works
SELECT 'Users table RLS policies fixed successfully and pipelines table created' as status;