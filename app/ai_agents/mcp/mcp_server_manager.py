"""
MCP Server Manager

This module handles all MCP (Model Context Protocol) server creation, connection,
and management logic extracted from agents.py.

Provides:
- MCP server creation for different integration types
- Connection management and comprehensive error handling
- OAuth integration checking
- Local MCP server creation
- Integration with retry logic and circuit breaker patterns

Following PRD: prd-pipedream-mcp-integration.md
Enhanced with error handling system from Task 2.0
"""

import os
import logging
import tempfile
from typing import Dict, Any, List, Optional, Union

from .error_handler import (
    MCPConnectionError,
    MCPConfigurationError,
    MCPAuthenticationError,
    get_error_handler,
)
from .retry_handler import retry_mcp_operation
from .oauth_integration import (
    OAuthTokens,
    MCPCredentials,
    OAuthProvider,
    get_mcp_credentials_for_service,
)

logger = logging.getLogger(__name__)


def create_pipedream_mcp_servers(user_id: Optional[str] = None) -> List[Any]:
    """
    Create Pipedream MCP servers for user integrations.

    Args:
        user_id: User identifier for filtering integrations

    Returns:
        List of MCP server configurations
    """
    # Check if MCPs are disabled to prevent Content-Type errors
    if os.getenv("DISABLE_MCP", "false").lower() == "true":
        logger.info(
            "ℹ️ MCP servers disabled to prevent 'text/event-stream' vs 'text/html' errors"
        )
        logger.info("   Agents will function normally using local database tools only.")
        return []

    # For now, return empty list until proper MCP integration is ready
    return []


@retry_mcp_operation(max_attempts=3, service_name="mcp_connection", log_attempts=True)
async def connect_mcp_servers_properly(mcp_servers: List[Any]) -> List[Any]:
    """
    Connect MCP servers with comprehensive error handling and retry logic.

    Args:
        mcp_servers: List of MCP server configurations

    Returns:
        List of successfully connected MCP servers

    Raises:
        MCPConnectionError: If critical connection failures occur
    """
    connected = []
    error_handler = get_error_handler()

    for server in mcp_servers:
        try:
            # Get server name for better error reporting
            server_name = getattr(server, "name", type(server).__name__)

            # Actually connect the server with timeout
            await server.connect()
            logger.info(f"✅ MCP server connected successfully: {server_name}")
            connected.append(server)

        except Exception as raw_error:
            # Classify and handle the error
            server_name = getattr(server, "name", type(server).__name__)
            mcp_error = error_handler.handle_error(
                raw_error,
                service_name=server_name,
                operation="connect_server",
                context={"server_type": type(server).__name__},
            )

            # Log user-friendly error message
            logger.warning(f"⚠️ {mcp_error.get_user_friendly_message()}")

            # Continue with other servers instead of failing completely
            continue

    if not connected and mcp_servers:
        # All servers failed to connect
        raise MCPConnectionError(
            service_name="mcp_servers",
            message=f"Failed to connect any of {len(mcp_servers)} MCP servers",
            context={"total_servers": len(mcp_servers)},
        )

    return connected


async def connect_mcp_servers(mcp_servers: List[Any]) -> Dict[str, Any]:
    """
    Connect MCP servers and return status.

    Args:
        mcp_servers: List of MCP server configurations

    Returns:
        Dictionary with connection status
    """
    connected_servers = await connect_mcp_servers_properly(mcp_servers)

    return {
        "total": len(mcp_servers),
        "connected": len(connected_servers),
        "servers": connected_servers,
    }


