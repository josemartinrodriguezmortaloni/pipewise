-- Fix RLS policies for user_accounts table
-- This script enables proper access to user_accounts table for OAuth integration
-- Enable RLS on user_accounts table if not already enabled
ALTER TABLE user_accounts ENABLE ROW LEVEL SECURITY;
-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can insert their own accounts" ON user_accounts;
DROP POLICY IF EXISTS "Users can view their own accounts" ON user_accounts;
DROP POLICY IF EXISTS "Users can update their own accounts" ON user_accounts;
DROP POLICY IF EXISTS "Users can delete their own accounts" ON user_accounts;
-- Create comprehensive RLS policies for user_accounts
-- Policy for INSERT: Users can insert their own accounts
CREATE POLICY "Users can insert their own accounts" ON user_accounts FOR
INSERT WITH CHECK (auth.uid() = user_id);
-- Policy for SELECT: Users can view their own accounts
CREATE POLICY "Users can view their own accounts" ON user_accounts FOR
SELECT USING (auth.uid() = user_id);
-- Policy for UPDATE: Users can update their own accounts
CREATE POLICY "Users can update their own accounts" ON user_accounts FOR
UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
-- Policy for DELETE: Users can delete their own accounts
CREATE POLICY "Users can delete their own accounts" ON user_accounts FOR DELETE USING (auth.uid() = user_id);
-- Grant necessary permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON user_accounts TO authenticated;
GRANT ALL ON user_accounts TO anon;
-- Ensure the table structure is correct
ALTER TABLE user_accounts
ALTER COLUMN user_id
SET DEFAULT auth.uid(),
    ALTER COLUMN created_at
SET DEFAULT now(),
    ALTER COLUMN updated_at
SET DEFAULT now();
-- Add trigger for updated_at if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS update_user_accounts_updated_at ON user_accounts;
CREATE TRIGGER update_user_accounts_updated_at BEFORE
UPDATE ON user_accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();