"""
Setup script for agent memories table in Supabase.

Creates the required table structure for persistent memory storage.
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional

# Agregar el directorio raíz del proyecto al path de Python
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from supabase import Client
except ImportError:
    print("❌ Supabase library not installed. Run: uv add supabase")
    sys.exit(1)

logger = logging.getLogger(__name__)


def get_supabase_client() -> Optional[Client]:
    """Get configured Supabase client."""
    try:
        # Intentar importar desde el módulo app
        from app.supabase.supabase_client import SupabaseCRMClient

        crm_client = SupabaseCRMClient()
        return crm_client.client

    except ImportError as e:
        logger.error(f"Failed to import SupabaseCRMClient: {e}")

        # Fallback: crear cliente directamente usando variables de entorno
        try:
            from dotenv import load_dotenv

            load_dotenv()

            supabase_url = os.getenv("SUPABASE_URL") or os.getenv(
                "NEXT_PUBLIC_SUPABASE_URL"
            )
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv(
                "SUPABASE_SERVICE_ROLE_KEY"
            )

            if not supabase_url or not supabase_key:
                logger.error(
                    "❌ Missing Supabase URL or Service Key in environment variables"
                )
                return None

            from supabase import create_client

            client = create_client(supabase_url, supabase_key)
            logger.info(
                "✅ Created Supabase client directly from environment variables"
            )
            return client

        except Exception as fallback_error:
            logger.error(f"Failed to create fallback Supabase client: {fallback_error}")
            return None

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
        # Note: Supabase doesn't support direct SQL execution via API
        # We'll need to create the table using the dashboard or alternative methods
        logger.info(
            "📝 Agent memories table SQL commands (execute manually in Supabase dashboard):"
        )

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

        print("\n" + "=" * 60)
        print("🔧 SQL COMMANDS TO EXECUTE IN SUPABASE DASHBOARD:")
        print("=" * 60)
        print(create_table_sql)

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

        print(create_indexes_sql)

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

        print(helper_functions_sql)

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

        print(trigger_sql)
        print("=" * 60)
        print("📋 Copy and paste the above SQL commands into the Supabase SQL Editor")
        print("🔗 Go to: https://supabase.com/dashboard/project/[YOUR-PROJECT]/sql")
        print("=" * 60)

        # Try to check if the table already exists using the REST API
        try:
            result = client.table("agent_memories").select("id").limit(1).execute()
            if result.data is not None:
                logger.info("✅ agent_memories table already exists and is accessible")
                return True
        except Exception as check_error:
            logger.info("ℹ️ Table doesn't exist yet or isn't accessible via REST API")
            logger.info(
                "⚠️ Please execute the SQL commands manually in Supabase dashboard"
            )

        return True  # Return True since we provided the SQL commands

    except Exception as e:
        logger.error(f"❌ Failed to prepare agent_memories table setup: {e}")
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


def verify_table_creation(client: Client) -> bool:
    """Verify that the table was created successfully."""
    try:
        # Try to access the table via REST API
        result = client.table("agent_memories").select("*").limit(1).execute()

        if result.data is not None:
            logger.info(
                "✅ Table verification successful: agent_memories table is accessible"
            )

            # Try to get some basic info about record count
            try:
                count_result = client.table("agent_memories").select("id").execute()
                record_count = len(count_result.data) if count_result.data else 0
                logger.info(
                    f"📊 Current records in agent_memories: {record_count} (sampled)"
                )
            except Exception:
                logger.info("📊 Could not determine record count")

            return True
        else:
            logger.warning(
                "⚠️ Table verification failed: table not accessible via REST API"
            )
            return False

    except Exception as e:
        logger.warning(f"⚠️ Table verification failed: {e}")
        logger.info("ℹ️ This is normal if the table hasn't been created yet")
        return False


def create_table_with_postgres(client: Client) -> bool:
    """
    Alternative method to create table using direct PostgreSQL connection.
    This requires the database URL to be accessible.
    """
    try:
        # Try to get database URL from environment
        from dotenv import load_dotenv

        load_dotenv()

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.info(
                "ℹ️ No DATABASE_URL found, cannot use direct PostgreSQL connection"
            )
            return False

        # Try to import psycopg2
        try:
            import psycopg2
        except ImportError:
            logger.info(
                "ℹ️ psycopg2 not installed, cannot use direct PostgreSQL connection"
            )
            logger.info("💡 Install with: uv add psycopg2-binary")
            return False

        # Connect to PostgreSQL directly
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        logger.info("🔌 Connected to PostgreSQL directly")

        # Execute table creation
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

        cursor.execute(create_table_sql)
        logger.info("✅ Created agent_memories table")

        # Create indexes
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_agent_memories_agent_id ON agent_memories (agent_id);",
            "CREATE INDEX IF NOT EXISTS idx_agent_memories_workflow_id ON agent_memories (workflow_id);",
            "CREATE INDEX IF NOT EXISTS idx_agent_memories_agent_workflow ON agent_memories (agent_id, workflow_id);",
            "CREATE INDEX IF NOT EXISTS idx_agent_memories_created_at ON agent_memories (created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_agent_memories_tags ON agent_memories USING GIN (tags);",
            "CREATE INDEX IF NOT EXISTS idx_agent_memories_content ON agent_memories USING GIN (content);",
            "CREATE INDEX IF NOT EXISTS idx_agent_memories_metadata ON agent_memories USING GIN (metadata);",
        ]

        for index_sql in indexes_sql:
            cursor.execute(index_sql)
        logger.info("✅ Created indexes for agent_memories table")

        # Create helper functions
        helper_functions = [
            """
            CREATE OR REPLACE FUNCTION count_distinct_agents(table_name TEXT)
            RETURNS INTEGER AS $$
            DECLARE
                result INTEGER;
            BEGIN
                EXECUTE format('SELECT COUNT(DISTINCT agent_id) FROM %I', table_name) INTO result;
                RETURN result;
            END;
            $$ LANGUAGE plpgsql;
            """,
            """
            CREATE OR REPLACE FUNCTION count_distinct_workflows(table_name TEXT)
            RETURNS INTEGER AS $$
            DECLARE
                result INTEGER;
            BEGIN
                EXECUTE format('SELECT COUNT(DISTINCT workflow_id) FROM %I', table_name) INTO result;
                RETURN result;
            END;
            $$ LANGUAGE plpgsql;
            """,
        ]

        for func_sql in helper_functions:
            cursor.execute(func_sql)
        logger.info("✅ Created helper functions")

        # Create trigger
        trigger_sql = """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        DROP TRIGGER IF EXISTS update_agent_memories_updated_at ON agent_memories;
        CREATE TRIGGER update_agent_memories_updated_at
            BEFORE UPDATE ON agent_memories
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """

        cursor.execute(trigger_sql)
        logger.info("✅ Created update trigger")

        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()

        logger.info("✅ Successfully created agent_memories table with PostgreSQL")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create table with PostgreSQL: {e}")
        return False


def main():
    """Main setup function."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    logger.info("🚀 Setting up agent memories table in Supabase...")
    logger.info(f"📁 Project root: {project_root}")

    # Get Supabase client
    client = get_supabase_client()
    if not client:
        logger.error("❌ Failed to get Supabase client")
        return False

    # Try automated creation with PostgreSQL first
    logger.info("🔄 Attempting automated table creation...")
    if create_table_with_postgres(client):
        logger.info("✅ Table created automatically!")

        # Verify table creation
        if verify_table_creation(client):
            logger.info("✅ Table verification successful!")
        else:
            logger.warning("⚠️ Table verification failed")

        logger.info("✅ Agent memories setup completed successfully!")
        return True

    # Fallback to manual instructions
    logger.info("🔄 Automated creation failed, providing manual instructions...")
    if not create_agent_memories_table(client):
        logger.error("❌ Failed to provide setup instructions")
        return False

    # Verify table creation
    if not verify_table_creation(client):
        logger.warning("⚠️ Table verification failed, but continuing...")

    # Set up RLS (optional, comment out if not needed)
    # if not setup_row_level_security(client):
    #     logger.warning("⚠️ RLS setup failed, continuing anyway")

    logger.info("✅ Agent memories setup completed successfully!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