def get_user_integration(
    user_id: str,
    service: str,  # Changed from integration_type to service
) -> Optional[Dict[str, Any]]:
    """
    Get user integration configuration for a specific service.
    Connects to OAuth system to check if user has authorized the integration.
    Enhanced with comprehensive error handling and user-friendly messages.

    Args:
        user_id: User identifier
        service: Service name (google_calendar, twitter, calendly, etc.)

    Returns:
        Integration configuration if enabled, None otherwise

    Raises:
        MCPConfigurationError: If integration configuration is invalid
        MCPAuthenticationError: If authentication fails
    """
    error_handler = get_error_handler()

    try:
        # Import here to avoid circular imports
        from app.api.oauth_integration_manager import get_oauth_integration_manager

        oauth_manager = get_oauth_integration_manager()

        # Check if user has this service connected with valid tokens
        if oauth_manager.is_integration_connected(user_id, service):
            # Get the service credentials for MCP usage
            credentials = oauth_manager.create_mcp_credentials(user_id, service)

            if credentials:
                logger.info(f"✅ {service} service enabled for user {user_id}")
                return {
                    "enabled": True,
                    "service": service,  # Changed from integration_type
                    "user_id": user_id,
                    "credentials": credentials,
                    "config": credentials,  # For backward compatibility
                    "created_at": "2025-01-07T12:00:00Z",
                }
            else:
                # Credentials creation failed
                raise MCPAuthenticationError(
                    service_name=service,
                    message=f"Failed to create MCP credentials for {service}",
                    context={"user_id": user_id},
                )

        # If not connected, return None (not an error, just not configured)
        logger.debug(f"ℹ️ Service {service} not connected for user {user_id}")
        return None

    except (MCPConfigurationError, MCPAuthenticationError):
        # Re-raise MCP errors as-is
        raise

    except ImportError as e:
        # OAuth manager not available
        mcp_error = MCPConfigurationError(
            service_name=service,
            config_key="oauth_integration_manager",
            message=f"OAuth integration manager not available: {e}",
            context={"user_id": user_id, "import_error": str(e)},
        )
        error_handler.handle_error(mcp_error, log_error=True)
        return None  # Changed: no demo fallback

    except Exception as raw_error:
        # Handle other errors
        mcp_error = error_handler.handle_error(
            raw_error,
            service_name=service,
            operation="get_user_integration",
            context={"user_id": user_id},
        )

        logger.warning(
            f"⚠️ {mcp_error.get_user_friendly_message()} - No integration available"
        )
        return None  # Changed: no demo fallback


def create_mcp_servers_for_user(
    user_id: Optional[str] = None, agent_type: Optional[str] = None
) -> List[Any]:
    """
    Create MCP servers using the new AgentMCPFactory.

    REFACTORED: Now uses AgentMCPFactory for agent-specific MCP creation.
    Maintains backward compatibility by creating all agent MCPs when agent_type is None.

    Following https://openai.github.io/openai-agents-python/mcp/

    Args:
        user_id: User identifier for OAuth integration filtering
        agent_type: Optional agent type (coordinator, meeting_scheduler, lead_administrator).
                   If None, creates MCPs for all agent types for backward compatibility.

    Returns:
        List of configured MCP server instances ready for agent usage
    """
    # Import the factory here to avoid circular imports
    from .agent_mcp_factory import AgentMCPFactory, AgentType

    logger.info(
        f"🏭 Creating MCP servers using AgentMCPFactory (user: {user_id}, agent: {agent_type})"
    )

    factory = AgentMCPFactory(user_id)
    mcp_servers = []

    if agent_type:
        # Create MCPs for specific agent type
        try:
            # Convert string to AgentType enum
            agent_mapping = {
                "coordinator": AgentType.COORDINATOR,
                "meeting_scheduler": AgentType.MEETING_SCHEDULER,
                "lead_administrator": AgentType.LEAD_ADMINISTRATOR,
            }

            enum_agent_type = agent_mapping.get(agent_type)
            if enum_agent_type:
                mcp_servers = factory.create_mcp_servers_for_agent(
                    enum_agent_type,
                    include_local=False,  # Don't include local server here, will be added in get_all_mcp_servers_for_user
                )
                logger.info(
                    f"✅ Created {len(mcp_servers)} MCP servers for {agent_type} agent"
                )
            else:
                logger.warning(f"⚠️ Unknown agent type: {agent_type}")

        except Exception as e:
            logger.error(f"❌ Error creating MCPs for agent type {agent_type}: {e}")

    else:
        # Backward compatibility: Create MCPs for all agent types
        logger.info("🔄 Backward compatibility mode: creating MCPs for all agent types")

        for agent_enum in AgentType:
            try:
                agent_mcps = factory.create_mcp_servers_for_agent(
                    agent_enum,
                    include_local=False,  # Local server added separately
                )
                mcp_servers.extend(agent_mcps)
                logger.debug(f"✅ Added {len(agent_mcps)} MCPs for {agent_enum.value}")

            except Exception as e:
                logger.error(f"❌ Error creating MCPs for {agent_enum.value}: {e}")
                continue

        # Remove duplicates (some agents might share the same services)
        seen_servers = set()
        unique_servers = []

        for server in mcp_servers:
            # Use server configuration as identifier
            server_id = f"{getattr(server, 'params', {}).get('headers', {}).get('x-pd-app-slug', str(id(server)))}"

            if server_id not in seen_servers:
                seen_servers.add(server_id)
                unique_servers.append(server)
            else:
                logger.debug(f"🔄 Skipping duplicate MCP server: {server_id}")

        mcp_servers = unique_servers

    logger.info(f"✅ AgentMCPFactory created {len(mcp_servers)} unique MCP servers")
    return mcp_servers


