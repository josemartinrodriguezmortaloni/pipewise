"""
OAuth Token Refresh Module

This module handles automatic refresh of expired OAuth tokens for MCP integrations.
It provides functions to refresh tokens for different OAuth providers and update
them in Supabase storage.

Key Features:
- Automatic token refresh for expired tokens
- Provider-specific refresh logic
- Supabase integration for token storage
- Retry logic for failed refresh attempts
- Comprehensive error handling

Following PRD: Task 3.0 - Integrar MCP con Sistema OAuth Existente
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .error_handler import (
    MCPAuthenticationError,
    MCPConfigurationError,
    get_error_handler,
    MCPErrorCategory,
)
from .retry_handler import retry_mcp_operation
from .oauth_integration import OAuthTokens, OAuthProvider

logger = logging.getLogger(__name__)


@dataclass
class RefreshResult:
    """Result of token refresh operation"""

    success: bool
    new_tokens: Optional[OAuthTokens] = None
    error_message: Optional[str] = None
    expires_at: Optional[datetime] = None


class OAuthTokenRefreshManager:
    """
    Manages OAuth token refresh operations for different providers.

    Handles automatic refresh of expired tokens and updates them in Supabase.
    Each provider has specific refresh logic and API endpoints.
    """

    def __init__(self):
        self.error_handler = get_error_handler()
        self._refresh_cache = {}  # Cache refresh results to avoid repeated calls

    @retry_mcp_operation(
        max_attempts=3, service_name="token_refresh", log_attempts=True
    )
    async def refresh_mcp_token(
        self, user_id: str, service_name: str, force_refresh: bool = False
    ) -> RefreshResult:
        """
        Refresh OAuth token for a specific service.

        Args:
            user_id: User identifier
            service_name: Name of the service
            force_refresh: Force refresh even if token is not expired

        Returns:
            RefreshResult with success status and new tokens
        """
        try:
            # Get current token info
            current_tokens = await self._get_current_tokens(user_id, service_name)

            if not current_tokens:
                return RefreshResult(
                    success=False,
                    error_message=f"No existing tokens found for {service_name}",
                )

            # Check if refresh is needed
            if not force_refresh and not current_tokens.expires_soon(minutes=10):
                logger.debug(f"Token for {service_name} not expired, skipping refresh")
                return RefreshResult(
                    success=True,
                    new_tokens=current_tokens,
                    expires_at=current_tokens.expires_at,
                )

            # Check refresh cache
            cache_key = f"{user_id}:{service_name}"
            cached_result = self._get_cached_refresh_result(cache_key)
            if cached_result:
                logger.debug(f"Using cached refresh result for {service_name}")
                return cached_result

            # Perform provider-specific refresh
            result = await self._refresh_by_provider(current_tokens, service_name)

            if result.success and result.new_tokens:
                # Update tokens in Supabase
                await self._update_tokens_in_supabase(
                    user_id, service_name, result.new_tokens
                )
                logger.info(f"✅ Successfully refreshed OAuth token for {service_name}")

                # Cache the result
                self._cache_refresh_result(cache_key, result)
            else:
                logger.warning(
                    f"⚠️ Failed to refresh token for {service_name}: {result.error_message}"
                )

            return result

        except Exception as e:
            mcp_error = self.error_handler.handle_error(
                e,
                service_name=service_name,
                operation="refresh_oauth_token",
                context={"user_id": user_id},
            )

            return RefreshResult(
                success=False, error_message=mcp_error.get_user_friendly_message()
            )

    async def _refresh_by_provider(
        self, current_tokens: OAuthTokens, service_name: str
    ) -> RefreshResult:
        """
        Refresh tokens based on OAuth provider.

        Args:
            current_tokens: Current OAuth tokens
            service_name: Name of the service

        Returns:
            RefreshResult with new tokens or error
        """
        if not current_tokens.refresh_token:
            return RefreshResult(
                success=False,
                error_message=f"No refresh token available for {service_name}",
            )

        provider = current_tokens.provider

        if provider == OAuthProvider.GOOGLE:
            return await self._refresh_google_token(current_tokens)
        elif provider == OAuthProvider.TWITTER:
            return await self._refresh_twitter_token(current_tokens)
        elif provider == OAuthProvider.SENDGRID:
            return await self._refresh_sendgrid_token(current_tokens)
        elif provider == OAuthProvider.CALENDLY:
            return await self._refresh_calendly_token(current_tokens)
        elif provider == OAuthProvider.PIPEDRIVE:
            return await self._refresh_pipedrive_token(current_tokens)
        elif provider == OAuthProvider.SALESFORCE:
            return await self._refresh_salesforce_token(current_tokens)
        elif provider == OAuthProvider.ZOHO:
            return await self._refresh_zoho_token(current_tokens)
        else:
            return RefreshResult(
                success=False,
                error_message=f"Unsupported OAuth provider: {provider.value if provider else 'Unknown'}",
            )

    async def _refresh_google_token(self, tokens: OAuthTokens) -> RefreshResult:
        """Refresh Google OAuth token"""
        try:
            import httpx

            # Google OAuth 2.0 token refresh endpoint
            refresh_url = "https://oauth2.googleapis.com/token"

            # Get client credentials from environment
            import os

            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

            if not client_id or not client_secret:
                return RefreshResult(
                    success=False,
                    error_message="Google OAuth credentials not configured",
                )

            # Prepare refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": tokens.refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(refresh_url, data=refresh_data)
                response.raise_for_status()

                token_data = response.json()

                # Create new tokens
                new_tokens = OAuthTokens(
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", tokens.refresh_token),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_at=datetime.now()
                    + timedelta(seconds=token_data.get("expires_in", 3600)),
                    scope=token_data.get("scope", tokens.scope),
                    provider=OAuthProvider.GOOGLE,
                    user_id=tokens.user_id,
                    service_account_id=tokens.service_account_id,
                )

                return RefreshResult(
                    success=True,
                    new_tokens=new_tokens,
                    expires_at=new_tokens.expires_at,
                )

        except Exception as e:
            logger.error(f"❌ Google token refresh failed: {e}")
            return RefreshResult(
                success=False, error_message=f"Google token refresh failed: {str(e)}"
            )

    async def _refresh_twitter_token(self, tokens: OAuthTokens) -> RefreshResult:
        """Refresh Twitter OAuth token"""
        try:
            import httpx

            # Twitter OAuth 2.0 token refresh endpoint
            refresh_url = "https://api.twitter.com/2/oauth2/token"

            # Get client credentials from environment
            import os

            client_id = os.getenv("TWITTER_CLIENT_ID")
            client_secret = os.getenv("TWITTER_CLIENT_SECRET")

            if not client_id or not client_secret:
                return RefreshResult(
                    success=False,
                    error_message="Twitter OAuth credentials not configured",
                )

            # Prepare refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": tokens.refresh_token,
                "client_id": client_id,
            }

            # Twitter uses Basic Auth for client credentials
            import base64

            auth_string = base64.b64encode(
                f"{client_id}:{client_secret}".encode()
            ).decode()

            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    refresh_url, data=refresh_data, headers=headers
                )
                response.raise_for_status()

                token_data = response.json()

                # Create new tokens
                new_tokens = OAuthTokens(
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", tokens.refresh_token),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_at=datetime.now()
                    + timedelta(seconds=token_data.get("expires_in", 7200)),
                    scope=token_data.get("scope", tokens.scope),
                    provider=OAuthProvider.TWITTER,
                    user_id=tokens.user_id,
                    service_account_id=tokens.service_account_id,
                )

                return RefreshResult(
                    success=True,
                    new_tokens=new_tokens,
                    expires_at=new_tokens.expires_at,
                )

        except Exception as e:
            logger.error(f"❌ Twitter token refresh failed: {e}")
            return RefreshResult(
                success=False, error_message=f"Twitter token refresh failed: {str(e)}"
            )

    async def _refresh_sendgrid_token(self, tokens: OAuthTokens) -> RefreshResult:
        """Refresh SendGrid OAuth token"""
        # SendGrid typically uses API keys, not OAuth refresh tokens
        return RefreshResult(
            success=False,
            error_message="SendGrid uses API keys, not OAuth refresh tokens",
        )

    async def _refresh_calendly_token(self, tokens: OAuthTokens) -> RefreshResult:
        """Refresh Calendly OAuth token"""
        try:
            import httpx

            # Calendly OAuth 2.0 token refresh endpoint
            refresh_url = "https://auth.calendly.com/oauth/token"

            # Get client credentials from environment
            import os

            client_id = os.getenv("CALENDLY_CLIENT_ID")
            client_secret = os.getenv("CALENDLY_CLIENT_SECRET")

            if not client_id or not client_secret:
                return RefreshResult(
                    success=False,
                    error_message="Calendly OAuth credentials not configured",
                )

            # Prepare refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": tokens.refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(refresh_url, data=refresh_data)
                response.raise_for_status()

                token_data = response.json()

                # Create new tokens
                new_tokens = OAuthTokens(
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", tokens.refresh_token),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_at=datetime.now()
                    + timedelta(seconds=token_data.get("expires_in", 3600)),
                    scope=token_data.get("scope", tokens.scope),
                    provider=OAuthProvider.CALENDLY,
                    user_id=tokens.user_id,
                    service_account_id=tokens.service_account_id,
                )

                return RefreshResult(
                    success=True,
                    new_tokens=new_tokens,
                    expires_at=new_tokens.expires_at,
                )

        except Exception as e:
            logger.error(f"❌ Calendly token refresh failed: {e}")
            return RefreshResult(
                success=False, error_message=f"Calendly token refresh failed: {str(e)}"
            )

    async def _refresh_pipedrive_token(self, tokens: OAuthTokens) -> RefreshResult:
        """Refresh Pipedrive OAuth token"""
        try:
            import httpx

            # Pipedrive OAuth 2.0 token refresh endpoint
            refresh_url = "https://oauth.pipedrive.com/oauth/token"

            # Get client credentials from environment
            import os

            client_id = os.getenv("PIPEDRIVE_CLIENT_ID")
            client_secret = os.getenv("PIPEDRIVE_CLIENT_SECRET")

            if not client_id or not client_secret:
                return RefreshResult(
                    success=False,
                    error_message="Pipedrive OAuth credentials not configured",
                )

            # Prepare refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": tokens.refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(refresh_url, data=refresh_data)
                response.raise_for_status()

                token_data = response.json()

                # Create new tokens
                new_tokens = OAuthTokens(
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", tokens.refresh_token),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_at=datetime.now()
                    + timedelta(seconds=token_data.get("expires_in", 3600)),
                    scope=token_data.get("scope", tokens.scope),
                    provider=OAuthProvider.PIPEDRIVE,
                    user_id=tokens.user_id,
                    service_account_id=tokens.service_account_id,
                )

                return RefreshResult(
                    success=True,
                    new_tokens=new_tokens,
                    expires_at=new_tokens.expires_at,
                )

        except Exception as e:
            logger.error(f"❌ Pipedrive token refresh failed: {e}")
            return RefreshResult(
                success=False, error_message=f"Pipedrive token refresh failed: {str(e)}"
            )

    async def _refresh_salesforce_token(self, tokens: OAuthTokens) -> RefreshResult:
        """Refresh Salesforce OAuth token"""
        try:
            import httpx

            # Salesforce OAuth 2.0 token refresh endpoint
            # The instance URL is stored in service_account_id
            instance_url = tokens.service_account_id or "https://login.salesforce.com"
            refresh_url = f"{instance_url}/services/oauth2/token"

            # Get client credentials from environment
            import os

            client_id = os.getenv("SALESFORCE_CLIENT_ID")
            client_secret = os.getenv("SALESFORCE_CLIENT_SECRET")

            if not client_id or not client_secret:
                return RefreshResult(
                    success=False,
                    error_message="Salesforce OAuth credentials not configured",
                )

            # Prepare refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": tokens.refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(refresh_url, data=refresh_data)
                response.raise_for_status()

                token_data = response.json()

                # Create new tokens
                new_tokens = OAuthTokens(
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", tokens.refresh_token),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_at=datetime.now()
                    + timedelta(seconds=token_data.get("expires_in", 3600)),
                    scope=token_data.get("scope", tokens.scope),
                    provider=OAuthProvider.SALESFORCE,
                    user_id=tokens.user_id,
                    service_account_id=token_data.get(
                        "instance_url", tokens.service_account_id
                    ),
                )

                return RefreshResult(
                    success=True,
                    new_tokens=new_tokens,
                    expires_at=new_tokens.expires_at,
                )

        except Exception as e:
            logger.error(f"❌ Salesforce token refresh failed: {e}")
            return RefreshResult(
                success=False,
                error_message=f"Salesforce token refresh failed: {str(e)}",
            )

    async def _refresh_zoho_token(self, tokens: OAuthTokens) -> RefreshResult:
        """Refresh Zoho OAuth token"""
        try:
            import httpx

            # Zoho OAuth 2.0 token refresh endpoint
            # The API domain is stored in service_account_id
            api_domain = tokens.service_account_id or "https://accounts.zoho.com"
            refresh_url = f"{api_domain}/oauth/v2/token"

            # Get client credentials from environment
            import os

            client_id = os.getenv("ZOHO_CLIENT_ID")
            client_secret = os.getenv("ZOHO_CLIENT_SECRET")

            if not client_id or not client_secret:
                return RefreshResult(
                    success=False, error_message="Zoho OAuth credentials not configured"
                )

            # Prepare refresh request
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": tokens.refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(refresh_url, data=refresh_data)
                response.raise_for_status()

                token_data = response.json()

                # Create new tokens
                new_tokens = OAuthTokens(
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", tokens.refresh_token),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_at=datetime.now()
                    + timedelta(seconds=token_data.get("expires_in", 3600)),
                    scope=token_data.get("scope", tokens.scope),
                    provider=OAuthProvider.ZOHO,
                    user_id=tokens.user_id,
                    service_account_id=token_data.get(
                        "api_domain", tokens.service_account_id
                    ),
                )

                return RefreshResult(
                    success=True,
                    new_tokens=new_tokens,
                    expires_at=new_tokens.expires_at,
                )

        except Exception as e:
            logger.error(f"❌ Zoho token refresh failed: {e}")
            return RefreshResult(
                success=False, error_message=f"Zoho token refresh failed: {str(e)}"
            )

    async def _get_current_tokens(
        self, user_id: str, service_name: str
    ) -> Optional[OAuthTokens]:
        """Get current OAuth tokens from Supabase"""
        try:
            from app.supabase.supabase_client import get_supabase_admin_client

            supabase = get_supabase_admin_client()

            # Query user_accounts table (NOT oauth_integrations)
            response = (
                supabase.table("user_accounts")
                .select("*")
                .eq("user_id", user_id)
                .eq("service", service_name)
                .eq("connected", True)
                .execute()
            )

            if not response.data:
                logger.debug(
                    f"⚪ No OAuth tokens found for user {user_id}, service {service_name}"
                )
                return None

            data = response.data[0]  # Get first record instead of using .single()
            account_data_raw = data.get("account_data", {})

            # Decrypt account_data if it's encrypted
            if isinstance(account_data_raw, str):
                from app.core.security import safe_decrypt

                account_data = safe_decrypt(account_data_raw)
                logger.debug(
                    f"✅ Decrypted account_data for token refresh: {service_name} - user {user_id}"
                )
            elif isinstance(account_data_raw, dict):
                account_data = account_data_raw
                logger.debug(
                    f"✅ Account_data already decrypted for token refresh: {service_name} - user {user_id}"
                )
            else:
                logger.error(
                    f"❌ Invalid account_data type for token refresh: {service_name}: {type(account_data_raw)}"
                )
                return None

            # Check if decryption was successful
            if not account_data:
                logger.warning(
                    f"⚠️ Failed to decrypt account_data for token refresh: {service_name} - user {user_id}"
                )
                return None

            if not account_data or not account_data.get("access_token"):
                logger.debug(
                    f"⚪ No access token found in account_data for {service_name}"
                )
                return None

            # Map service name to provider
            provider_mapping = {
                "google_calendar": OAuthProvider.GOOGLE,
                "google": OAuthProvider.GOOGLE,
                "twitter": OAuthProvider.TWITTER,
                "sendgrid": OAuthProvider.SENDGRID,
                "calendly_v2": OAuthProvider.CALENDLY,
                "calendly": OAuthProvider.CALENDLY,
                "pipedrive": OAuthProvider.PIPEDRIVE,
                "salesforce_rest_api": OAuthProvider.SALESFORCE,
                "salesforce": OAuthProvider.SALESFORCE,
                "zoho_crm": OAuthProvider.ZOHO,
            }

            provider = provider_mapping.get(service_name)
            if not provider:
                logger.warning(
                    f"⚠️ Unknown OAuth provider for token refresh: {service_name}"
                )
                return None

            # Parse expires_at
            expires_at = None
            if account_data.get("expires_at"):
                try:
                    expires_at = datetime.fromisoformat(
                        account_data["expires_at"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"⚠️ Invalid expires_at format for token refresh: {service_name}: {e}"
                    )

            return OAuthTokens(
                access_token=account_data["access_token"],
                refresh_token=account_data.get("refresh_token"),
                token_type=account_data.get("token_type", "Bearer"),
                expires_at=expires_at,
                scope=account_data.get("scope"),
                provider=provider,
                user_id=user_id,
                service_account_id=account_data.get("metadata", {}).get(
                    "service_account_id"
                ),
            )

        except Exception as e:
            logger.error(f"❌ Error getting current tokens: {e}")
            return None

    async def _update_tokens_in_supabase(
        self, user_id: str, service_name: str, new_tokens: OAuthTokens
    ) -> None:
        """Update tokens in Supabase"""
        try:
            from app.supabase.supabase_client import get_supabase_client

            supabase = get_supabase_client()

            # Prepare new account_data with updated tokens
            account_data = {
                "access_token": new_tokens.access_token,
                "refresh_token": new_tokens.refresh_token,
                "token_type": new_tokens.token_type,
                "expires_at": new_tokens.expires_at.isoformat()
                if new_tokens.expires_at
                else None,
                "scope": new_tokens.scope,
                "metadata": {
                    "service_account_id": new_tokens.service_account_id,
                    "updated_at": datetime.now().isoformat(),
                },
            }

            # Update user_accounts table (NOT oauth_integrations)
            supabase.table("user_accounts").update(
                {
                    "account_data": account_data,
                    "updated_at": datetime.now().isoformat(),
                }
            ).eq("user_id", user_id).eq("service", service_name).execute()

            logger.info(f"✅ Updated tokens in Supabase for {service_name}")

        except Exception as e:
            logger.error(f"❌ Error updating tokens in Supabase: {e}")
            raise

    def _get_cached_refresh_result(self, cache_key: str) -> Optional[RefreshResult]:
        """Get cached refresh result if still valid"""
        if cache_key in self._refresh_cache:
            result, timestamp = self._refresh_cache[cache_key]

            # Cache is valid for 5 minutes
            if datetime.now() - timestamp < timedelta(minutes=5):
                return result
            else:
                # Remove expired cache entry
                del self._refresh_cache[cache_key]

        return None

    def _cache_refresh_result(self, cache_key: str, result: RefreshResult) -> None:
        """Cache refresh result with timestamp"""
        self._refresh_cache[cache_key] = (result, datetime.now())

    def clear_refresh_cache(self) -> None:
        """Clear the refresh cache"""
        self._refresh_cache.clear()
        logger.info("🧹 Cleared OAuth refresh cache")

    async def refresh_all_expiring_tokens(
        self, user_id: str, minutes_before_expiry: int = 10
    ) -> Dict[str, RefreshResult]:
        """
        Refresh all tokens that are expiring soon for a user.

        Args:
            user_id: User identifier
            minutes_before_expiry: Refresh tokens expiring within this many minutes

        Returns:
            Dictionary mapping service names to refresh results
        """
        try:
            from app.supabase.supabase_client import get_supabase_admin_client

            supabase = get_supabase_admin_client()

            # Get all integrations for the user from user_accounts table
            response = (
                supabase.table("user_accounts")
                .select("service, account_data")
                .eq("user_id", user_id)
                .eq("connected", True)
                .execute()
            )

            if not response.data:
                return {}

            results = {}
            cutoff_time = datetime.now() + timedelta(minutes=minutes_before_expiry)

            for integration in response.data:
                service_name = integration["service"]
                account_data_raw = integration.get("account_data", {})

                # Decrypt account_data if it's encrypted
                if isinstance(account_data_raw, str):
                    from app.core.security import safe_decrypt

                    account_data = safe_decrypt(account_data_raw)
                elif isinstance(account_data_raw, dict):
                    account_data = account_data_raw
                else:
                    continue

                expires_at_str = (
                    account_data.get("expires_at") if account_data else None
                )

                if expires_at_str:
                    try:
                        expires_at = datetime.fromisoformat(
                            expires_at_str.replace("Z", "+00:00")
                        )

                        if expires_at <= cutoff_time:
                            logger.info(
                                f"🔄 Refreshing expiring token for {service_name}"
                            )
                            result = await self.refresh_mcp_token(user_id, service_name)
                            results[service_name] = result
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"⚠️ Invalid expires_at format for {service_name}: {e}"
                        )
                        continue

            return results

        except Exception as e:
            logger.error(f"❌ Error refreshing expiring tokens: {e}")
            return {}


# Global refresh manager instance
_token_refresh_manager = OAuthTokenRefreshManager()


def get_token_refresh_manager() -> OAuthTokenRefreshManager:
    """
    Get the global token refresh manager instance.

    Returns:
        OAuthTokenRefreshManager instance
    """
    return _token_refresh_manager


async def refresh_mcp_token(user_id: str, service_name: str) -> RefreshResult:
    """
    Convenience function to refresh OAuth token for a service.

    Args:
        user_id: User identifier
        service_name: Name of the service

    Returns:
        RefreshResult with success status and new tokens
    """
    manager = get_token_refresh_manager()
    return await manager.refresh_mcp_token(user_id, service_name)


async def refresh_all_expiring_tokens(user_id: str) -> Dict[str, RefreshResult]:
    """
    Convenience function to refresh all expiring tokens for a user.

    Args:
        user_id: User identifier

    Returns:
        Dictionary mapping service names to refresh results
    """
    manager = get_token_refresh_manager()
    return await manager.refresh_all_expiring_tokens(user_id)
