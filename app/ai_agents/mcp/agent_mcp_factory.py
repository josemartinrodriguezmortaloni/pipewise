"""
Agent MCP Factory

Factory pattern implementation for creating agent-specific MCP servers.
Each agent type gets specific MCP servers based on their role:

- Coordinator Agent: SendGrid (email) + Twitter (social media)
- Meeting Scheduler Agent: Calendly + Google Calendar
- Lead Administrator Agent: Pipedrive + Salesforce + Zoho CRM

Enhanced with comprehensive error handling, retry logic, and user-friendly messages.

Following PRD: prd-pipedream-mcp-integration.md
Enhanced with error handling system from Task 2.0
"""

import os
import logging
from typing import Dict, Any, List, Optional, Set
from enum import Enum

from .error_handler import (
    MCPConnectionError,
    MCPConfigurationError,
    MCPAuthenticationError,
    get_error_handler,
    create_user_friendly_error,
    MCPErrorCategory,
)
from .retry_handler import retry_mcp_operation
from .oauth_integration import (
    OAuthTokens,
    MCPCredentials,
    OAuthProvider,
    MCPServiceType,
    get_mcp_credentials_for_service,
    create_demo_oauth_tokens,
)
from .oauth_analytics_logger import (
    get_oauth_analytics_logger,
    OAuthEventType,
    OAuthEventStatus,
)

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Supported agent types with their specific MCP requirements"""

    COORDINATOR = "coordinator"
    MEETING_SCHEDULER = "meeting_scheduler"
    LEAD_ADMINISTRATOR = "lead_administrator"


class AgentMCPFactory:
    """
    Factory for creating agent-specific MCP servers.

    Each agent type receives only the MCP servers relevant to their function,
    improving performance and security by limiting access to necessary services only.
    """

    # Agent-specific MCP mapping based on PRD requirements
    AGENT_MCP_MAPPING = {
        AgentType.COORDINATOR: {
            "sendgrid",  # Email marketing/transactional
            "twitter",  # Social media outreach
        },
        AgentType.MEETING_SCHEDULER: {
            "calendly_v2",  # Scheduling links and events
            "google_calendar",  # Calendar management
        },
        AgentType.LEAD_ADMINISTRATOR: {
            "pipedrive",  # CRM operations
            "salesforce_rest_api",  # Enterprise CRM
            "zoho_crm",  # Alternative CRM
        },
    }

    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize the agent MCP factory.

        Args:
            user_id: User identifier for OAuth integration filtering
        """
        self.user_id = user_id
        self._mcp_cache = {}  # Cache for created MCP servers

    def create_mcp_servers_for_agent(
        self, agent_type: AgentType, include_local: bool = True
    ) -> List[Any]:
        """
        Create MCP servers specific to an agent type.

        Args:
            agent_type: Type of agent (coordinator, meeting_scheduler, lead_administrator)
            include_local: Whether to include local filesystem MCP server

        Returns:
            List of MCP servers configured for the specific agent type
        """
        cache_key = f"{agent_type.value}_{self.user_id}_{include_local}"

        # Return cached servers if available
        if cache_key in self._mcp_cache:
            logger.debug(f"🔄 Using cached MCP servers for {agent_type.value}")
            return self._mcp_cache[cache_key]

        logger.info(f"🏭 Creating MCP servers for {agent_type.value} agent")

        # Get required services for this agent type
        required_services = self.AGENT_MCP_MAPPING.get(agent_type, set())

        if not required_services:
            logger.warning(
                f"⚠️ No MCP services defined for agent type: {agent_type.value}"
            )
            return []

        # Create MCP servers for required services
        mcp_servers = self._create_pipedream_mcp_servers(required_services)

        # Add local MCP server if requested
        if include_local:
            local_server = self._create_local_mcp_server()
            if local_server:
                mcp_servers.append(local_server)

        # Cache the results
        self._mcp_cache[cache_key] = mcp_servers

        logger.info(
            f"✅ Created {len(mcp_servers)} MCP servers for {agent_type.value} agent"
        )

        return mcp_servers

    @retry_mcp_operation(
        max_attempts=2, service_name="pipedream_factory", log_attempts=True
    )
    def _create_pipedream_mcp_servers(self, required_services: Set[str]) -> List[Any]:
        """
        Create Pipedream MCP servers for specific services.
        Enhanced with comprehensive error handling and retry logic.

        Args:
            required_services: Set of service names to create MCP servers for

        Returns:
            List of configured Pipedream MCP servers

        Raises:
            MCPConfigurationError: If critical configuration is missing
            MCPConnectionError: If service creation fails completely
        """
        error_handler = get_error_handler()

        # Check if MCPs are disabled
        if os.getenv("DISABLE_MCP", "false").lower() == "true":
            logger.info("ℹ️ MCP servers disabled via DISABLE_MCP environment variable")
            return []

        # Try to import MCP components
        try:
            from agents.mcp import MCPServerSse
        except ImportError as e:
            mcp_error = MCPConfigurationError(
                service_name="pipedream_mcp",
                config_key="agents.mcp",
                message=f"MCP components not available: {e}",
                context={"import_error": str(e)},
            )
            error_handler.handle_error(mcp_error, log_error=True)
            logger.info(f"ℹ️ {mcp_error.get_user_friendly_message()}")
            return []

        # Get Pipedream credentials
        pipedream_client_secret = os.getenv("PIPEDREAM_CLIENT_SECRET")
        project_id = os.getenv("PIPEDREAM_PROJECT_ID", "proj_default")
        environment = os.getenv("PIPEDREAM_ENVIRONMENT", "development")

        if not pipedream_client_secret:
            mcp_error = MCPConfigurationError(
                service_name="pipedream_mcp",
                config_key="PIPEDREAM_CLIENT_SECRET",
                message="PIPEDREAM_CLIENT_SECRET environment variable not found",
                context={"project_id": project_id, "environment": environment},
            )
            error_handler.handle_error(mcp_error, log_error=True)
            logger.info(f"ℹ️ {mcp_error.get_user_friendly_message()}")
            return []

        # Base headers for Pipedream MCP connections
        base_headers = {
            "Authorization": f"Bearer {pipedream_client_secret}",
            "x-pd-project-id": project_id,
            "x-pd-environment": environment,
        }

        mcp_servers = []
        failed_services = []

        # Filter services by OAuth validity before creating MCP servers
        if self.user_id:
            from .mcp_server_manager import validate_oauth_before_mcp_creation

            valid_services = validate_oauth_before_mcp_creation(
                self.user_id, list(required_services)
            )

            # Filter required services to only include those with valid OAuth
            required_services = set(valid_services)

            if not required_services:
                logger.info(
                    f"ℹ️ No services with valid OAuth tokens for user {self.user_id}"
                )
                return []

        # Create MCP servers only for required services
        for service_name in required_services:
            try:
                # Check if user has this integration enabled
                if self.user_id and not self._is_service_enabled(service_name):
                    logger.debug(
                        f"⚪ Skipping {service_name} - not enabled for user {self.user_id}"
                    )
                    continue

                external_user_id = (
                    f"pipewise_{self.user_id or 'default'}_{service_name}"
                )

                # Create MCP server following official documentation pattern
                server = MCPServerSse(
                    params={
                        "url": "https://remote.mcp.pipedream.net",
                        "headers": {
                            **base_headers,
                            "x-pd-external-user-id": external_user_id,
                            "x-pd-app-slug": service_name,
                        },
                    },
                    cache_tools_list=True,
                )

                mcp_servers.append(server)
                logger.info(f"✅ Created {service_name} MCP server")

                # Log successful MCP creation
                if self.user_id:
                    analytics_logger = get_oauth_analytics_logger()
                    analytics_logger.log_mcp_creation(
                        user_id=self.user_id,
                        service_name=service_name,
                        oauth_provider=self._get_oauth_provider_for_service(
                            service_name
                        ),
                        success=True,
                        context={"external_user_id": external_user_id},
                    )

            except Exception as raw_error:
                # Handle individual service creation failures
                mcp_error = error_handler.handle_error(
                    raw_error,
                    service_name=service_name,
                    operation="create_mcp_server",
                    context={
                        "user_id": self.user_id,
                        "external_user_id": f"pipewise_{self.user_id or 'default'}_{service_name}",
                        "pipedream_project_id": project_id,
                    },
                )

                logger.warning(f"⚠️ {mcp_error.get_user_friendly_message()}")
                failed_services.append(service_name)

                # Log failed MCP creation
                if self.user_id:
                    analytics_logger = get_oauth_analytics_logger()
                    analytics_logger.log_mcp_creation(
                        user_id=self.user_id,
                        service_name=service_name,
                        oauth_provider=self._get_oauth_provider_for_service(
                            service_name
                        ),
                        success=False,
                        error_message=mcp_error.get_user_friendly_message(),
                        context={"error_type": type(mcp_error).__name__},
                    )

                continue

        # Log summary
        if failed_services:
            logger.warning(
                f"⚠️ Failed to create {len(failed_services)} MCP servers: {', '.join(failed_services)}"
            )

        logger.info(f"✅ Successfully created {len(mcp_servers)} MCP servers")
        return mcp_servers

    def _create_local_mcp_server(self) -> Optional[Any]:
        """
        Create local MCP server for filesystem operations.

        Returns:
            Local MCP server instance or None if creation fails
        """
        try:
            from agents.mcp import MCPServerStdio
            import tempfile

            # Create temporary directory for safe file operations
            temp_dir = tempfile.mkdtemp(prefix="pipewise_mcp_")

            # Create filesystem MCP server
            filesystem_server = MCPServerStdio(
                params={
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", temp_dir],
                },
                cache_tools_list=True,
            )

            logger.info(
                f"✅ Created local filesystem MCP server (directory: {temp_dir})"
            )
            return filesystem_server

        except ImportError as e:
            logger.info(f"ℹ️ Local MCP server not available: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to create local MCP server: {e}")
            return None

    def _is_service_enabled(self, service_name: str) -> bool:
        """
        Check if a service is enabled for the current user with OAuth credentials.

        Enhanced to check for valid OAuth tokens in addition to service enablement.

        Args:
            service_name: Name of the service to check

        Returns:
            True if service is enabled with valid OAuth credentials, False otherwise
        """
        try:
            # Skip OAuth check if no user_id provided
            if not self.user_id:
                logger.debug(f"ℹ️ No user_id provided for {service_name}")
                return False

            # Import here to avoid circular imports
            from .mcp_server_manager import get_user_integration

            integration = get_user_integration(self.user_id, service_name)

            # Basic enablement check
            if not integration or not integration.get("enabled", False):
                logger.debug(
                    f"⚪ Service {service_name} not enabled for user {self.user_id}"
                )
                return False

            oauth_tokens = self._get_oauth_tokens_for_service(service_name)
            if not oauth_tokens:
                logger.debug(
                    f"⚪ No OAuth tokens found for {service_name}, user {self.user_id}"
                )
                return False

            # Validate token is not expired
            if oauth_tokens.is_expired():
                logger.warning(
                    f"⚠️ OAuth token expired for {service_name}, user {self.user_id}"
                )
                return False

            logger.info(
                f"✅ Service {service_name} enabled with valid OAuth tokens for user {self.user_id}"
            )
            return True

        except Exception as e:
            logger.warning(f"⚠️ Could not check service {service_name} status: {e}")
            return False

    def _get_oauth_tokens_for_service(self, service_name: str) -> Optional[OAuthTokens]:
        """
        Get OAuth tokens for a specific service from the user's integrations.

        Args:
            service_name: Name of the service to get tokens for

        Returns:
            OAuthTokens if available, None otherwise
        """
        try:
            # Ensure user_id is available
            if not self.user_id:
                return None

            # Import here to avoid circular imports
            from app.api.oauth_integration_manager import get_oauth_integration_manager

            oauth_manager = get_oauth_integration_manager()

            # Get tokens from OAuth manager (using existing methods)
            # For now, use the create_mcp_credentials method to check if we have valid credentials
            credentials = oauth_manager.create_mcp_credentials(
                self.user_id, service_name
            )

            if not credentials:
                return None

            # Extract basic token info from credentials
            # This is a temporary implementation until we have a proper get_user_tokens method
            access_token = credentials.get("access_token")
            if not access_token:
                logger.debug(f"⚪ No access token found for {service_name}")
                return None

            # Map service name to OAuth provider
            provider_mapping = {
                "google_calendar": OAuthProvider.GOOGLE,
                "twitter": OAuthProvider.TWITTER,
                "sendgrid": OAuthProvider.SENDGRID,
                "calendly_v2": OAuthProvider.CALENDLY,
                "pipedrive": OAuthProvider.PIPEDRIVE,
                "salesforce_rest_api": OAuthProvider.SALESFORCE,
                "zoho_crm": OAuthProvider.ZOHO,
            }

            provider = provider_mapping.get(service_name)
            if not provider:
                logger.warning(f"⚠️ Unknown OAuth provider for service: {service_name}")
                return None

            # Create OAuthTokens object with proper type handling
            return OAuthTokens(
                access_token=access_token,
                refresh_token=credentials.get("refresh_token"),
                token_type=credentials.get("token_type", "Bearer"),
                expires_at=credentials.get("expires_at"),
                scope=credentials.get("scope"),
                provider=provider,
                user_id=self.user_id,
                service_account_id=credentials.get("service_account_id"),
            )

        except ImportError:
            logger.info(f"ℹ️ OAuth integration manager not available for {service_name}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Error getting OAuth tokens for {service_name}: {e}")
            return None

    def _get_oauth_provider_for_service(
        self, service_name: str
    ) -> Optional[OAuthProvider]:
        """
        Get OAuth provider for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            OAuthProvider if known, None otherwise
        """
        provider_mapping = {
            "google_calendar": OAuthProvider.GOOGLE,
            "twitter": OAuthProvider.TWITTER,
            "sendgrid": OAuthProvider.SENDGRID,
            "calendly_v2": OAuthProvider.CALENDLY,
            "pipedrive": OAuthProvider.PIPEDRIVE,
            "salesforce_rest_api": OAuthProvider.SALESFORCE,
            "zoho_crm": OAuthProvider.ZOHO,
        }
        return provider_mapping.get(service_name)

    def get_agent_service_mapping(self) -> Dict[str, List[str]]:
        """
        Get the complete mapping of agents to their MCP services.

        Returns:
            Dictionary mapping agent types to their required services
        """
        return {
            agent_type.value: list(services)
            for agent_type, services in self.AGENT_MCP_MAPPING.items()
        }

    def clear_cache(self) -> None:
        """Clear the MCP server cache."""
        self._mcp_cache.clear()
        logger.info("🧹 Cleared MCP server cache")


