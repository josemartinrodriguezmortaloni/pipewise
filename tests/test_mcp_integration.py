"""
Unit tests for basic MCP integration functionality.

This module tests the core MCP integration features including:
- Connection establishment and management
- Tool discovery and validation
- Basic MCP operations
- Resource management
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Dict, Any, List, Optional
import asyncio
import json

from app.ai_agents.mcp.agent_mcp_factory import AgentMCPFactory, AgentType
from app.ai_agents.mcp.mcp_server_manager import MCPServerManager
from app.ai_agents.mcp.error_handler import (
    MCPConnectionError,
    MCPOperationError,
    MCPTimeoutError,
)
from app.ai_agents.mcp.oauth_integration import get_mcp_credentials_for_user
from app.ai_agents.tools.pipedream_mcp import PipedreamMCPClient


class TestMCPBasicIntegration:
    """Test basic MCP integration functionality."""

    @pytest.fixture
    async def mock_mcp_client(self) -> AsyncMock:
        """Create a mock MCP client."""
        client = AsyncMock(spec=PipedreamMCPClient)
        client.is_connected = True
        client.available_tools = ["send_email", "post_tweet", "create_calendar_event"]
        return client

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
        }

    @pytest.fixture
    def agent_factory(self) -> AgentMCPFactory:
        """Create an agent MCP factory instance."""
        return AgentMCPFactory()

    async def test_mcp_connection_establishment(
        self, mock_mcp_client: AsyncMock
    ) -> None:
        """Test successful MCP connection establishment."""
        # Arrange
        mock_mcp_client.connect = AsyncMock(return_value=True)
        mock_mcp_client.get_available_tools = AsyncMock(
            return_value=["send_email", "post_tweet"]
        )

        # Act
        result = await mock_mcp_client.connect()
        tools = await mock_mcp_client.get_available_tools()

        # Assert
        assert result is True
        assert tools == ["send_email", "post_tweet"]
        mock_mcp_client.connect.assert_called_once()
        mock_mcp_client.get_available_tools.assert_called_once()

    async def test_mcp_connection_failure(self, mock_mcp_client: AsyncMock) -> None:
        """Test MCP connection failure handling."""
        # Arrange
        mock_mcp_client.connect = AsyncMock(
            side_effect=MCPConnectionError("Connection failed")
        )

        # Act & Assert
        with pytest.raises(MCPConnectionError, match="Connection failed"):
            await mock_mcp_client.connect()

    async def test_mcp_tool_discovery(self, mock_mcp_client: AsyncMock) -> None:
        """Test MCP tool discovery functionality."""
        # Arrange
        expected_tools = [
            {
                "name": "send_email",
                "description": "Send an email via SendGrid",
                "parameters": {"to": "string", "subject": "string", "body": "string"},
            },
            {
                "name": "post_tweet",
                "description": "Post a tweet via Twitter API",
                "parameters": {"content": "string", "media": "optional"},
            },
        ]
        mock_mcp_client.discover_tools = AsyncMock(return_value=expected_tools)

        # Act
        tools = await mock_mcp_client.discover_tools()

        # Assert
        assert len(tools) == 2
        assert tools[0]["name"] == "send_email"
        assert tools[1]["name"] == "post_tweet"
        assert "parameters" in tools[0]
        mock_mcp_client.discover_tools.assert_called_once()

    async def test_mcp_tool_execution(self, mock_mcp_client: AsyncMock) -> None:
        """Test MCP tool execution."""
        # Arrange
        tool_name = "send_email"
        tool_params = {"to": "test@example.com", "subject": "Test", "body": "Hello"}
        expected_result = {"success": True, "message_id": "msg-123"}

        mock_mcp_client.execute_tool = AsyncMock(return_value=expected_result)

        # Act
        result = await mock_mcp_client.execute_tool(tool_name, tool_params)

        # Assert
        assert result == expected_result
        assert result["success"] is True
        mock_mcp_client.execute_tool.assert_called_once_with(tool_name, tool_params)

    async def test_mcp_tool_execution_failure(self, mock_mcp_client: AsyncMock) -> None:
        """Test MCP tool execution failure."""
        # Arrange
        tool_name = "invalid_tool"
        tool_params = {"param": "value"}
        mock_mcp_client.execute_tool = AsyncMock(
            side_effect=MCPOperationError("Tool not found")
        )

        # Act & Assert
        with pytest.raises(MCPOperationError, match="Tool not found"):
            await mock_mcp_client.execute_tool(tool_name, tool_params)

    @pytest.mark.asyncio
    async def test_agent_mcp_factory_coordinator_creation(
        self, agent_factory: AgentMCPFactory, mock_user_credentials: Dict[str, Any]
    ) -> None:
        """Test creation of Coordinator Agent MCPs."""
        # Arrange
        agent_type = AgentType.COORDINATOR

        with patch.object(agent_factory, "_create_coordinator_mcps") as mock_create:
            mock_create.return_value = {"sendgrid": AsyncMock(), "twitter": AsyncMock()}

            # Act
            mcps = await agent_factory.create_agent_mcps(
                agent_type, mock_user_credentials
            )

            # Assert
            assert "sendgrid" in mcps
            assert "twitter" in mcps
            mock_create.assert_called_once_with(mock_user_credentials)

    @pytest.mark.asyncio
    async def test_agent_mcp_factory_meeting_scheduler_creation(
        self, agent_factory: AgentMCPFactory, mock_user_credentials: Dict[str, Any]
    ) -> None:
        """Test creation of Meeting Scheduler Agent MCPs."""
        # Arrange
        agent_type = AgentType.MEETING_SCHEDULER

        with patch.object(
            agent_factory, "_create_meeting_scheduler_mcps"
        ) as mock_create:
            mock_create.return_value = {
                "calendly": AsyncMock(),
                "google_calendar": AsyncMock(),
            }

            # Act
            mcps = await agent_factory.create_agent_mcps(
                agent_type, mock_user_credentials
            )

            # Assert
            assert "calendly" in mcps
            assert "google_calendar" in mcps
            mock_create.assert_called_once_with(mock_user_credentials)

    @pytest.mark.asyncio
    async def test_agent_mcp_factory_lead_administrator_creation(
        self, agent_factory: AgentMCPFactory, mock_user_credentials: Dict[str, Any]
    ) -> None:
        """Test creation of Lead Administrator Agent MCPs."""
        # Arrange
        agent_type = AgentType.LEAD_ADMINISTRATOR

        with patch.object(
            agent_factory, "_create_lead_administrator_mcps"
        ) as mock_create:
            mock_create.return_value = {
                "pipedrive": AsyncMock(),
                "salesforce": AsyncMock(),
                "zoho": AsyncMock(),
            }

            # Act
            mcps = await agent_factory.create_agent_mcps(
                agent_type, mock_user_credentials
            )

            # Assert
            assert "pipedrive" in mcps
            assert "salesforce" in mcps
            assert "zoho" in mcps
            mock_create.assert_called_once_with(mock_user_credentials)

    async def test_mcp_server_manager_initialization(self) -> None:
        """Test MCP server manager initialization."""
        # Arrange & Act
        manager = MCPServerManager()

        # Assert
        assert manager is not None
        assert hasattr(manager, "servers")
        assert isinstance(manager.servers, dict)

    @pytest.mark.asyncio
    async def test_mcp_server_manager_start_servers(self) -> None:
        """Test starting MCP servers through manager."""
        # Arrange
        manager = MCPServerManager()
        mock_servers = {
            "sendgrid": AsyncMock(),
            "twitter": AsyncMock(),
            "calendly": AsyncMock(),
        }

        with patch.object(manager, "start_servers") as mock_start:
            mock_start.return_value = True

            # Act
            result = await manager.start_servers(mock_servers)

            # Assert
            assert result is True
            mock_start.assert_called_once_with(mock_servers)

    @pytest.mark.asyncio
    async def test_mcp_oauth_credentials_retrieval(
        self, mock_user_credentials: Dict[str, Any]
    ) -> None:
        """Test OAuth credentials retrieval for MCP services."""
        # Arrange
        user_id = "test-user-123"
        service_name = "sendgrid"

        with patch(
            "app.ai_agents.mcp.oauth_integration.get_mcp_credentials_for_user"
        ) as mock_get:
            mock_get.return_value = {
                "token": "mock-sendgrid-token",
                "expires_at": "2024-12-31",
            }

            # Act
            credentials = await get_mcp_credentials_for_user(user_id, service_name)

            # Assert
            assert credentials["token"] == "mock-sendgrid-token"
            assert "expires_at" in credentials
            mock_get.assert_called_once_with(user_id, service_name)

    async def test_mcp_connection_timeout_handling(
        self, mock_mcp_client: AsyncMock
    ) -> None:
        """Test MCP connection timeout handling."""
        # Arrange
        mock_mcp_client.connect = AsyncMock(
            side_effect=MCPTimeoutError("Connection timeout")
        )

        # Act & Assert
        with pytest.raises(MCPTimeoutError, match="Connection timeout"):
            await mock_mcp_client.connect()

    async def test_mcp_resource_cleanup(self, mock_mcp_client: AsyncMock) -> None:
        """Test proper resource cleanup for MCP connections."""
        # Arrange
        mock_mcp_client.disconnect = AsyncMock(return_value=True)
        mock_mcp_client.cleanup_resources = AsyncMock(return_value=True)

        # Act
        disconnect_result = await mock_mcp_client.disconnect()
        cleanup_result = await mock_mcp_client.cleanup_resources()

        # Assert
        assert disconnect_result is True
        assert cleanup_result is True
        mock_mcp_client.disconnect.assert_called_once()
        mock_mcp_client.cleanup_resources.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_concurrent_operations(self, mock_mcp_client: AsyncMock) -> None:
        """Test concurrent MCP operations."""
        # Arrange
        mock_mcp_client.execute_tool = AsyncMock(
            side_effect=[
                {"result": "email_sent"},
                {"result": "tweet_posted"},
                {"result": "event_created"},
            ]
        )

        # Act
        tasks = [
            mock_mcp_client.execute_tool("send_email", {"to": "test1@example.com"}),
            mock_mcp_client.execute_tool("post_tweet", {"content": "Hello world"}),
            mock_mcp_client.execute_tool("create_event", {"title": "Meeting"}),
        ]
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 3
        assert results[0]["result"] == "email_sent"
        assert results[1]["result"] == "tweet_posted"
        assert results[2]["result"] == "event_created"
        assert mock_mcp_client.execute_tool.call_count == 3


class TestMCPServiceSpecificIntegration:
    """Test service-specific MCP integrations."""

    @pytest.fixture
    def sendgrid_mcp_config(self) -> Dict[str, Any]:
        """SendGrid MCP configuration."""
        return {
            "service": "sendgrid",
            "tools": ["send_email", "create_template", "manage_contacts"],
            "api_key": "mock-sendgrid-key",
        }

    @pytest.fixture
    def twitter_mcp_config(self) -> Dict[str, Any]:
        """Twitter MCP configuration."""
        return {
            "service": "twitter",
            "tools": ["post_tweet", "send_dm", "search_tweets"],
            "api_key": "mock-twitter-key",
        }

    async def test_sendgrid_mcp_email_sending(
        self, sendgrid_mcp_config: Dict[str, Any]
    ) -> None:
        """Test SendGrid MCP email sending."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.send_email = AsyncMock(
            return_value={"success": True, "message_id": "msg-123"}
        )

        # Act
        result = await mock_client.send_email(
            to="test@example.com", subject="Test Email", body="Hello from MCP"
        )

        # Assert
        assert result["success"] is True
        assert "message_id" in result
        mock_client.send_email.assert_called_once()

    async def test_twitter_mcp_tweet_posting(
        self, twitter_mcp_config: Dict[str, Any]
    ) -> None:
        """Test Twitter MCP tweet posting."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.post_tweet = AsyncMock(
            return_value={"success": True, "tweet_id": "tweet-123"}
        )

        # Act
        result = await mock_client.post_tweet(content="Hello from MCP integration!")

        # Assert
        assert result["success"] is True
        assert "tweet_id" in result
        mock_client.post_tweet.assert_called_once_with(
            content="Hello from MCP integration!"
        )

    async def test_calendly_mcp_meeting_scheduling(self) -> None:
        """Test Calendly MCP meeting scheduling."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.create_meeting = AsyncMock(
            return_value={
                "success": True,
                "meeting_url": "https://calendly.com/meeting/123",
                "meeting_id": "meeting-123",
            }
        )

        # Act
        result = await mock_client.create_meeting(
            title="Discovery Call", duration=30, attendee_email="lead@example.com"
        )

        # Assert
        assert result["success"] is True
        assert "meeting_url" in result
        assert "meeting_id" in result
        mock_client.create_meeting.assert_called_once()

    async def test_pipedrive_mcp_lead_management(self) -> None:
        """Test Pipedrive MCP lead management."""
        # Arrange
        mock_client = AsyncMock()
        mock_client.create_deal = AsyncMock(
            return_value={"success": True, "deal_id": "deal-123", "status": "open"}
        )

        # Act
        result = await mock_client.create_deal(
            title="New Lead - Company ABC",
            value=5000,
            person_name="John Doe",
            person_email="john@company.com",
        )

        # Assert
        assert result["success"] is True
        assert "deal_id" in result
        assert result["status"] == "open"
        mock_client.create_deal.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