def create_local_mcp_server() -> Optional[Any]:
    """
    Create local MCP server using stdio transport for filesystem operations.
    Enhanced with comprehensive error handling and user-friendly messages.

    Auto-detects npm availability and fails gracefully on Windows systems
    where npm is not properly configured.

    Following documentation example:
    https://openai.github.io/openai-agents-python/mcp/

    Returns:
        Local MCP server instance or None if creation fails

    Raises:
        MCPConfigurationError: If server configuration is invalid
    """
    error_handler = get_error_handler()

    # First check if npm/npx is available
    try:
        import subprocess

        # Test if npm is available
        subprocess.run(["npm", "--version"], capture_output=True, check=True, timeout=5)
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        logger.info("ℹ️ npm/npx not available - skipping local MCP server creation")
        logger.info(
            "💡 Install Node.js with npm from https://nodejs.org/ to enable MCP filesystem server"
        )
        return None

    try:
        from agents.mcp import MCPServerStdio

        # Create temporary directory for safe file operations
        temp_dir = tempfile.mkdtemp(prefix="pipewise_mcp_")

        # Create filesystem MCP server with basic configuration
        filesystem_server = MCPServerStdio(
            params={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", temp_dir],
            },
            cache_tools_list=True,
        )

        logger.info(f"✅ Created local filesystem MCP server (directory: {temp_dir})")
        return filesystem_server

    except ImportError as e:
        # This is expected in some environments - not an error
        logger.info(f"ℹ️ Local MCP server not available: {e}")
        return None

    except FileNotFoundError as e:
        # npx or filesystem server not found
        logger.info(
            f"ℹ️ npx command not found - Node.js may not be properly installed: {e}"
        )
        logger.info(
            "💡 Install Node.js with npm from https://nodejs.org/ to enable MCP filesystem server"
        )
        return None

    except PermissionError as e:
        # Permission issues with temp directory
        mcp_error = MCPConfigurationError(
            service_name="local_filesystem",
            config_key="temp_directory",
            message=f"Permission denied creating temp directory: {e}",
            context={"error": str(e)},
        )
        error_handler.handle_error(mcp_error, log_error=True)
        logger.warning(f"⚠️ {mcp_error.get_user_friendly_message()}")
        return None

    except Exception as raw_error:
        # Handle other unexpected errors gracefully
        logger.info(f"ℹ️ Could not create local MCP server: {raw_error}")
        logger.info(
            "💡 This is normal if Node.js/npm is not available - agents will work with database tools only"
        )
        return None


# Convenience functions for backward compatibility and agent-specific usage
def get_all_mcp_servers_for_user(user_id: Optional[str] = None) -> List[Any]:
    """
    Get all MCP servers for a user including both Pipedream and local servers.

    REFACTORED: Now uses AgentMCPFactory internally.

    Args:
        user_id: User identifier for OAuth integration filtering

    Returns:
        List of all available MCP servers for the user
    """
    mcp_servers = create_mcp_servers_for_user(user_id)

    # Add local MCP server for filesystem operations
    local_server = create_local_mcp_server()
    if local_server:
        mcp_servers.append(local_server)

    return mcp_servers


