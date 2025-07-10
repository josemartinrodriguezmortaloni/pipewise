"""
OAuth Integration Manager for PipeWise CRM

This module manages the connection between OAuth authorizations and MCP server credentials.
When users authorize integrations, this system stores the tokens and makes them available
to MCP servers for agent usage.

Updated to use the correct 'user_accounts' table structure.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

from app.supabase.supabase_client import SupabaseCRMClient
from app.core.oauth_config import get_oauth_config

load_dotenv()
logger = logging.getLogger(__name__)


class OAuthIntegrationManager:
    """Manages OAuth tokens and MCP server credentials using user_accounts table"""

    def __init__(self):
        self.db_client = SupabaseCRMClient()
        # Import admin client for bypassing RLS policies
        from app.supabase.supabase_client import get_supabase_admin_client

        self.admin_client = get_supabase_admin_client()

        # OAuth configs are service-specific, we'll get them as needed
        self.oauth_configs = {}  # Cache for OAuth configs by service

    def get_oauth_config_for_service(self, service: str) -> Optional[Dict[str, Any]]:
        """Get OAuth config for a specific service"""
        if service not in self.oauth_configs:
            config = get_oauth_config(service)
            if config:
                self.oauth_configs[service] = config
        return self.oauth_configs.get(service)

    def store_oauth_tokens(
        self,
        user_id: str,
        service: str,  # Changed from integration_type to service
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        scope: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        profile_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Store OAuth tokens after successful authorization.

        Args:
            user_id: User ID who authorized the integration
            service: Service name (google, twitter, calendly, etc.)
            access_token: OAuth access token
            refresh_token: OAuth refresh token (if provided)
            expires_in: Token expiration time in seconds
            scope: OAuth scopes granted
            additional_data: Any additional integration-specific data
            profile_data: User profile data from the service

        Returns:
            bool: Success status
        """
        try:
            # Calculate expiration time
            expires_at = None
            if expires_in:
                expires_at = (
                    datetime.utcnow() + timedelta(seconds=expires_in)
                ).isoformat()

            # Prepare account data (OAuth credentials)
            account_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": expires_at,
                "scope": scope,
                "metadata": additional_data or {},
            }

            # Check if account already exists
            existing = (
                self.db_client.client.table("user_accounts")
                .select("*")
                .eq("user_id", user_id)
                .eq("service", service)
                .execute()
            )

            current_time = datetime.utcnow().isoformat()

            if existing.data:
                # Update existing account
                update_data = {
                    "account_data": account_data,
                    "connected": True,
                    "connected_at": current_time,
                    "updated_at": current_time,
                }

                if profile_data:
                    update_data["profile_data"] = profile_data

                self.db_client.client.table("user_accounts").update(update_data).eq(
                    "user_id", user_id
                ).eq("service", service).execute()

                logger.info(
                    f"✅ Updated OAuth tokens for {service} service for user {user_id}"
                )
            else:
                # Create new account
                insert_data = {
                    "user_id": user_id,
                    "service": service,
                    "account_data": account_data,
                    "connected": True,
                    "connected_at": current_time,
                    "profile_data": profile_data or {},
                    "created_at": current_time,
                    "updated_at": current_time,
                }

                self.db_client.client.table("user_accounts").insert(
                    insert_data
                ).execute()

                logger.info(
                    f"✅ Stored OAuth tokens for {service} service for user {user_id}"
                )

            return True

        except Exception as e:
            logger.error(f"❌ Error storing OAuth tokens for {service}: {e}")
            return False

    def get_user_integration_tokens(
        self,
        user_id: str,
        service: str,  # Changed from integration_type to service
    ) -> Optional[Dict[str, Any]]:
        """
        Get OAuth tokens for a user's service integration.

        Args:
            user_id: User ID
            service: Service name

        Returns:
            Dict with token information or None if not found
        """
        try:
            # Use admin client to bypass RLS policies
            result = (
                self.admin_client.table("user_accounts")
                .select("*")
                .eq("user_id", user_id)
                .eq("service", service)
                .eq("connected", True)
                .execute()
            )

            logger.info(
                f"✅ Query executed for {service} - user {user_id}, found {len(result.data)} records"
            )

            if result.data:
                account = result.data[0]

                # CRITICAL FIX: Decrypt account_data if it's encrypted
                account_data_raw = account.get("account_data", {})

                # Check if account_data is encrypted (string) or already decrypted (dict)
                if isinstance(account_data_raw, str):
                    # Data is encrypted, decrypt it
                    from app.core.security import safe_decrypt

                    account_data = safe_decrypt(account_data_raw)
                    logger.info(
                        f"✅ Decrypted account_data for {service} - user {user_id}"
                    )
                    logger.info(
                        f"✅ Decrypted data keys: {list(account_data.keys()) if account_data else 'None'}"
                    )
                elif isinstance(account_data_raw, dict):
                    # Data is already decrypted
                    account_data = account_data_raw
                    logger.info(
                        f"✅ Account_data already decrypted for {service} - user {user_id}"
                    )
                else:
                    # Invalid data type
                    logger.error(
                        f"❌ Invalid account_data type for {service} - user {user_id}: {type(account_data_raw)}"
                    )
                    return None

                # Check if decryption was successful
                if not account_data:
                    logger.warning(
                        f"⚠️ Failed to decrypt account_data for {service} - user {user_id}"
                    )
                    return None

                # Additional debug: Check if access_token exists
                has_access_token = bool(account_data.get("access_token"))
                logger.info(
                    f"✅ Has access_token: {has_access_token} for {service} - user {user_id}"
                )

                if not has_access_token:
                    logger.warning(
                        f"⚠️ No access_token found in decrypted data for {service} - user {user_id}"
                    )
                    return None

                # Check if token is expired
                if account_data.get("expires_at"):
                    try:
                        expires_at = datetime.fromisoformat(
                            account_data["expires_at"].replace("Z", "+00:00")
                        )
                        if (
                            datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
                            >= expires_at
                        ):
                            logger.warning(
                                f"⚠️ Access token expired for {service} - user {user_id}"
                            )
                            # Try to refresh token if refresh_token is available
                            if account_data.get("refresh_token"):
                                return self._refresh_access_token(
                                    user_id, service, account
                                )
                            else:
                                return None
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"⚠️ Invalid expires_at format for {service}: {e}"
                        )

                # Return account data in the expected format
                return {
                    "access_token": account_data.get("access_token"),
                    "refresh_token": account_data.get("refresh_token"),
                    "expires_at": account_data.get("expires_at"),
                    "scope": account_data.get("scope"),
                    "metadata": account_data.get("metadata", {}),
                    "enabled": account.get("connected", False),
                    "profile_data": account.get("profile_data", {}),
                    "connected_at": account.get("connected_at"),
                }

            return None

        except Exception as e:
            logger.error(f"❌ Error getting integration tokens for {service}: {e}")
            return None

    def _refresh_access_token(
        self, user_id: str, service: str, account_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh an expired access token using the refresh token.

        Args:
            user_id: User ID
            service: Service name
            account_data: Current account data with refresh token

        Returns:
            Updated account data or None if refresh failed
        """
        try:
            # Implementation would depend on the specific OAuth provider
            # For now, return None to indicate refresh failed
            logger.warning(f"⚠️ Token refresh not implemented for {service}")
            return None

        except Exception as e:
            logger.error(f"❌ Error refreshing token for {service}: {e}")
            return None

    def create_mcp_credentials(
        self,
        user_id: str,
        service: str,  # Changed from integration_type to service
    ) -> Optional[Dict[str, Any]]:
        """
        Create MCP server credentials from user's OAuth tokens.

        Args:
            user_id: User ID
            service: Service name

        Returns:
            Dict with MCP credentials or None if not available
        """
        integration = self.get_user_integration_tokens(user_id, service)

        if not integration:
            logger.warning(f"⚠️ No valid tokens found for {service} - user {user_id}")
            return None

        # Map service types to MCP credential formats
        mcp_credentials = {}

        if service in ["google", "google_calendar"]:
            # Google services (Gmail, Calendar)
            mcp_credentials = {
                "access_token": integration["access_token"],
                "refresh_token": integration.get("refresh_token"),
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "scope": integration.get("scope", ""),
                "expires_at": integration.get("expires_at"),
            }

        elif service == "twitter":
            # Twitter API
            mcp_credentials = {
                "access_token": integration["access_token"],
                "refresh_token": integration.get("refresh_token"),
                "bearer_token": integration.get("metadata", {}).get("bearer_token"),
                "api_key": os.getenv("TWITTER_API_KEY"),
                "api_secret": os.getenv("TWITTER_API_SECRET"),
                "user_id": integration.get("metadata", {}).get("user_id"),
                "username": integration.get("metadata", {}).get("username"),
            }

        elif service in ["calendly", "calendly_v2"]:
            # Calendly API
            mcp_credentials = {
                "access_token": integration["access_token"],
                "refresh_token": integration.get("refresh_token"),
                "organization": integration.get("metadata", {}).get("organization"),
                "user_uri": integration.get("metadata", {}).get("user_uri"),
                "scope": integration.get("scope", ""),
            }

        elif service == "pipedrive":
            # Pipedrive CRM
            mcp_credentials = {
                "access_token": integration["access_token"],
                "refresh_token": integration.get("refresh_token"),
                "api_domain": integration.get("metadata", {}).get("api_domain"),
                "company_id": integration.get("metadata", {}).get("company_id"),
            }

        elif service in ["salesforce", "salesforce_rest_api"]:
            # Salesforce CRM
            mcp_credentials = {
                "access_token": integration["access_token"],
                "refresh_token": integration.get("refresh_token"),
                "instance_url": integration.get("metadata", {}).get("instance_url"),
                "scope": integration.get("scope", ""),
            }

        elif service == "sendgrid":
            # SendGrid Email
            mcp_credentials = {
                "access_token": integration["access_token"],
                "api_key": integration.get("metadata", {}).get("api_key"),
            }

        elif service == "zoho_crm":
            # Zoho CRM
            mcp_credentials = {
                "access_token": integration["access_token"],
                "refresh_token": integration.get("refresh_token"),
                "api_domain": integration.get("metadata", {}).get("api_domain"),
                "scope": integration.get("scope", ""),
            }

        else:
            # Generic OAuth integration
            mcp_credentials = {
                "access_token": integration["access_token"],
                "refresh_token": integration.get("refresh_token"),
                "scope": integration.get("scope", ""),
                "metadata": integration.get("metadata", {}),
            }

        logger.info(f"✅ Created MCP credentials for {service} - user {user_id}")
        return mcp_credentials

    def get_enabled_integrations(self, user_id: str) -> Dict[str, Any]:
        """
        Get all enabled integrations for a user.

        Args:
            user_id: User ID

        Returns:
            Dict of enabled integrations with their credentials
        """
        try:
            result = (
                self.db_client.client.table("user_accounts")
                .select("*")
                .eq("user_id", user_id)
                .eq("connected", True)
                .execute()
            )

            enabled_integrations = {}

            for account in result.data:
                service = account["service"]
                credentials = self.create_mcp_credentials(user_id, service)

                if credentials:
                    enabled_integrations[service] = {
                        "enabled": True,
                        "connected": account.get("connected", False),
                        "credentials": credentials,
                        "profile_data": account.get("profile_data", {}),
                        "connected_at": account.get("connected_at"),
                        "updated_at": account.get("updated_at"),
                    }

            logger.info(
                f"✅ Found {len(enabled_integrations)} enabled integrations for user {user_id}"
            )
            return enabled_integrations

        except Exception as e:
            logger.error(
                f"❌ Error getting enabled integrations for user {user_id}: {e}"
            )
            return {}

    def disable_integration(self, user_id: str, service: str) -> bool:
        """
        Disable an integration for a user.

        Args:
            user_id: User ID
            service: Service name to disable

        Returns:
            bool: Success status
        """
        try:
            self.db_client.client.table("user_accounts").update(
                {"connected": False, "updated_at": datetime.utcnow().isoformat()}
            ).eq("user_id", user_id).eq("service", service).execute()

            logger.info(f"✅ Disabled {service} integration for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error disabling {service} integration: {e}")
            return False

    def is_integration_connected(self, user_id: str, service: str) -> bool:
        """
        Check if an integration is connected and has valid tokens.

        Args:
            user_id: User ID
            service: Service name

        Returns:
            bool: True if connected with valid tokens
        """
        integration = self.get_user_integration_tokens(user_id, service)
        return integration is not None and integration.get("enabled", False)


def get_oauth_integration_manager() -> OAuthIntegrationManager:
    """Get instance of OAuth Integration Manager"""
    return OAuthIntegrationManager()


# Demo and testing
if __name__ == "__main__":
    print("🔐 Testing OAuth Integration Manager")
    print("=" * 60)

    # Initialize manager
    manager = OAuthIntegrationManager()
    test_user_id = "test_user_123"

    # Test storing tokens
    success = manager.store_oauth_tokens(
        user_id=test_user_id,
        service="google",  # Changed from integration_type to service
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_in=3600,
        scope="https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar",
        additional_data={"email": "test@example.com"},
        profile_data={"name": "Test User", "email": "test@example.com"},
    )
    print(f"📋 Store tokens result: {success}")

    # Test getting integration
    integration = manager.get_user_integration_tokens(test_user_id, "google")
    print(f"🔍 Get integration: {integration is not None}")

    # Test creating MCP credentials
    credentials = manager.create_mcp_credentials(test_user_id, "google")
    print(f"🔧 MCP credentials created: {credentials is not None}")

    # Test getting all enabled integrations
    enabled = manager.get_enabled_integrations(test_user_id)
    print(f"📊 Enabled integrations: {len(enabled)}")

    print("\n✅ OAuth Integration Manager Test Complete!")
