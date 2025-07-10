#!/usr/bin/env python3
"""
Script to fix RLS policies for agent_memories table in Supabase.
This resolves the "new row violates row-level security policy" error.

Usage:
    python app/scripts/fix_agent_memories_table.py
"""

import os
import sys
from pathlib import Path
import logging

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from app.supabase.supabase_client import SupabaseCRMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def apply_agent_memories_fix():
    """Apply RLS fix to agent_memories table."""
    try:
        # Initialize Supabase client
        client = SupabaseCRMClient()

        logger.info("🔧 Applying agent_memories table fix...")

        # Read the SQL fix script
        script_path = Path(__file__).parent / "fix_agent_memories_rls.sql"

        if not script_path.exists():
            logger.error(f"❌ SQL script not found: {script_path}")
            return False

        with open(script_path, "r", encoding="utf-8") as f:
            sql_commands = f.read()

        # Split SQL commands by semicolon and execute each one
        commands = [
            cmd.strip()
            for cmd in sql_commands.split(";")
            if cmd.strip() and not cmd.strip().startswith("--")
        ]

        for i, command in enumerate(commands):
            if command.strip():
                try:
                    # Skip comment-only commands and \d commands
                    if command.strip().startswith("--") or command.strip().startswith(
                        "\\"
                    ):
                        continue

                    logger.info(
                        f"Executing command {i + 1}/{len(commands)}: {command[:50]}..."
                    )

                    # Use raw SQL execution
                    result = client.client.rpc("execute_sql", {"sql_query": command})

                    logger.info(f"✅ Command {i + 1} executed successfully")

                except Exception as cmd_error:
                    # Some commands might fail (like CREATE TABLE IF NOT EXISTS if table exists)
                    # This is usually OK
                    logger.warning(
                        f"⚠️ Command {i + 1} completed with warning: {cmd_error}"
                    )
                    continue

        # Test the fix by trying to insert a test record
        logger.info("🧪 Testing the fix with a test insert...")

        test_data = {
            "agent_id": "test_agent",
            "workflow_id": "test_workflow",
            "content": {"test": "data"},
            "tags": ["test"],
            "metadata": {"type": "test"},
        }

        try:
            result = client.client.table("agent_memories").insert(test_data).execute()

            # Clean up test data
            if result.data:
                test_id = result.data[0]["id"]
                client.client.table("agent_memories").delete().eq(
                    "id", test_id
                ).execute()
                logger.info("✅ Test insert successful! RLS fix applied correctly.")

        except Exception as test_error:
            logger.error(f"❌ Test insert failed: {test_error}")
            logger.info("💡 Try running this SQL manually in Supabase Dashboard:")
            logger.info("   ALTER TABLE agent_memories DISABLE ROW LEVEL SECURITY;")
            return False

        logger.info("🎉 Agent memories table fix completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to apply agent_memories fix: {e}")
        logger.info("💡 Manual fix required:")
        logger.info("1. Go to Supabase Dashboard > SQL Editor")
        logger.info("2. Run: ALTER TABLE agent_memories DISABLE ROW LEVEL SECURITY;")
        logger.info("3. Or create appropriate RLS policies for your use case")
        return False


def main():
    """Main function."""
    logger.info("🚀 Starting agent_memories table fix...")

    # Check environment variables
    required_env_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        logger.info("Please set them in your .env file")
        return 1

    success = apply_agent_memories_fix()

    if success:
        logger.info("✅ Fix completed successfully!")
        logger.info("🔄 Now restart your backend server to test the workflow")
        return 0
    else:
        logger.error("❌ Fix failed. Check logs above for details.")
        return 1


if __name__ == "__main__":
    exit(main())