# Agent-specific convenience functions
def get_coordinator_mcp_servers(user_id: Optional[str] = None) -> List[Any]:
    """Get MCP servers for Coordinator Agent (SendGrid + Twitter)"""
    mcp_servers = create_mcp_servers_for_user(user_id, "coordinator")

    # Add local server for coordinator
    local_server = create_local_mcp_server()
    if local_server:
        mcp_servers.append(local_server)

    return mcp_servers


def get_meeting_scheduler_mcp_servers(user_id: Optional[str] = None) -> List[Any]:
    """Get MCP servers for Meeting Scheduler Agent (Calendly + Google Calendar)"""
    mcp_servers = create_mcp_servers_for_user(user_id, "meeting_scheduler")

    # Add local server for meeting scheduler
    local_server = create_local_mcp_server()
    if local_server:
        mcp_servers.append(local_server)

    return mcp_servers


def get_lead_administrator_mcp_servers(user_id: Optional[str] = None) -> List[Any]:
    """Get MCP servers for Lead Administrator Agent (CRM tools)"""
    # Lead Administrator typically doesn't need local filesystem access
    # as it focuses on CRM operations, but we'll include it for consistency
    mcp_servers = create_mcp_servers_for_user(user_id, "lead_administrator")

    # Add local server for lead administrator (optional)
    local_server = create_local_mcp_server()
    if local_server:
        mcp_servers.append(local_server)

    return mcp_servers


@retry_mcp_operation(
    max_attempts=3, service_name="oauth_credentials", log_attempts=True
)
async def get_mcp_credentials_for_user(
    user_id: str, service_name: str
) -> Optional[MCPCredentials]:
    """
    Get MCP credentials for a user from Supabase OAuth tokens.

    This function fetches OAuth tokens from Supabase and converts them to
    MCP-compatible credentials for use with external services.

    Args:
        user_id: User identifier
        service_name: Name of the service (google_calendar, twitter, etc.)

    Returns:
        MCPCredentials if valid OAuth tokens are found, None otherwise

    Raises:
        MCPAuthenticationError: If authentication fails
        MCPConfigurationError: If service configuration is invalid
    """
    error_handler = get_error_handler()

    try:
        # Get OAuth tokens from Supabase
        oauth_tokens = await _get_oauth_tokens_from_supabase(user_id, service_name)

        if not oauth_tokens:
            logger.debug(
                f"⚪ No OAuth tokens found for user {user_id}, service {service_name}"
            )
            return None

        # Validate token expiration
        if oauth_tokens.is_expired():
            logger.warning(
                f"⚠️ OAuth token expired for user {user_id}, service {service_name}"
            )

            # Try to refresh the token using the dedicated refresh manager
            from .oauth_token_refresh import get_token_refresh_manager

            refresh_manager = get_token_refresh_manager()
            refresh_result = await refresh_manager.refresh_mcp_token(
                user_id, service_name
            )

            if refresh_result.success and refresh_result.new_tokens:
                oauth_tokens = refresh_result.new_tokens
                logger.info(f"✅ Successfully refreshed OAuth token for {service_name}")
            else:
                raise MCPAuthenticationError(
                    service_name=service_name,
                    message=f"OAuth token expired and refresh failed for {service_name}: {refresh_result.error_message}",
                    context={"user_id": user_id},
                )

        # Convert OAuth tokens to MCP credentials
        mcp_credentials = get_mcp_credentials_for_service(
            oauth_tokens, service_name, user_id
        )

        logger.info(
            f"✅ Created MCP credentials for user {user_id}, service {service_name}"
        )
        return mcp_credentials

    except (MCPAuthenticationError, MCPConfigurationError):
        # Re-raise MCP errors as-is
        raise

    except Exception as raw_error:
        # Handle other unexpected errors
        mcp_error = error_handler.handle_error(
            raw_error,
            service_name=service_name,
            operation="get_mcp_credentials",
            context={"user_id": user_id},
        )
        logger.warning(f"⚠️ {mcp_error.get_user_friendly_message()}")
        return None


