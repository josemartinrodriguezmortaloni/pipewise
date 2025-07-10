-- Database Optimization: Remove Unused Tables
-- This script removes tables that are not being used in the codebase
-- PHASE 1: Remove completely unused tables
-- These tables have no references in the codebase
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS login_attempts CASCADE;
DROP TABLE IF EXISTS password_reset_tokens CASCADE;
DROP TABLE IF EXISTS email_confirmation_tokens CASCADE;
DROP TABLE IF EXISTS oauth2_states CASCADE;
DROP TABLE IF EXISTS pipelines CASCADE;
DROP TABLE IF EXISTS security_alerts CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS user_invitations CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
-- PHASE 2: Drop redundant views/stats tables
-- These are views or stats tables that can be regenerated if needed
DROP VIEW IF EXISTS auth_stats CASCADE;
DROP VIEW IF EXISTS user_stats CASCADE;
DROP VIEW IF EXISTS contacts_with_stats CASCADE;
-- PHASE 3: Consider dropping if not needed in future
-- Uncomment these if you're sure they won't be needed:
-- DROP TABLE IF EXISTS integrations CASCADE;
-- (Keep for now - may be used for storing OAuth configs)
-- DROP TABLE IF EXISTS user_accounts CASCADE;
-- (Keep for now - might be different from users table)
-- PHASE 4: Optimize remaining tables
-- Add missing indexes for performance
CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_contacts_user_id ON contacts(user_id);
CREATE INDEX IF NOT EXISTS idx_outreach_messages_contact_id ON outreach_messages(contact_id);
-- Optimize users table
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login);
-- Clean up any orphaned data
DELETE FROM messages
WHERE conversation_id NOT IN (
        SELECT id
        FROM conversations
    );
DELETE FROM conversations
WHERE user_id NOT IN (
        SELECT id
        FROM users
    );
DELETE FROM leads
WHERE user_id NOT IN (
        SELECT id
        FROM users
    );
DELETE FROM contacts
WHERE user_id NOT IN (
        SELECT id
        FROM users
    );
-- Update table statistics
ANALYZE users;
ANALYZE leads;
ANALYZE conversations;
ANALYZE messages;
ANALYZE contacts;
ANALYZE outreach_messages;
ANALYZE agent_memories;
-- Vacuum tables for optimal performance
VACUUM (ANALYZE) users;
VACUUM (ANALYZE) leads;
VACUUM (ANALYZE) conversations;
VACUUM (ANALYZE) messages;
VACUUM (ANALYZE) contacts;
VACUUM (ANALYZE) outreach_messages;
VACUUM (ANALYZE) agent_memories;