-- Setup OAuth Tables for PipeWise
-- Run this in your Supabase SQL Editor
-- Create user_accounts table for OAuth integrations
CREATE TABLE IF NOT EXISTS public.user_accounts (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    service text NOT NULL,
    account_data jsonb NOT NULL,
    -- Encrypted OAuth tokens
    connected boolean DEFAULT true,
    connected_at timestamp with time zone DEFAULT now(),
    profile_data jsonb DEFAULT '{}',
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    -- Ensure one account per user per service
    UNIQUE(user_id, service)
);
-- Add RLS policies
ALTER TABLE public.user_accounts ENABLE ROW LEVEL SECURITY;
-- Users can only see their own accounts
CREATE POLICY "Users can view own accounts" ON public.user_accounts FOR
SELECT USING (auth.uid() = user_id);
-- Users can insert their own accounts
CREATE POLICY "Users can insert own accounts" ON public.user_accounts FOR
INSERT WITH CHECK (auth.uid() = user_id);
-- Users can update their own accounts
CREATE POLICY "Users can update own accounts" ON public.user_accounts FOR
UPDATE USING (auth.uid() = user_id);
-- Users can delete their own accounts
CREATE POLICY "Users can delete own accounts" ON public.user_accounts FOR DELETE USING (auth.uid() = user_id);
-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_accounts_user_id ON public.user_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_accounts_service ON public.user_accounts(service);
CREATE INDEX IF NOT EXISTS idx_user_accounts_connected ON public.user_accounts(connected);
-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now();
RETURN NEW;
END;
$$ language 'plpgsql';
CREATE TRIGGER update_user_accounts_updated_at BEFORE
UPDATE ON public.user_accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- Grant permissions
GRANT ALL ON public.user_accounts TO authenticated;
GRANT ALL ON public.user_accounts TO service_role;