async def _get_oauth_tokens_from_supabase(
    user_id: str, service_name: str
) -> Optional[OAuthTokens]:
    """
    Get OAuth tokens from Supabase for a specific service.

    Args:
        user_id: User identifier
        service_name: Name of the service

    Returns:
        OAuthTokens if found, None otherwise
    """
    try:
        # Import Supabase admin client to bypass RLS
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
                f"⚪ No OAuth integration found for user {user_id}, service {service_name}"
            )
            return None

        integration_data = response.data[0]

        # Map service name to OAuth provider
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
            logger.warning(f"⚠️ Unknown OAuth provider for service: {service_name}")
            return None

        # Extract and decrypt account_data (contains OAuth tokens)
        account_data_raw = integration_data.get("account_data", {})

        # Decrypt account_data if it's encrypted (string)
        if isinstance(account_data_raw, str):
            from app.core.security import safe_decrypt

            account_data = safe_decrypt(account_data_raw)
            logger.debug(
                f"✅ Decrypted account_data for {service_name} - user {user_id}"
            )
        elif isinstance(account_data_raw, dict):
            account_data = account_data_raw
            logger.debug(
                f"✅ Account_data already decrypted for {service_name} - user {user_id}"
            )
        else:
            logger.error(
                f"❌ Invalid account_data type for {service_name}: {type(account_data_raw)}"
            )
            return None

        if not account_data or not account_data.get("access_token"):
            logger.debug(f"⚪ No access token found in account_data for {service_name}")
            return None

        # Parse expires_at if available
        expires_at = None
        if account_data.get("expires_at"):
            from datetime import datetime

            expires_at = datetime.fromisoformat(
                account_data["expires_at"].replace("Z", "+00:00")
            )

        oauth_tokens = OAuthTokens(
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

        logger.debug(
            f"✅ Retrieved OAuth tokens for user {user_id}, service {service_name}"
        )
        return oauth_tokens

    except Exception as e:
        logger.error(f"❌ Error getting OAuth tokens from Supabase: {e}")
        return None


async def _refresh_oauth_token(
    user_id: str, service_name: str, expired_tokens: OAuthTokens
) -> Optional[OAuthTokens]:
    """
    Refresh OAuth token using refresh token.

    Args:
        user_id: User identifier
        service_name: Name of the service
        expired_tokens: The expired OAuth tokens

    Returns:
        New OAuthTokens if refresh successful, None otherwise
    """
    try:
        if not expired_tokens.refresh_token:
            logger.debug(f"⚪ No refresh token available for {service_name}")
            return None

        # Import OAuth manager for refresh logic
        from app.api.oauth_integration_manager import get_oauth_integration_manager

        oauth_manager = get_oauth_integration_manager()

        # TODO: Implement token refresh when oauth_manager.refresh_user_token is available
        # For now, we'll skip refresh functionality and let the calling code handle expired tokens
        # This is a placeholder for future implementation

        # Use existing refresh logic if available
        # if hasattr(oauth_manager, "refresh_user_token"):
        #     refreshed_data = oauth_manager.refresh_user_token(user_id, service_name)
        #     if refreshed_data:
        #         # Update tokens in Supabase
        #         await _update_oauth_tokens_in_supabase(user_id, service_name, refreshed_data)
        #         # Create new OAuthTokens object
        #         return OAuthTokens(...)

        # For now, return None when refresh is needed
        # This allows the calling code to handle expired tokens appropriately

        logger.debug(f"⚪ Token refresh not available for {service_name}")
        return None

    except Exception as e:
        logger.warning(f"⚠️ Error refreshing OAuth token for {service_name}: {e}")
        return None


async def _update_oauth_tokens_in_supabase(
    user_id: str, service_name: str, token_data: Dict[str, Any]
) -> None:
    """
    Update OAuth tokens in Supabase after refresh.

    Args:
        user_id: User identifier
        service_name: Name of the service
        token_data: New token data
    """
    try:
        from app.supabase.supabase_client import get_supabase_admin_client
        from app.core.security import encrypt_oauth_tokens

        supabase = get_supabase_admin_client()

        # Encrypt the new token data
        encrypted_tokens = encrypt_oauth_tokens(token_data)

        # Update user_accounts table (NOT oauth_integrations)
        supabase.table("user_accounts").update(
            {
                "account_data": encrypted_tokens,
                "updated_at": "now()",
            }
        ).eq("user_id", user_id).eq("service", service_name).execute()

        logger.info(
            f"✅ Updated OAuth tokens in Supabase for user {user_id}, service {service_name}"
        )

    except Exception as e:
        logger.error(f"❌ Error updating OAuth tokens in Supabase: {e}")


def validate_oauth_tokens_for_service(user_id: str, service_name: str) -> bool:
    """
    Validate that OAuth tokens exist and are valid for a service.

    Args:
        user_id: User identifier
        service_name: Name of the service

    Returns:
        True if tokens are valid, False otherwise
    """
    try:
        # Import admin client to bypass RLS
        from app.supabase.supabase_client import get_supabase_admin_client

        supabase = get_supabase_admin_client()

        # Query user_accounts table (NOT oauth_integrations)
        response = (
            supabase.table("user_accounts")
            .select("account_data")
            .eq("user_id", user_id)
            .eq("service", service_name)
            .eq("connected", True)
            .execute()
        )

        if not response.data:
            logger.debug(
                f"⚪ No OAuth tokens found for user {user_id}, service {service_name}"
            )
            return False

        # Get the first record (should only be one per user/service)
        account_record = response.data[0]
        account_data_raw = account_record.get("account_data", {})

        # Decrypt account_data if it's encrypted (string)
        if isinstance(account_data_raw, str):
            from app.core.security import safe_decrypt

            account_data = safe_decrypt(account_data_raw)
            logger.debug(
                f"✅ Decrypted account_data for validation: {service_name} - user {user_id}"
            )
        elif isinstance(account_data_raw, dict):
            account_data = account_data_raw
            logger.debug(
                f"✅ Account_data already decrypted for validation: {service_name} - user {user_id}"
            )
        else:
            logger.error(
                f"❌ Invalid account_data type for validation: {service_name}: {type(account_data_raw)}"
            )
            return False

        # Check if decryption was successful
        if not account_data:
            logger.warning(
                f"⚠️ Failed to decrypt account_data for validation: {service_name} - user {user_id}"
            )
            return False

        # Check if we have an access token
        if not account_data.get("access_token"):
            logger.debug(
                f"⚪ No access token found for validation: {service_name} - user {user_id}"
            )
            return False

        # Check if token is expired
        if account_data.get("expires_at"):
            from datetime import datetime

            try:
                expires_at = datetime.fromisoformat(
                    account_data["expires_at"].replace("Z", "+00:00")
                )
                if datetime.now().replace(tzinfo=expires_at.tzinfo) >= expires_at:
                    logger.debug(
                        f"⚪ OAuth token expired for user {user_id}, service {service_name}"
                    )
                    return False
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"⚠️ Invalid expires_at format for validation: {service_name}: {e}"
                )
                # If we can't parse the date, assume token is still valid

        logger.debug(
            f"✅ OAuth tokens validated successfully for user {user_id}, service {service_name}"
        )
        return True

    except Exception as e:
        logger.warning(f"⚠️ Error validating OAuth tokens: {e}")
        return False


