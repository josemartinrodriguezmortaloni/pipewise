-- Clean up unused database tables in PipeWise
-- These tables have code implemented but are not used in the main workflow
-- =====================================================
-- BACKUP NOTICE: 
-- Run these commands ONLY if you are sure these tables contain no important data
-- Consider backing up data first if needed
-- =====================================================
-- Drop unused tables in correct order (respecting foreign key constraints)
-- Drop messages table first (depends on conversations)
DROP TABLE IF EXISTS messages CASCADE;
-- Drop conversations table (depends on leads but leads is staying)
DROP TABLE IF EXISTS conversations CASCADE;
-- Drop outreach_messages table (depends on contacts)
DROP TABLE IF EXISTS outreach_messages CASCADE;
-- Drop contacts table
DROP TABLE IF EXISTS contacts CASCADE;
-- Drop the contacts_with_stats view if it exists
DROP VIEW IF EXISTS contacts_with_stats CASCADE;
-- Drop integrations table (not needed as values stored elsewhere)
DROP TABLE IF EXISTS integrations CASCADE;
-- Drop any related functions that were created for these tables
DROP FUNCTION IF EXISTS get_contact_stats(text) CASCADE;
-- =====================================================
-- Optional: Clean up any related policies (RLS)
-- =====================================================
-- Remove any row-level security policies for dropped tables
-- (Supabase automatically drops policies when tables are dropped)
-- =====================================================
-- SUMMARY OF REMAINING TABLES:
-- =====================================================
-- ✅ users - User management
-- ✅ leads - Main lead/prospect management
-- ✅ agent_memories - AI agent memory system
-- ✅ pipelines - User pipeline configuration
-- ✅ auth_temp_sessions - Authentication sessions
-- ✅ rate_limits - Rate limiting
-- ✅ user_sessions - User sessions
-- ✅ auth_audit_logs - Authentication audit
-- ✅ user_accounts - OAuth accounts
-- =====================================================
-- VERIFICATION QUERIES:
-- =====================================================
-- Run these after cleanup to verify tables are gone:
-- SELECT table_name FROM information_schema.tables 
-- WHERE table_schema = 'public' 
-- AND table_name IN ('contacts', 'conversations', 'messages', 'outreach_messages', 'integrations');
-- This should return no rows if cleanup was successful.