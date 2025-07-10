-- Fix RLS policies for contacts table
-- Allow users to manage their own contacts
-- Disable RLS temporarily to modify policies
ALTER TABLE contacts DISABLE ROW LEVEL SECURITY;
-- Drop all existing policies for contacts
DO $$
DECLARE r RECORD;
BEGIN FOR r IN
SELECT policyname
FROM pg_policies
WHERE tablename = 'contacts' LOOP EXECUTE 'DROP POLICY IF EXISTS "' || r.policyname || '" ON contacts';
END LOOP;
END $$;
-- Create simple, effective policies for contacts
-- Using consistent type casting to avoid UUID/TEXT comparison errors
CREATE POLICY "contacts_policy_select" ON contacts FOR
SELECT USING (
        user_id::text = auth.uid()::text
        OR auth.role() = 'service_role'
    );
CREATE POLICY "contacts_policy_insert" ON contacts FOR
INSERT WITH CHECK (
        user_id::text = auth.uid()::text
        OR auth.role() = 'service_role'
    );
CREATE POLICY "contacts_policy_update" ON contacts FOR
UPDATE USING (
        user_id::text = auth.uid()::text
        OR auth.role() = 'service_role'
    ) WITH CHECK (
        user_id::text = auth.uid()::text
        OR auth.role() = 'service_role'
    );
CREATE POLICY "contacts_policy_delete" ON contacts FOR DELETE USING (
    user_id::text = auth.uid()::text
    OR auth.role() = 'service_role'
);
-- Re-enable RLS
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
-- Test query to verify policies work
-- SELECT count(*) FROM contacts WHERE user_id = '9e6fd7a1-d7b4-4f50-baa5-4c4d867a9ba4';
-- Show current policies for verification
SELECT schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename = 'contacts';