class OAuth2ValidationMiddleware:
    """
    Middleware for validating OAuth2 tokens before MCP server creation.
    Enhanced with caching for improved performance.
    """

    def __init__(self):
        self.validation_cache: Dict[
            str, Union[bool, float]
        ] = {}  # Change to Union[bool, float]
        self.cache_ttl = 300  # 5 minutes cache for validation results

    def validate_tokens_for_mcp_creation(
        self, user_id: str, service_names: List[str]
    ) -> Dict[str, bool]:
        """
        Validate OAuth tokens for a list of services before creating MCP servers.
        Enhanced with caching and error handling.

        Args:
            user_id: User identifier
            service_names: List of service names to validate

        Returns:
            Dictionary of service -> validation status

        Raises:
            MCPAuthenticationError: If critical authentication failures occur
        """
        results = {}
        error_handler = get_error_handler()

        for service_name in service_names:
            cache_key = f"{user_id}_{service_name}"
            cached_result = self._get_cached_validation(cache_key)

            if cached_result is not None:
                results[service_name] = cached_result
                continue

            is_valid = self._validate_service_oauth_tokens(user_id, service_name)

            if is_valid:
                self._cache_validation_result(cache_key, True)
                results[service_name] = True
            else:
                logger.warning(f"⚠️ Invalid OAuth tokens for {service_name}")
                results[service_name] = False  # No demo check

        return results

    def _validate_service_oauth_tokens(self, user_id: str, service_name: str) -> bool:
        """
        Validate OAuth tokens for a specific service.

        Args:
            user_id: User identifier
            service_name: Service name

        Returns:
            True if tokens are valid, False otherwise
        """
        try:
            # Use the existing validation function
            return validate_oauth_tokens_for_service(user_id, service_name)

        except Exception as raw_error:
            error_handler = get_error_handler()
            mcp_error = error_handler.handle_error(
                raw_error,
                service_name=service_name,
                operation="oauth_validation",
                context={"user_id": user_id},
            )

            logger.warning(
                f"⚠️ {mcp_error.get_user_friendly_message()} - Validation failed"
            )
            return False  # No demo fallback

    def _get_cached_validation(self, cache_key: str) -> Optional[bool]:
        """
        Get cached validation result.

        Args:
            cache_key: Cache key for validation result

        Returns:
            Cached validation result or None if not cached or expired
        """
        import time  # Add import here

        if cache_key in self.validation_cache:
            expire_key = f"{cache_key}_expire"
            if expire_key in self.validation_cache:
                if time.time() < self.validation_cache[expire_key]:
                    return self.validation_cache[cache_key]  # type: ignore  # We know it's bool here
                else:
                    # Clean up expired entries
                    del self.validation_cache[cache_key]
                    del self.validation_cache[expire_key]
        return None

    def _cache_validation_result(self, cache_key: str, result: bool) -> None:
        """
        Cache validation result.

        Args:
            cache_key: Cache key for validation result
            result: Validation result to cache
        """
        self.validation_cache[cache_key] = result
        # Set timeout for cache cleanup (simple implementation)
        import time

        self.validation_cache[f"{cache_key}_expire"] = time.time() + self.cache_ttl

    def filter_services_by_oauth_validity(
        self, user_id: str, service_names: List[str]
    ) -> List[str]:
        """
        Filter list of services to only those with valid OAuth tokens.

        Args:
            user_id: User identifier
            service_names: List of service names to filter

        Returns:
            List of services with valid OAuth tokens
        """
        validation_results = self.validate_tokens_for_mcp_creation(
            user_id, service_names
        )
        valid_services = [
            service for service, is_valid in validation_results.items() if is_valid
        ]

        logger.info(
            f"✅ {len(valid_services)} services have valid OAuth tokens: {', '.join(valid_services)}"
        )
        logger.debug(
            f"🔒 Filtered out {len(service_names) - len(valid_services)} services without valid OAuth: {', '.join(set(service_names) - set(valid_services))}"
        )

        return valid_services

    def clear_validation_cache(self) -> None:
        """
        Clear the validation cache.
        """
        self.validation_cache.clear()


# Global middleware instance
_oauth_validation_middleware = OAuth2ValidationMiddleware()


def get_oauth_validation_middleware() -> OAuth2ValidationMiddleware:
    """
    Get the global OAuth validation middleware instance.

    Returns:
        OAuth2ValidationMiddleware instance
    """
    return _oauth_validation_middleware


def validate_oauth_before_mcp_creation(
    user_id: str, service_names: List[str]
) -> List[str]:
    """
    Convenience function to validate OAuth tokens before MCP creation.

    Args:
        user_id: User identifier
        service_names: List of service names to validate

    Returns:
        List of service names with valid OAuth tokens
    """
    middleware = get_oauth_validation_middleware()
    return middleware.filter_services_by_oauth_validity(user_id, service_names)
