-- Fix contacts table structure to match application schema
-- Based on the test failure showing missing 'company' column
-- Add missing columns if they don't exist
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS company VARCHAR(200);
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS position VARCHAR(100);
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS location VARCHAR(100);
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS platform_username VARCHAR(100);
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS preferences JSONB;
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS tags TEXT [];
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
ALTER TABLE contacts
ADD COLUMN IF NOT EXISTS last_contacted TIMESTAMPTZ;
-- Verification query to check the table structure after updates
SELECT column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'contacts'
ORDER BY ordinal_position;
-- Optional: Test insert to verify structure works
-- Uncomment the lines below to test:
-- INSERT INTO contacts (
--     name, 
--     email, 
--     phone, 
--     platform, 
--     platform_id, 
--     platform_username,
--     company, 
--     position, 
--     location, 
--     user_id, 
--     metadata
-- ) VALUES (
--     'Test Contact',
--     'test@example.com',
--     '+1234567890',
--     'email',
--     'test_123',
--     'testuser',
--     'Test Company',
--     'Test Position',
--     'Test Location',
--     '9e6fd7a1-d7b4-4f50-baa5-4c4d867a9ba4',
--     '{"test": true}'::jsonb
-- );
-- Cleanup test data (uncomment if you ran the test insert above):
-- DELETE FROM contacts WHERE email = 'test@example.com';