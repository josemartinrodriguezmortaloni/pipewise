#!/usr/bin/env python3
"""
OAuth and MCP Diagnostic Script

This script checks the OAuth credentials and MCP server configuration
to identify and fix issues with credential retrieval and MCP server connections.

Usage:
    python fix_oauth_mcp_diagnostics.py [--user-id USER_ID] [--service SERVICE] [--fix]
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import argparse

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from app.supabase.supabase_client import SupabaseCRMClient
from app.api.oauth_integration_manager import OAuthIntegrationManager
from app.ai_agents.mcp.mcp_server_manager import validate_oauth_tokens_for_service
from app.core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OAuthMCPDiagnostics:
    """OAuth and MCP diagnostic tools"""

    def __init__(self):
        self.db_client = SupabaseCRMClient()
        self.oauth_manager = OAuthIntegrationManager()
        self.settings = get_settings()

    def check_database_tables(self) -> Dict[str, Any]:
        """Check if required database tables exist"""
        logger.info("🔍 Checking database tables...")

        tables_to_check = [
            "user_accounts",
            "users",
            "leads",
            "conversations",
            "messages",
        ]

        results = {}

        for table in tables_to_check:
            try:
                result = (
                    self.db_client.client.table(table).select("*").limit(1).execute()
                )
                results[table] = {
                    "exists": True,
                    "accessible": True,
                    "record_count": len(result.data),
                    "error": None,
                }
                logger.info(f"✅ Table '{table}' exists and accessible")
            except Exception as e:
                results[table] = {
                    "exists": False,
                    "accessible": False,
                    "record_count": 0,
                    "error": str(e),
                }
                logger.error(f"❌ Table '{table}' error: {e}")

        return results

    def check_user_accounts_structure(self) -> Dict[str, Any]:
        """Check user_accounts table structure"""
        logger.info("🔍 Checking user_accounts table structure...")

        try:
            # Try to get a sample record to check structure
            result = (
                self.db_client.client.table("user_accounts")
                .select("*")
                .limit(1)
                .execute()
            )

            if result.data:
                sample_record = result.data[0]
                logger.info(f"✅ user_accounts table structure:")
                for key, value in sample_record.items():
                    logger.info(f"   - {key}: {type(value).__name__}")

                return {
                    "exists": True,
                    "fields": list(sample_record.keys()),
                    "sample_record": sample_record,
                    "has_account_data": "account_data" in sample_record,
                    "has_service_field": "service" in sample_record,
                    "has_connected_field": "connected" in sample_record,
                }
            else:
                logger.info("⚪ user_accounts table is empty")
                return {
                    "exists": True,
                    "fields": [],
                    "sample_record": None,
                    "has_account_data": False,
                    "has_service_field": False,
                    "has_connected_field": False,
                }

        except Exception as e:
            logger.error(f"❌ Error checking user_accounts structure: {e}")
            return {"exists": False, "error": str(e)}

    def check_oauth_credentials(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Check OAuth credentials for a user or all users"""
        logger.info(f"🔍 Checking OAuth credentials for user: {user_id or 'all users'}")

        results = {}

        try:
            if user_id:
                # Check specific user
                query = (
                    self.db_client.client.table("user_accounts")
                    .select("*")
                    .eq("user_id", user_id)
                )
            else:
                # Check all users
                query = (
                    self.db_client.client.table("user_accounts").select("*").limit(10)
                )

            result = query.execute()

            if result.data:
                for account in result.data:
                    user_id_key = account.get("user_id")
                    service = account.get("service")
                    connected = account.get("connected", False)
                    account_data = account.get("account_data", {})

                    if user_id_key not in results:
                        results[user_id_key] = {}

                    # Check if account_data has required fields
                    has_access_token = bool(account_data.get("access_token"))
                    has_refresh_token = bool(account_data.get("refresh_token"))
                    expires_at = account_data.get("expires_at")

                    # Check if token is expired
                    is_expired = False
                    if expires_at:
                        try:
                            expires_datetime = datetime.fromisoformat(
                                expires_at.replace("Z", "+00:00")
                            )
                            is_expired = datetime.now() >= expires_datetime
                        except Exception:
                            is_expired = True

                    results[user_id_key][service] = {
                        "connected": connected,
                        "has_access_token": has_access_token,
                        "has_refresh_token": has_refresh_token,
                        "expires_at": expires_at,
                        "is_expired": is_expired,
                        "account_data_keys": list(account_data.keys()),
                        "created_at": account.get("created_at"),
                        "updated_at": account.get("updated_at"),
                    }

                    status = (
                        "🟢"
                        if connected and has_access_token and not is_expired
                        else "🔴"
                    )
                    logger.info(
                        f"{status} User {user_id_key} - {service}: connected={connected}, has_token={has_access_token}, expired={is_expired}"
                    )
            else:
                logger.info("⚪ No OAuth credentials found")

        except Exception as e:
            logger.error(f"❌ Error checking OAuth credentials: {e}")
            results["error"] = str(e)

        return results

    def check_mcp_configuration(self) -> Dict[str, Any]:
        """Check MCP server configuration"""
        logger.info("🔍 Checking MCP server configuration...")

        results = {
            "disable_mcp": os.getenv("DISABLE_MCP", "false").lower() == "true",
            "environment_variables": {},
            "node_js_available": False,
            "npm_available": False,
            "pipedream_config": {},
        }

        # Check environment variables
        env_vars_to_check = [
            "DISABLE_MCP",
            "PIPEDREAM_CLIENT_SECRET",
            "PIPEDREAM_PROJECT_ID",
            "PIPEDREAM_ENVIRONMENT",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "TWITTER_API_KEY",
            "TWITTER_API_SECRET",
        ]

        for var in env_vars_to_check:
            value = os.getenv(var)
            results["environment_variables"][var] = {
                "exists": value is not None,
                "value": "***" if value else None,
                "length": len(value) if value else 0,
            }

            status = "✅" if value else "❌"
            logger.info(f"{status} {var}: {'Set' if value else 'Not set'}")

        # Check Node.js availability
        try:
            import subprocess

            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                results["node_js_available"] = True
                logger.info(f"✅ Node.js available: {result.stdout.strip()}")
            else:
                results["node_js_available"] = False
                logger.info("❌ Node.js not available")
        except Exception as e:
            results["node_js_available"] = False
            logger.info(f"❌ Node.js check failed: {e}")

        # Check npm availability
        try:
            import subprocess

            result = subprocess.run(
                ["npm", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                results["npm_available"] = True
                logger.info(f"✅ npm available: {result.stdout.strip()}")
            else:
                results["npm_available"] = False
                logger.info("❌ npm not available")
        except Exception as e:
            results["npm_available"] = False
            logger.info(f"❌ npm check failed: {e}")

        return results

    def test_oauth_integration_manager(
        self, user_id: str, service: str
    ) -> Dict[str, Any]:
        """Test OAuth integration manager functionality"""
        logger.info(f"🔍 Testing OAuth integration manager for {service}")

        results = {"user_id": user_id, "service": service, "tests": {}}

        try:
            # Test 1: Check if integration is connected
            is_connected = self.oauth_manager.is_integration_connected(user_id, service)
            results["tests"]["is_connected"] = {
                "success": True,
                "result": is_connected,
                "error": None,
            }
            logger.info(f"✅ is_integration_connected: {is_connected}")

        except Exception as e:
            results["tests"]["is_connected"] = {
                "success": False,
                "result": None,
                "error": str(e),
            }
            logger.error(f"❌ is_integration_connected failed: {e}")

        try:
            # Test 2: Get user integration tokens
            tokens = self.oauth_manager.get_user_integration_tokens(user_id, service)
            results["tests"]["get_tokens"] = {
                "success": True,
                "result": bool(tokens),
                "token_keys": list(tokens.keys()) if tokens else [],
                "error": None,
            }
            logger.info(f"✅ get_user_integration_tokens: {bool(tokens)}")

        except Exception as e:
            results["tests"]["get_tokens"] = {
                "success": False,
                "result": None,
                "error": str(e),
            }
            logger.error(f"❌ get_user_integration_tokens failed: {e}")

        try:
            # Test 3: Create MCP credentials
            credentials = self.oauth_manager.create_mcp_credentials(user_id, service)
            results["tests"]["create_mcp_credentials"] = {
                "success": True,
                "result": bool(credentials),
                "credential_keys": list(credentials.keys()) if credentials else [],
                "error": None,
            }
            logger.info(f"✅ create_mcp_credentials: {bool(credentials)}")

        except Exception as e:
            results["tests"]["create_mcp_credentials"] = {
                "success": False,
                "result": None,
                "error": str(e),
            }
            logger.error(f"❌ create_mcp_credentials failed: {e}")

        try:
            # Test 4: Get enabled integrations
            enabled = self.oauth_manager.get_enabled_integrations(user_id)
            results["tests"]["get_enabled_integrations"] = {
                "success": True,
                "result": list(enabled.keys()) if enabled else [],
                "error": None,
            }
            logger.info(
                f"✅ get_enabled_integrations: {list(enabled.keys()) if enabled else []}"
            )

        except Exception as e:
            results["tests"]["get_enabled_integrations"] = {
                "success": False,
                "result": None,
                "error": str(e),
            }
            logger.error(f"❌ get_enabled_integrations failed: {e}")

        return results

    def test_mcp_server_manager(self, user_id: str, service: str) -> Dict[str, Any]:
        """Test MCP server manager functionality"""
        logger.info(f"🔍 Testing MCP server manager for {service}")

        results = {"user_id": user_id, "service": service, "tests": {}}

        try:
            # Test 1: Validate OAuth tokens
            is_valid = validate_oauth_tokens_for_service(user_id, service)
            results["tests"]["validate_oauth_tokens"] = {
                "success": True,
                "result": is_valid,
                "error": None,
            }
            logger.info(f"✅ validate_oauth_tokens_for_service: {is_valid}")

        except Exception as e:
            results["tests"]["validate_oauth_tokens"] = {
                "success": False,
                "result": None,
                "error": str(e),
            }
            logger.error(f"❌ validate_oauth_tokens_for_service failed: {e}")

        return results

    def create_test_user_account(self, user_id: str, service: str) -> Dict[str, Any]:
        """Create a test user account for testing"""
        logger.info(f"🔧 Creating test user account for {service}")

        test_account_data = {
            "access_token": f"test_token_{service}_{user_id}",
            "refresh_token": f"test_refresh_{service}_{user_id}",
            "expires_at": (datetime.now().replace(year=2025)).isoformat(),
            "token_type": "Bearer",
            "scope": "read write",
            "metadata": {
                "test_account": True,
                "created_by": "diagnostic_script",
                "service_account_id": f"test_service_id_{service}",
            },
        }

        try:
            # Use the admin client to bypass RLS policies
            from app.supabase.supabase_client import get_supabase_admin_client

            admin_client = get_supabase_admin_client()

            # First, ensure the user exists in the users table
            existing_user = (
                admin_client.table("users").select("*").eq("id", user_id).execute()
            )

            if not existing_user.data:
                # Create the user first
                user_data = {
                    "id": user_id,
                    "email": f"test_{user_id}@example.com",
                    "full_name": f"Test User {user_id[:8]}",
                    "role": "user",
                    "auth_provider": "email",
                    "is_active": True,
                    "email_confirmed": True,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "preferences": {
                        "theme": "light",
                        "language": "en",
                        "timezone": "UTC",
                    },
                }

                admin_client.table("users").insert(user_data).execute()
                logger.info(f"✅ Created test user {user_id}")
            else:
                logger.info(f"✅ User {user_id} already exists")

            # Now create or update the OAuth account
            existing_account = (
                admin_client.table("user_accounts")
                .select("*")
                .eq("user_id", user_id)
                .eq("service", service)
                .execute()
            )

            current_time = datetime.now().isoformat()

            if existing_account.data:
                # Update existing
                admin_client.table("user_accounts").update(
                    {
                        "account_data": test_account_data,
                        "connected": True,
                        "updated_at": current_time,
                    }
                ).eq("user_id", user_id).eq("service", service).execute()

                logger.info(f"✅ Updated test account for {service}")
            else:
                # Create new
                admin_client.table("user_accounts").insert(
                    {
                        "user_id": user_id,
                        "service": service,
                        "account_data": test_account_data,
                        "connected": True,
                        "connected_at": current_time,
                        "created_at": current_time,
                        "updated_at": current_time,
                        "profile_data": {
                            "test_profile": True,
                            "service": service,
                        },
                    }
                ).execute()

                logger.info(f"✅ Created test account for {service}")

            return {
                "success": True,
                "user_id": user_id,
                "service": service,
                "account_data": test_account_data,
                "error": None,
            }

        except Exception as e:
            logger.error(f"❌ Error creating test account: {e}")
            return {
                "success": False,
                "user_id": user_id,
                "service": service,
                "error": str(e),
            }

    def run_comprehensive_diagnostics(
        self, user_id: Optional[str] = None, service: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run comprehensive diagnostics"""
        logger.info("🚀 Running comprehensive OAuth and MCP diagnostics...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "service": service,
            "tests": {},
        }

        # 1. Check database tables
        results["tests"]["database_tables"] = self.check_database_tables()

        # 2. Check user_accounts structure
        results["tests"]["user_accounts_structure"] = (
            self.check_user_accounts_structure()
        )

        # 3. Check OAuth credentials
        results["tests"]["oauth_credentials"] = self.check_oauth_credentials(user_id)

        # 4. Check MCP configuration
        results["tests"]["mcp_configuration"] = self.check_mcp_configuration()

        # 5. Test OAuth integration manager (if user_id and service provided)
        if user_id and service:
            results["tests"]["oauth_integration_manager"] = (
                self.test_oauth_integration_manager(user_id, service)
            )
            results["tests"]["mcp_server_manager"] = self.test_mcp_server_manager(
                user_id, service
            )

        # Summary
        results["summary"] = self.generate_summary(results)

        return results

    def generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate diagnostic summary"""
        summary = {
            "database_ok": False,
            "oauth_credentials_ok": False,
            "mcp_configuration_ok": False,
            "overall_status": "❌ Issues found",
            "recommendations": [],
        }

        # Check database status
        db_tests = results["tests"].get("database_tables", {})
        if db_tests.get("user_accounts", {}).get("exists"):
            summary["database_ok"] = True
        else:
            summary["recommendations"].append("Fix database table structure")

        # Check OAuth credentials
        oauth_tests = results["tests"].get("oauth_credentials", {})
        if oauth_tests and not oauth_tests.get("error"):
            summary["oauth_credentials_ok"] = True
        else:
            summary["recommendations"].append("Set up OAuth credentials")

        # Check MCP configuration
        mcp_tests = results["tests"].get("mcp_configuration", {})
        if mcp_tests.get("disable_mcp") == False:
            summary["mcp_configuration_ok"] = True
        else:
            summary["recommendations"].append(
                "Enable MCP servers (set DISABLE_MCP=false)"
            )

        # Overall status
        if (
            summary["database_ok"]
            and summary["oauth_credentials_ok"]
            and summary["mcp_configuration_ok"]
        ):
            summary["overall_status"] = "✅ All systems operational"
        elif summary["database_ok"] and summary["oauth_credentials_ok"]:
            summary["overall_status"] = "⚠️ Partial functionality (MCP disabled)"
        else:
            summary["overall_status"] = "❌ Critical issues found"

        return summary


def main():
    """Main diagnostic function"""
    parser = argparse.ArgumentParser(description="OAuth and MCP Diagnostics")
    parser.add_argument("--user-id", help="User ID to check")
    parser.add_argument("--service", help="Service to check (e.g., google, twitter)")
    parser.add_argument(
        "--create-test", action="store_true", help="Create test user account"
    )
    parser.add_argument("--fix", action="store_true", help="Apply fixes where possible")

    args = parser.parse_args()

    diagnostics = OAuthMCPDiagnostics()

    if args.create_test and args.user_id and args.service:
        logger.info("🔧 Creating test user account...")
        result = diagnostics.create_test_user_account(args.user_id, args.service)
        print(f"Test account creation result: {result}")

    # Run comprehensive diagnostics
    results = diagnostics.run_comprehensive_diagnostics(args.user_id, args.service)

    # Print summary
    summary = results["summary"]
    print("\n" + "=" * 50)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 50)
    print(f"Overall Status: {summary['overall_status']}")
    print(f"Database OK: {'✅' if summary['database_ok'] else '❌'}")
    print(f"OAuth Credentials OK: {'✅' if summary['oauth_credentials_ok'] else '❌'}")
    print(f"MCP Configuration OK: {'✅' if summary['mcp_configuration_ok'] else '❌'}")

    if summary["recommendations"]:
        print("\nRecommendations:")
        for i, rec in enumerate(summary["recommendations"], 1):
            print(f"{i}. {rec}")

    # Apply fixes if requested
    if args.fix:
        logger.info("🔧 Applying fixes...")

        # Fix 1: Enable MCP if disabled
        if not summary["mcp_configuration_ok"]:
            logger.info("Setting DISABLE_MCP=false")
            os.environ["DISABLE_MCP"] = "false"

        # Fix 2: Create test account if needed
        if args.user_id and args.service and not summary["oauth_credentials_ok"]:
            logger.info("Creating test OAuth credentials...")
            diagnostics.create_test_user_account(args.user_id, args.service)

    print("\n" + "=" * 50)
    print("Para detalles completos, revisa los logs arriba.")
    print("=" * 50)


if __name__ == "__main__":
    main()