# Convenience functions for easy usage
def create_coordinator_mcps(user_id: Optional[str] = None) -> List[Any]:
    """Create MCP servers for Coordinator Agent (SendGrid + Twitter)"""
    factory = AgentMCPFactory(user_id)
    return factory.create_mcp_servers_for_agent(AgentType.COORDINATOR)


def create_meeting_scheduler_mcps(user_id: Optional[str] = None) -> List[Any]:
    """Create MCP servers for Meeting Scheduler Agent (Calendly + Google Calendar)"""
    factory = AgentMCPFactory(user_id)
    return factory.create_mcp_servers_for_agent(AgentType.MEETING_SCHEDULER)


def create_lead_administrator_mcps(user_id: Optional[str] = None) -> List[Any]:
    """Create MCP servers for Lead Administrator Agent (CRM tools)"""
    factory = AgentMCPFactory(user_id)
    return factory.create_mcp_servers_for_agent(AgentType.LEAD_ADMINISTRATOR)


def get_mcp_servers_by_agent_name(
    agent_name: str, user_id: Optional[str] = None
) -> List[Any]:
    """
    Get MCP servers by agent name (string-based lookup).

    Args:
        agent_name: Name of the agent (coordinator, meeting_scheduler, lead_administrator)
        user_id: User identifier for OAuth integration filtering

    Returns:
        List of MCP servers for the specified agent
    """
    agent_mapping = {
        "coordinator": AgentType.COORDINATOR,
        "meeting_scheduler": AgentType.MEETING_SCHEDULER,
        "lead_administrator": AgentType.LEAD_ADMINISTRATOR,
        # Alternative names for flexibility
        "PipeWise Coordinator": AgentType.COORDINATOR,
        "Meeting Scheduling Specialist": AgentType.MEETING_SCHEDULER,
        "PipeWise Lead Administrator": AgentType.LEAD_ADMINISTRATOR,
    }

    agent_type = agent_mapping.get(agent_name)
    if not agent_type:
        logger.warning(f"⚠️ Unknown agent name: {agent_name}")
        return []

    factory = AgentMCPFactory(user_id)
    return factory.create_mcp_servers_for_agent(agent_type)
