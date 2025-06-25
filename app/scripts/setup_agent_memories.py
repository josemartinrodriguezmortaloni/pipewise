"""
Setup script for agent memories table in Supabase.

Creates the required table structure for persistent memory storage.
"""

import logging
from typing import Optional
from supabase import Client

logger = logging.getLogger(__name__)


def get_supabase_client() -> Optional[Client]:
    """Get configured Supabase client."""
    try:
        from app.supabase.supabase_client import SupabaseCRMClient

        crm_client = SupabaseCRMClient()
        return crm_client.client

    except Exception as e:
        logger.error(f"Failed to get Supabase client: {e}")
        return None


def create_agent_memories_table(client: Client) -> bool:
    """
    Create the agent_memories table for persistent memory storage.

    Table structure:
    - id: UUID primary key
    - agent_id: String identifier for the agent
    - workflow_id: String identifier for the workflow session
    - content: JSONB field for flexible memory content
    - tags: Array of strings for categorization
    - metadata: JSONB field for additional metadata
    - created_at: Timestamp
    - updated_at: Timestamp

    Args:
        client: Supabase client instance

    Returns:
        bool: True if successful, False otherwise
    """

    try:
        # SQL to create the table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS agent_memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id TEXT NOT NULL,
            workflow_id TEXT NOT NULL,
            content JSONB NOT NULL DEFAULT '{}',
            tags TEXT[] DEFAULT '{}',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """

        # Execute table creation
        result = client.rpc("sql", {"query": create_table_sql}).execute()

        if result.data:
            logger.info("✅ Created agent_memories table successfully")
        else:
            logger.warning("⚠️ Table creation result unclear, may already exist")

        # Create indexes for better performance
        create_indexes_sql = """
        -- Index for agent queries
        CREATE INDEX IF NOT EXISTS idx_agent_memories_agent_id 
        ON agent_memories (agent_id);
        
        -- Index for workflow queries
        CREATE INDEX IF NOT EXISTS idx_agent_memories_workflow_id 
        ON agent_memories (workflow_id);
        
        -- Composite index for agent + workflow queries
        CREATE INDEX IF NOT EXISTS idx_agent_memories_agent_workflow 
        ON agent_memories (agent_id, workflow_id);
        
        -- Index for timestamp-based queries
        CREATE INDEX IF NOT EXISTS idx_agent_memories_created_at 
        ON agent_memories (created_at DESC);
        
        -- GIN index for tags array queries
        CREATE INDEX IF NOT EXISTS idx_agent_memories_tags 
        ON agent_memories USING GIN (tags);
        
        -- GIN index for content JSONB queries
        CREATE INDEX IF NOT EXISTS idx_agent_memories_content 
        ON agent_memories USING GIN (content);
        
        -- GIN index for metadata JSONB queries
        CREATE INDEX IF NOT EXISTS idx_agent_memories_metadata 
        ON agent_memories USING GIN (metadata);
        """

        # Execute index creation
        index_result = client.rpc("sql", {"query": create_indexes_sql}).execute()

        if index_result.data is not None:
            logger.info("✅ Created indexes for agent_memories table")
        else:
            logger.warning("⚠️ Index creation result unclear")

        # Create helper functions for statistics
        helper_functions_sql = """
        -- Function to count distinct agents
        CREATE OR REPLACE FUNCTION count_distinct_agents(table_name TEXT)
        RETURNS INTEGER AS $$
        DECLARE
            result INTEGER;
        BEGIN
            EXECUTE format('SELECT COUNT(DISTINCT agent_id) FROM %I', table_name) INTO result;
            RETURN result;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Function to count distinct workflows
        CREATE OR REPLACE FUNCTION count_distinct_workflows(table_name TEXT)
        RETURNS INTEGER AS $$
        DECLARE
            result INTEGER;
        BEGIN
            EXECUTE format('SELECT COUNT(DISTINCT workflow_id) FROM %I', table_name) INTO result;
            RETURN result;
        END;
        $$ LANGUAGE plpgsql;
        """

        # Execute helper functions creation
        functions_result = client.rpc("sql", {"query": helper_functions_sql}).execute()

        if functions_result.data is not None:
            logger.info("✅ Created helper functions for agent_memories")
        else:
            logger.warning("⚠️ Helper functions creation result unclear")

        # Create trigger for updated_at
        trigger_sql = """
        -- Create trigger function for updated_at
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Create trigger
        DROP TRIGGER IF EXISTS update_agent_memories_updated_at ON agent_memories;
        CREATE TRIGGER update_agent_memories_updated_at
            BEFORE UPDATE ON agent_memories
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """

        # Execute trigger creation
        trigger_result = client.rpc("sql", {"query": trigger_sql}).execute()

        if trigger_result.data is not None:
            logger.info("✅ Created update trigger for agent_memories")
        else:
            logger.warning("⚠️ Trigger creation result unclear")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to create agent_memories table: {e}")
        return False


def setup_row_level_security(client: Client) -> bool:
    """
    Set up Row Level Security (RLS) policies for agent_memories table.

    This ensures tenant isolation and proper access control.
    """

    try:
        rls_sql = """
        -- Enable RLS on agent_memories table
        ALTER TABLE agent_memories ENABLE ROW LEVEL SECURITY;
        
        -- Policy for authenticated users to access their own tenant's data
        CREATE POLICY IF NOT EXISTS "Users can access their tenant memories"
        ON agent_memories
        FOR ALL
        TO authenticated
        USING (
            -- This assumes you have a way to identify tenant from user context
            -- Adjust based on your authentication setup
            auth.uid()::text = ANY(
                SELECT user_id::text FROM tenants 
                WHERE tenant_id = (metadata->>'tenant_id')::text
            )
        );
        
        -- Policy for service role (bypass RLS for system operations)
        CREATE POLICY IF NOT EXISTS "Service role can access all memories"
        ON agent_memories
        FOR ALL
        TO service_role
        USING (true);
        """

        # Execute RLS setup
        result = client.rpc("sql", {"query": rls_sql}).execute()

        if result.data is not None:
            logger.info("✅ Set up Row Level Security for agent_memories")
            return True
        else:
            logger.warning("⚠️ RLS setup result unclear")
            return False

    except Exception as e:
        logger.error(f"❌ Failed to set up RLS: {e}")
        return False


def main():
    """Main setup function."""
    logging.basicConfig(level=logging.INFO)
    logger.info("🚀 Setting up agent memories table in Supabase...")

    # Get Supabase client
    client = get_supabase_client()
    if not client:
        logger.error("❌ Failed to get Supabase client")
        return False

    # Create table and indexes
    if not create_agent_memories_table(client):
        logger.error("❌ Failed to create agent_memories table")
        return False

    # Set up RLS (optional, comment out if not needed)
    # if not setup_row_level_security(client):
    #     logger.warning("⚠️ RLS setup failed, continuing anyway")

    logger.info("✅ Agent memories setup completed successfully!")
    return True


if __name__ == "__main__":
    main()
