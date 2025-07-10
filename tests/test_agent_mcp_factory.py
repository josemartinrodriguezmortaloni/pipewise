"""
Unit tests for Agent MCP Factory functionality.

This module tests the factory pattern for creating agent-specific MCPs including:
- Agent type validation and mapping
- Factory creation methods for each agent type
- MCP configuration and initialization
- Error handling in factory operations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, Any, List, Optional
import asyncio
from enum import Enum

from app.ai_agents.mcp.agent_mcp_factory import AgentMCPFactory, AgentType
from app.ai_agents.mcp.error_handler import (
    MCPConnectionError,
    MCPConfigurationError,
    MCPOperationError,
)
from app.ai_agents.tools.pipedream_mcp import PipedreamMCPClient


class TestAgentMCPFactory:
    """Test Agent MCP Factory functionality."""

    @pytest.fixture
    def factory(self) -> AgentMCPFactory:
        """Create an Agent MCP Factory instance."""
        return AgentMCPFactory()

    @pytest.fixture
    def mock_user_credentials(self) -> Dict[str, Any]:
        """Create mock user OAuth credentials."""
        return {
            "user_id": "test-user-123",
            "google_token": "mock-google-token",
            "twitter_token": "mock-twitter-token",
            "sendgrid_token": "mock-sendgrid-token",
            "calendly_token": "mock-calendly-token",
            "pipedrive_token": "mock-pipedrive-token",
            "salesforce_token": "mock-salesforce-token",
            "zoho_token": "mock-zoho-token",
        }

    @pytest.fixture
    def mock_sendgrid_mcp(self) -> AsyncMock:
        """Create mock SendGrid MCP client."""
        client = AsyncMock()
        client.service_name = "sendgrid"
        client.is_connected = True
        client.available_tools = [
            "send_email",
            "create_template",
            "manage_contacts",
            "get_stats",
        ]
        return client

    @pytest.fixture
    def mock_twitter_mcp(self) -> AsyncMock:
        """Create mock Twitter MCP client."""
        client = AsyncMock()
        client.service_name = "twitter"
        client.is_connected = True
        client.available_tools = [
            "post_tweet",
            "send_dm",
            "search_tweets",
            "get_profile",
        ]
        return client

    @pytest.fixture
    def mock_calendly_mcp(self) -> AsyncMock:
        """Create mock Calendly MCP client."""
        client = AsyncMock()
        client.service_name = "calendly"
        client.is_connected = True
        client.available_tools = [
            "create_meeting",
            "cancel_meeting",
            "get_availability",
        ]
        return client

    @pytest.fixture
    def mock_google_calendar_mcp(self) -> AsyncMock:
        """Create mock Google Calendar MCP client."""
        client = AsyncMock()
        client.service_name = "google_calendar"
        client.is_connected = True
        client.available_tools = [
            "create_event",
            "update_event",
            "delete_event",
            "get_availability",
        ]
        return client

    def test_agent_type_enum_values(self) -> None:
        """Test that AgentType enum has expected values."""
        # Act & Assert
        assert AgentType.COORDINATOR in AgentType
        assert AgentType.MEETING_SCHEDULER in AgentType
        assert AgentType.LEAD_ADMINISTRATOR in AgentType

        # Check string representations
        assert AgentType.COORDINATOR.value == "coordinator"
        assert AgentType.MEETING_SCHEDULER.value == "meeting_scheduler"
        assert AgentType.LEAD_ADMINISTRATOR.value == "lead_administrator"

    def test_factory_initialization(self, factory: AgentMCPFactory) -> None:
        """Test factory initialization."""
        # Assert
        assert factory is not None
        assert hasattr(factory, "create_agent_mcps")
        assert hasattr(factory, "_create_coordinator_mcps")
        assert hasattr(factory, "_create_meeting_scheduler_mcps")
        assert hasattr(factory, "_create_lead_administrator_mcps")

    @pytest.mark.asyncio
    async def test_create_coordinator_mcps(
        self,
        factory: AgentMCPFactory,
        mock_user_credentials: Dict[str, Any],
        mock_sendgrid_mcp: AsyncMock,
        mock_twitter_mcp: AsyncMock,
    ) -> None:
        """Test creation of Coordinator Agent MCPs."""
        # Arrange
        with patch.object(
            factory, "_create_sendgrid_mcp", return_value=mock_sendgrid_mcp
        ) as mock_sendgrid:
            with patch.object(
                factory, "_create_twitter_mcp", return_value=mock_twitter_mcp
            ) as mock_twitter:
                # Act
                mcps = await factory.create_agent_mcps(
                    AgentType.COORDINATOR, mock_user_credentials
                )

                # Assert
                assert "sendgrid" in mcps
                assert "twitter" in mcps
                assert mcps["sendgrid"] == mock_sendgrid_mcp
                assert mcps["twitter"] == mock_twitter_mcp

                mock_sendgrid.assert_called_once_with(mock_user_credentials)
                mock_twitter.assert_called_once_with(mock_user_credentials)

    @pytest.mark.asyncio
    async def test_create_meeting_scheduler_mcps(
        self,
        factory: AgentMCPFactory,
        mock_user_credentials: Dict[str, Any],
        mock_calendly_mcp: AsyncMock,
        mock_google_calendar_mcp: AsyncMock,
    ) -> None:
        """Test creation of Meeting Scheduler Agent MCPs."""
        # Arrange
        with patch.object(
            factory, "_create_calendly_mcp", return_value=mock_calendly_mcp
        ) as mock_calendly:
            with patch.object(
                factory,
                "_create_google_calendar_mcp",
                return_value=mock_google_calendar_mcp,
            ) as mock_gcal:
                # Act
                mcps = await factory.create_agent_mcps(
                    AgentType.MEETING_SCHEDULER, mock_user_credentials
                )

                # Assert
                assert "calendly" in mcps
                assert "google_calendar" in mcps
                assert mcps["calendly"] == mock_calendly_mcp
                assert mcps["google_calendar"] == mock_google_calendar_mcp

                mock_calendly.assert_called_once_with(mock_user_credentials)
                mock_gcal.assert_called_once_with(mock_user_credentials)

    @pytest.mark.asyncio
    async def test_create_lead_administrator_mcps(
        self, factory: AgentMCPFactory, mock_user_credentials: Dict[str, Any]
    ) -> None:
        """Test creation of Lead Administrator Agent MCPs."""
        # Arrange
        mock_pipedrive = AsyncMock()
        mock_salesforce = AsyncMock()
        mock_zoho = AsyncMock()

        mock_pipedrive.service_name = "pipedrive"
        mock_salesforce.service_name = "salesforce"
        mock_zoho.service_name = "zoho"

        with patch.object(
            factory, "_create_pipedrive_mcp", return_value=mock_pipedrive
        ) as mock_pipe:
            with patch.object(
                factory, "_create_salesforce_mcp", return_value=mock_salesforce
            ) as mock_sf:
                with patch.object(
                    factory, "_create_zoho_mcp", return_value=mock_zoho
                ) as mock_z:
                    # Act
                    mcps = await factory.create_agent_mcps(
                        AgentType.LEAD_ADMINISTRATOR, mock_user_credentials
                    )

                    # Assert
                    assert "pipedrive" in mcps
                    assert "salesforce" in mcps
                    assert "zoho" in mcps
                    assert mcps["pipedrive"] == mock_pipedrive
                    assert mcps["salesforce"] == mock_salesforce
                    assert mcps["zoho"] == mock_zoho

                    mock_pipe.assert_called_once_with(mock_user_credentials)
                    mock_sf.assert_called_once_with(mock_user_credentials)
                    mock_z.assert_called_once_with(mock_user_credentials)

    @pytest.mark.asyncio
    async def test_invalid_agent_type_error(
        self, factory: AgentMCPFactory, mock_user_credentials: Dict[str, Any]
    ) -> None:
        """Test error handling for invalid agent type."""
        # Arrange
        invalid_agent_type = "invalid_agent"

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported agent type"):
            await factory.create_agent_mcps(invalid_agent_type, mock_user_credentials)

    @pytest.mark.asyncio
    async def test_missing_credentials_error(self, factory: AgentMCPFactory) -> None:
        """Test error handling for missing user credentials."""
        # Arrange
        incomplete_credentials = {"user_id": "test-user-123"}  # Missing OAuth tokens

        # Act & Assert
        with pytest.raises(MCPConfigurationError, match="Missing required credentials"):
            await factory.create_agent_mcps(
                AgentType.COORDINATOR, incomplete_credentials
            )

    @pytest.mark.asyncio
    async def test_mcp_connection_failure_handling(
        self, factory: AgentMCPFactory, mock_user_credentials: Dict[str, Any]
    ) -> None:
        """Test handling of MCP connection failures during creation."""
        # Arrange
        with patch.object(
            factory,
            "_create_sendgrid_mcp",
            side_effect=MCPConnectionError("SendGrid connection failed"),
        ):
            with patch.object(
                factory, "_create_twitter_mcp", return_value=AsyncMock()
            ) as mock_twitter:
                # Act & Assert
                with pytest.raises(
                    MCPConnectionError, match="SendGrid connection failed"
                ):
                    await factory.create_agent_mcps(
                        AgentType.COORDINATOR, mock_user_credentials
                    )

    @pytest.mark.asyncio
    async def test_partial_mcp_creation_success(
        self, factory: AgentMCPFactory, mock_user_credentials: Dict[str, Any]
    ) -> None:
        """Test successful creation when some MCPs fail but others succeed."""
        # Arrange
        mock_twitter = AsyncMock()
        mock_twitter.service_name = "twitter"

        with patch.object(
            factory,
            "_create_sendgrid_mcp",
            side_effect=MCPConnectionError("SendGrid failed"),
        ):
            with patch.object(
                factory, "_create_twitter_mcp", return_value=mock_twitter
            ):
                with patch.object(
                    factory, "_handle_partial_failures", return_value=True
                ):
                    # Act
                    mcps = await factory.create_agent_mcps(
                        AgentType.COORDINATOR, mock_user_credentials
                    )

                    # Assert - Should only contain successful MCPs
                    assert "twitter" in mcps
                    assert "sendgrid" not in mcps or mcps["sendgrid"] is None

    def test_get_agent_mcp_mapping(self, factory: AgentMCPFactory) -> None:
        """Test getting the MCP mapping for different agent types."""
        # Act
        coordinator_mapping = factory.get_agent_mcp_mapping(AgentType.COORDINATOR)
        scheduler_mapping = factory.get_agent_mcp_mapping(AgentType.MEETING_SCHEDULER)
        admin_mapping = factory.get_agent_mcp_mapping(AgentType.LEAD_ADMINISTRATOR)

        # Assert
        assert "sendgrid" in coordinator_mapping
        assert "twitter" in coordinator_mapping

        assert "calendly" in scheduler_mapping
        assert "google_calendar" in scheduler_mapping

        assert "pipedrive" in admin_mapping
        assert "salesforce" in admin_mapping
        assert "zoho" in admin_mapping

    @pytest.mark.asyncio
    async def test_validate_mcp_requirements(
        self, factory: AgentMCPFactory, mock_user_credentials: Dict[str, Any]
    ) -> None:
        """Test validation of MCP requirements before creation."""
        # Arrange
        with patch.object(
            factory, "_validate_agent_requirements", return_value=True
        ) as mock_validate:
            # Act
            is_valid = await factory.validate_mcp_requirements(
                AgentType.COORDINATOR, mock_user_credentials
            )

            # Assert
            assert is_valid is True
            mock_validate.assert_called_once_with(
                AgentType.COORDINATOR, mock_user_credentials
            )

    @pytest.mark.asyncio
    async def test_concurrent_mcp_creation(
        self, factory: AgentMCPFactory, mock_user_credentials: Dict[str, Any]
    ) -> None:
        """Test concurrent creation of MCPs for multiple agent types."""
        # Arrange
        mock_coordinator_mcps = {"sendgrid": AsyncMock(), "twitter": AsyncMock()}
        mock_scheduler_mcps = {"calendly": AsyncMock(), "google_calendar": AsyncMock()}

        with patch.object(
            factory,
            "create_agent_mcps",
            side_effect=[mock_coordinator_mcps, mock_scheduler_mcps],
        ) as mock_create:
            # Act
            tasks = [
                factory.create_agent_mcps(AgentType.COORDINATOR, mock_user_credentials),
                factory.create_agent_mcps(
                    AgentType.MEETING_SCHEDULER, mock_user_credentials
                ),
            ]
            results = await asyncio.gather(*tasks)

            # Assert
            assert len(results) == 2
            assert results[0] == mock_coordinator_mcps
            assert results[1] == mock_scheduler_mcps
            assert mock_create.call_count == 2

    def test_factory_configuration_defaults(self, factory: AgentMCPFactory) -> None:
        """Test factory configuration defaults."""
        # Act
        config = factory.get_default_configuration()

        # Assert
        assert "timeout" in config
        assert "retry_attempts" in config
        assert "connection_pool_size" in config
        assert config["timeout"] > 0
        assert config["retry_attempts"] > 0

    @pytest.mark.asyncio
    async def test_cleanup_mcps_on_failure(
        self, factory: AgentMCPFactory, mock_user_credentials: Dict[str, Any]
    ) -> None:
        """Test cleanup of successfully created MCPs when subsequent creation fails."""
        # Arrange
        mock_sendgrid = AsyncMock()
        mock_sendgrid.disconnect = AsyncMock()

        with patch.object(factory, "_create_sendgrid_mcp", return_value=mock_sendgrid):
            with patch.object(
                factory,
                "_create_twitter_mcp",
                side_effect=MCPConnectionError("Twitter failed"),
            ):
                with patch.object(factory, "_cleanup_failed_mcps") as mock_cleanup:
                    # Act & Assert
                    with pytest.raises(MCPConnectionError):
                        await factory.create_agent_mcps(
                            AgentType.COORDINATOR, mock_user_credentials
                        )

                    # Should call cleanup for partially created MCPs
                    mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_health_validation(
        self, factory: AgentMCPFactory, mock_sendgrid_mcp: AsyncMock
    ) -> None:
        """Test health validation of created MCPs."""
        # Arrange
        mock_sendgrid_mcp.health_check = AsyncMock(
            return_value={"status": "healthy", "response_time": 100}
        )

        # Act
        health_status = await factory.validate_mcp_health(mock_sendgrid_mcp)

        # Assert
        assert health_status["status"] == "healthy"
        assert "response_time" in health_status
        mock_sendgrid_mcp.health_check.assert_called_once()

    def test_get_supported_agent_types(self, factory: AgentMCPFactory) -> None:
        """Test getting list of supported agent types."""
        # Act
        supported_types = factory.get_supported_agent_types()

        # Assert
        assert AgentType.COORDINATOR in supported_types
        assert AgentType.MEETING_SCHEDULER in supported_types
        assert AgentType.LEAD_ADMINISTRATOR in supported_types
        assert len(supported_types) == 3


class TestAgentMCPConfiguration:
    """Test agent-specific MCP configuration."""

    @pytest.fixture
    def factory(self) -> AgentMCPFactory:
        """Create factory instance."""
        return AgentMCPFactory()

    def test_coordinator_agent_mcp_config(self, factory: AgentMCPFactory) -> None:
        """Test Coordinator Agent MCP configuration."""
        # Act
        config = factory.get_agent_mcp_config(AgentType.COORDINATOR)

        # Assert
        assert "sendgrid" in config
        assert "twitter" in config
        assert config["sendgrid"]["tools"] is not None
        assert config["twitter"]["tools"] is not None

    def test_meeting_scheduler_agent_mcp_config(self, factory: AgentMCPFactory) -> None:
        """Test Meeting Scheduler Agent MCP configuration."""
        # Act
        config = factory.get_agent_mcp_config(AgentType.MEETING_SCHEDULER)

        # Assert
        assert "calendly" in config
        assert "google_calendar" in config
        assert config["calendly"]["tools"] is not None
        assert config["google_calendar"]["tools"] is not None

    def test_lead_administrator_agent_mcp_config(
        self, factory: AgentMCPFactory
    ) -> None:
        """Test Lead Administrator Agent MCP configuration."""
        # Act
        config = factory.get_agent_mcp_config(AgentType.LEAD_ADMINISTRATOR)

        # Assert
        assert "pipedrive" in config
        assert "salesforce" in config
        assert "zoho" in config
        assert config["pipedrive"]["tools"] is not None

    def test_invalid_agent_type_config_error(self, factory: AgentMCPFactory) -> None:
        """Test error handling for invalid agent type in configuration."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported agent type"):
            factory.get_agent_mcp_config("invalid_agent")

    def test_mcp_tool_validation(self, factory: AgentMCPFactory) -> None:
        """Test validation of MCP tools for each agent type."""
        # Act
        coordinator_tools = factory.get_required_tools(AgentType.COORDINATOR)
        scheduler_tools = factory.get_required_tools(AgentType.MEETING_SCHEDULER)
        admin_tools = factory.get_required_tools(AgentType.LEAD_ADMINISTRATOR)

        # Assert - Coordinator tools
        assert "send_email" in coordinator_tools
        assert "post_tweet" in coordinator_tools

        # Assert - Meeting Scheduler tools
        assert "create_meeting" in scheduler_tools
        assert "create_event" in scheduler_tools

        # Assert - Lead Administrator tools
        assert "create_deal" in admin_tools
        assert "update_lead" in admin_tools


if __name__ == "__main__":
    pytest.main([__file__])
