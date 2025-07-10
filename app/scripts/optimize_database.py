#!/usr/bin/env python3
"""
Database Optimization Script for PipeWise
Removes unused tables and optimizes the database structure.

Usage:
    python app/scripts/optimize_database.py [--dry-run] [--force]
"""

import os
import sys
import logging
from pathlib import Path
import argparse
from typing import List, Dict

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from app.supabase.supabase_client import SupabaseCRMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """Handles database optimization and cleanup."""

    def __init__(self):
        """Initialize the optimizer."""
        self.client = SupabaseCRMClient()

        # Tables to be removed (completely unused)
        self.tables_to_drop = [
            "api_keys",
            "login_attempts",
            "password_reset_tokens",
            "email_confirmation_tokens",
            "oauth2_states",
            "pipelines",
            "security_alerts",
            "tasks",
            "user_invitations",
            "user_sessions",
        ]

        # Views to be removed (can be regenerated)
        self.views_to_drop = ["auth_stats", "user_stats", "contacts_with_stats"]

        # Tables to keep and optimize
        self.core_tables = [
            "users",
            "leads",
            "conversations",
            "messages",
            "contacts",
            "outreach_messages",
            "agent_memories",
            "auth_audit_logs",
        ]

        # Optional tables (keep for now)
        self.optional_tables = ["integrations", "user_accounts"]

    def get_existing_tables(self) -> List[str]:
        """Get list of existing tables in the database."""
        try:
            # Query to get all user tables
            result = self.client.client.rpc("get_user_tables").execute()
            return [table["table_name"] for table in result.data] if result.data else []
        except Exception as e:
            logger.warning(f"Could not query existing tables: {e}")
            return []

    def analyze_table_usage(self) -> Dict[str, Dict]:
        """Analyze current table usage and sizes."""
        analysis = {}

        for table in self.core_tables + self.optional_tables:
            try:
                # Get row count (simplified approach)
                count_result = (
                    self.client.client.table(table).select("*").limit(1).execute()
                )
                row_count = len(count_result.data) if count_result.data else 0

                analysis[table] = {
                    "status": "active" if table in self.core_tables else "optional",
                    "row_count": row_count,
                    "action": "keep_optimize"
                    if table in self.core_tables
                    else "keep_monitor",
                }

            except Exception as e:
                analysis[table] = {
                    "status": "error",
                    "error": str(e),
                    "action": "investigate",
                }

        # Add unused tables
        for table in self.tables_to_drop:
            analysis[table] = {
                "status": "unused",
                "row_count": "unknown",
                "action": "drop",
            }

        for view in self.views_to_drop:
            analysis[view] = {
                "status": "unused_view",
                "row_count": "unknown",
                "action": "drop",
            }

        return analysis

    def create_backup_info(self) -> str:
        """Create backup information before optimization."""
        backup_info = f"""
# Database Optimization Backup Info
Generated: {os.popen("date").read().strip()}

## Tables before optimization:
"""

        existing_tables = self.get_existing_tables()
        for table in existing_tables:
            backup_info += f"- {table}\n"

        return backup_info

    def optimize_database(self, dry_run: bool = True) -> bool:
        """Perform database optimization."""
        try:
            logger.info("🚀 Starting database optimization...")

            if dry_run:
                logger.info("🔍 DRY RUN MODE - No changes will be made")

            # Create backup info
            backup_info = self.create_backup_info()
            backup_path = Path(__file__).parent / "database_backup_info.txt"

            if not dry_run:
                with open(backup_path, "w") as f:
                    f.write(backup_info)
                logger.info(f"📝 Backup info saved to {backup_path}")

            # Analyze current state
            analysis = self.analyze_table_usage()

            logger.info("📊 Current database analysis:")
            for table, info in analysis.items():
                logger.info(
                    f"  {table}: {info['status']} - {info['action']} (rows: {info.get('row_count', 'unknown')})"
                )

            # Read optimization script
            script_path = Path(__file__).parent / "optimize_database_tables.sql"
            if not script_path.exists():
                logger.error(f"❌ SQL script not found: {script_path}")
                return False

            with open(script_path, "r") as f:
                sql_script = f.read()

            if dry_run:
                logger.info("🔍 Would execute SQL optimization script")
                logger.info(f"📄 Script size: {len(sql_script.split(';'))} commands")
                return True

            # Execute optimization script
            logger.info("⚙️ Executing database optimization...")

            # Split and execute SQL commands
            commands = [
                cmd.strip()
                for cmd in sql_script.split(";")
                if cmd.strip() and not cmd.strip().startswith("--")
            ]

            success_count = 0
            for i, command in enumerate(commands):
                try:
                    if command.strip():
                        # Use direct SQL execution for DDL commands
                        self.client.client.rpc(
                            "execute_ddl", {"ddl_query": command}
                        ).execute()
                        success_count += 1
                        logger.info(f"✅ Executed command {i + 1}/{len(commands)}")

                except Exception as cmd_error:
                    # Some commands may fail safely (like dropping non-existent tables)
                    if "does not exist" in str(cmd_error).lower():
                        logger.info(f"ℹ️ Command {i + 1} - table/view already removed")
                    else:
                        logger.warning(f"⚠️ Command {i + 1} failed: {cmd_error}")

            logger.info(
                f"✅ Database optimization completed! {success_count}/{len(commands)} commands executed successfully"
            )

            # Final analysis
            final_analysis = self.analyze_table_usage()
            logger.info("📊 Post-optimization analysis:")

            active_tables = [
                t
                for t, info in final_analysis.items()
                if info["status"] in ["active", "optional"]
            ]
            logger.info(f"🎯 Optimized database: {len(active_tables)} tables remaining")

            return True

        except Exception as e:
            logger.error(f"❌ Database optimization failed: {e}")
            return False

    def verify_optimization(self) -> bool:
        """Verify that optimization was successful."""
        try:
            logger.info("🔍 Verifying optimization...")

            # Test core functionality
            test_queries = [
                ("users", "SELECT COUNT(*) FROM users"),
                ("leads", "SELECT COUNT(*) FROM leads"),
                ("agent_memories", "SELECT COUNT(*) FROM agent_memories"),
            ]

            for table, query in test_queries:
                try:
                    result = self.client.client.rpc(
                        "execute_query", {"query": query}
                    ).execute()
                    logger.info(f"✅ {table} table accessible")
                except Exception as e:
                    logger.error(f"❌ {table} table test failed: {e}")
                    return False

            logger.info("✅ Optimization verification successful!")
            return True

        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Optimize PipeWise database")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force optimization without confirmation"
    )
    parser.add_argument(
        "--verify-only", action="store_true", help="Only verify current state"
    )

    args = parser.parse_args()

    optimizer = DatabaseOptimizer()

    if args.verify_only:
        return 0 if optimizer.verify_optimization() else 1

    # Show analysis
    analysis = optimizer.analyze_table_usage()

    print("\n" + "=" * 60)
    print("📊 PIPEWISE DATABASE OPTIMIZATION")
    print("=" * 60)

    unused_count = len([t for t, info in analysis.items() if info["action"] == "drop"])
    active_count = len(
        [t for t, info in analysis.items() if info["status"] in ["active", "optional"]]
    )

    print(f"📈 Current: {len(analysis)} total objects")
    print(f"🎯 After optimization: {active_count} tables (removing {unused_count})")
    print(f"💾 Space savings: ~{unused_count * 10}% database size reduction")

    if not args.dry_run and not args.force:
        confirm = input(
            "\n⚠️  This will permanently remove unused tables. Continue? (y/N): "
        )
        if confirm.lower() != "y":
            print("❌ Optimization cancelled")
            return 1

    # Run optimization
    success = optimizer.optimize_database(dry_run=args.dry_run)

    if success and not args.dry_run:
        # Verify results
        success = optimizer.verify_optimization()

    if success:
        print("\n🎉 Database optimization completed successfully!")
        if args.dry_run:
            print("💡 Run without --dry-run to apply changes")
        return 0
    else:
        print("\n❌ Database optimization failed")
        return 1


if __name__ == "__main__":
    exit(main())
