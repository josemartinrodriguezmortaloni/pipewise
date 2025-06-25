"""
Unit tests for the Enhanced Coordinator System with Multi-Channel Communication

Tests cover:
1. Communication tools integration (email, Instagram, Twitter)
2. Coordinator agent configuration and behavior
3. Message processing workflows
4. Memory system integration
5. Handoff mechanisms
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from app.agents.agents import (
    ModernAgents,
    IncomingMessage,
    CoordinatorResponse,
    TenantContext,
    create_agents_with_memory,
    # Communication tools
    send_email,
    send_template_email,
    send_instagram_dm,
    get_instagram_user_info,
    send_twitter_dm,
    get_twitter_user_by_username,
    reply_to_tweet,
)
from app.agents.memory import MemoryManager, InMemoryStore
from app.agents.memory.base import TestInMemoryStore


class TestCommunicationTools:
    """Test the communication function tools"""

    @patch("app.agents.tools.email.get_email_client")
    def test_send_email_success(self, mock_get_client):
        """Test successful email sending"""
        # Mock email client
        mock_client = Mock()
        mock_client.send_email.return_value = {
            "success": True,
            "message_id": "email_123",
        }
        mock_get_client.return_value = mock_client

        # Test the function tool
        result = send_email(
            to_email="test@example.com",
            subject="Test Subject",
            content="Test content",
            content_type="html",
        )

        assert "Email sent successfully" in result
        assert "test@example.com" in result
        assert "email_123" in result
        mock_client.send_email.assert_called_once_with(
            "test@example.com", "Test Subject", "Test content", "html"
        )

    @patch("app.agents.tools.email.get_email_client")
    def test_send_email_failure(self, mock_get_client):
        """Test email sending failure"""
        mock_client = Mock()
        mock_client.send_email.return_value = {
            "success": False,
            "error": "SMTP connection failed",
        }
        mock_get_client.return_value = mock_client

        result = send_email(
            to_email="test@example.com", subject="Test Subject", content="Test content"
        )

        assert "Failed to send email" in result
        assert "SMTP connection failed" in result

    @patch("app.agents.tools.instagram.get_instagram_client")
    def test_send_instagram_dm_success(self, mock_get_client):
        """Test successful Instagram DM sending"""
        mock_client = Mock()
        mock_client.send_direct_message.return_value = {
            "success": True,
            "message_id": "ig_msg_456",
        }
        mock_get_client.return_value = mock_client

        result = send_instagram_dm(
            recipient_id="ig_user_123", message="Hello from PipeWise!"
        )

        assert "Instagram DM sent successfully" in result
        assert "ig_user_123" in result
        assert "ig_msg_456" in result

    @patch("app.agents.tools.twitter.get_twitter_client")
    def test_send_twitter_dm_success(self, mock_get_client):
        """Test successful Twitter DM sending"""
        mock_client = Mock()
        mock_client.send_direct_message.return_value = {
            "success": True,
            "message_id": "tw_msg_789",
        }
        mock_get_client.return_value = mock_client

        result = send_twitter_dm(
            recipient_id="tw_user_456", message="Hello from PipeWise!"
        )

        assert "Twitter DM sent successfully" in result
        assert "tw_user_456" in result
        assert "tw_msg_789" in result

    @patch("app.agents.tools.twitter.get_twitter_client")
    def test_get_twitter_user_info(self, mock_get_client):
        """Test Twitter user information retrieval"""
        mock_client = Mock()
        mock_client.get_user_by_username.return_value = {
            "name": "John Doe",
            "id": "tw_123456",
            "public_metrics": {"followers_count": 1000},
        }
        mock_get_client.return_value = mock_client

        result = get_twitter_user_by_username("johndoe")

        assert "Twitter user: @johndoe (John Doe)" in result
        assert "ID: tw_123456" in result
        assert "Followers: 1000" in result


class TestIncomingMessageModel:
    """Test the IncomingMessage model"""

    def test_incoming_message_creation(self):
        """Test creating IncomingMessage instances"""
        # Email message
        email_msg = IncomingMessage(
            lead_id="lead_123",
            channel="email",
            message_content="Hello, interested in PipeWise",
            context={"sender_email": "test@example.com"},
        )

        assert email_msg.lead_id == "lead_123"
        assert email_msg.channel == "email"
        assert email_msg.context["sender_email"] == "test@example.com"

        # Instagram message
        ig_msg = IncomingMessage(
            lead_id="lead_456",
            channel="instagram",
            channel_user_id="ig_123",
            channel_username="testuser",
            message_content="Saw your content about CRM",
        )

        assert ig_msg.channel == "instagram"
        assert ig_msg.channel_user_id == "ig_123"
        assert ig_msg.channel_username == "testuser"

        # Twitter message
        twitter_msg = IncomingMessage(
            lead_id="lead_789",
            channel="twitter",
            channel_user_id="tw_456",
            channel_username="techleader",
            message_content="@PipeWiseCRM great solution!",
            context={"tweet_id": "tweet_123"},
        )

        assert twitter_msg.channel == "twitter"
        assert twitter_msg.context["tweet_id"] == "tweet_123"


class TestEnhancedAgentConfiguration:
    """Test the enhanced agent configuration with communication tools"""

    def test_coordinator_has_communication_tools(self):
        """Test that coordinator agent has all communication tools"""
        # Create memory manager for testing
        volatile_store = TestInMemoryStore()
        memory_manager = MemoryManager(volatile_store, volatile_store)

        # Create agents
        agents = create_agents_with_memory(memory_manager, "test_workflow")
        coordinator = agents["coordinator"]

        # Check that coordinator has the expected tools
        tool_names = [tool.name for tool in coordinator.tools]

        # CRM tools
        assert "get_crm_lead_data" in tool_names
        assert "analyze_lead_opportunity" in tool_names
        assert "update_lead_qualification" in tool_names
        assert "schedule_meeting_for_lead" in tool_names

        # Email tools
        assert "send_email" in tool_names
        assert "send_template_email" in tool_names

        # Instagram tools
        assert "send_instagram_dm" in tool_names
        assert "get_instagram_user_info" in tool_names

        # Twitter tools
        assert "send_twitter_dm" in tool_names
        assert "get_twitter_user_by_username" in tool_names
        assert "reply_to_tweet" in tool_names

    def test_coordinator_output_type(self):
        """Test that coordinator agent has correct output type"""
        volatile_store = TestInMemoryStore()
        memory_manager = MemoryManager(volatile_store, volatile_store)

        agents = create_agents_with_memory(memory_manager, "test_workflow")
        coordinator = agents["coordinator"]

        # Check output type is set correctly
        assert coordinator.output_type == CoordinatorResponse

    def test_coordinator_prompt_loading(self):
        """Test that coordinator loads the coordinatorPrompt"""
        volatile_store = TestInMemoryStore()
        memory_manager = MemoryManager(volatile_store, volatile_store)

        agents = create_agents_with_memory(memory_manager, "test_workflow")
        coordinator = agents["coordinator"]

        # Check that instructions contain reference to coordinator prompt
        # This is a basic check - the actual prompt content loading is tested separately
        assert (
            "PRIMARY CONTACT POINT" in coordinator.instructions
            or "coordinatorPrompt" in coordinator.instructions
        )


class TestModernAgentsEnhanced:
    """Test the enhanced ModernAgents functionality"""

    @pytest.fixture
    def agents(self):
        """Create ModernAgents instance for testing"""
        return ModernAgents()

    @pytest.fixture
    def sample_email_message(self):
        """Sample email message for testing"""
        return IncomingMessage(
            lead_id="test_lead_001",
            channel="email",
            message_content="Hello, interested in your CRM solution",
            context={"sender_email": "test@example.com"},
        )

    @pytest.fixture
    def sample_instagram_message(self):
        """Sample Instagram message for testing"""
        return IncomingMessage(
            lead_id="test_lead_002",
            channel="instagram",
            channel_user_id="ig_123456",
            channel_username="testuser",
            message_content="Saw your post about automation, interested!",
        )

    def test_convenience_method_email(self, agents):
        """Test the convenience method for email messages"""
        # This would normally be an async test, but we'll test the message creation
        # The actual processing would require mocking the entire agent workflow

        # Test that we can create the message structure correctly
        lead_id = "test_lead"
        email_content = "Test email content"
        sender_email = "sender@test.com"

        # We can't easily test the full async workflow without extensive mocking,
        # but we can verify the method exists and the message structure is correct
        assert hasattr(agents, "handle_email_message")
        assert hasattr(agents, "handle_instagram_message")
        assert hasattr(agents, "handle_twitter_message")

    def test_convenience_method_parameters(self, agents):
        """Test that convenience methods have correct parameters"""
        import inspect

        # Check email method signature
        email_sig = inspect.signature(agents.handle_email_message)
        email_params = list(email_sig.parameters.keys())
        assert "lead_id" in email_params
        assert "email_content" in email_params
        assert "sender_email" in email_params

        # Check Instagram method signature
        ig_sig = inspect.signature(agents.handle_instagram_message)
        ig_params = list(ig_sig.parameters.keys())
        assert "lead_id" in ig_params
        assert "message_content" in ig_params
        assert "instagram_user_id" in ig_params
        assert "username" in ig_params

        # Check Twitter method signature
        tw_sig = inspect.signature(agents.handle_twitter_message)
        tw_params = list(tw_sig.parameters.keys())
        assert "lead_id" in tw_params
        assert "message_content" in tw_params
        assert "twitter_user_id" in tw_params
        assert "username" in tw_params
        assert "tweet_id" in tw_params


class TestTenantContextIntegration:
    """Test tenant context integration with enhanced features"""

    def test_tenant_context_with_memory_manager(self):
        """Test creating tenant context with memory manager"""
        volatile_store = TestInMemoryStore()
        memory_manager = MemoryManager(volatile_store, volatile_store)

        tenant_context = TenantContext(
            tenant_id="test_tenant",
            user_id="test_user",
            is_premium=True,
            api_limits={"calls_per_hour": 1000},
            features_enabled=["multi_channel", "ai_coordinator"],
            memory_manager=memory_manager,
        )

        assert tenant_context.memory_manager is not None
        assert tenant_context.is_premium is True
        assert "multi_channel" in tenant_context.features_enabled
        assert "ai_coordinator" in tenant_context.features_enabled

    def test_modern_agents_with_tenant_context(self):
        """Test ModernAgents initialization with tenant context"""
        volatile_store = TestInMemoryStore()
        memory_manager = MemoryManager(volatile_store, volatile_store)

        tenant_context = TenantContext(
            tenant_id="test_tenant",
            user_id="test_user",
            is_premium=True,
            api_limits={"calls_per_hour": 1000},
            features_enabled=["multi_channel"],
            memory_manager=memory_manager,
        )

        agents = ModernAgents(tenant_context)

        assert agents.tenant_context.tenant_id == "test_tenant"
        assert agents.tenant_context.memory_manager is not None


class TestErrorHandling:
    """Test error handling in communication tools"""

    @patch("app.agents.tools.email.get_email_client")
    def test_email_tool_exception_handling(self, mock_get_client):
        """Test that email tool handles exceptions gracefully"""
        mock_get_client.side_effect = Exception("Connection failed")

        result = send_email(
            to_email="test@example.com", subject="Test", content="Test content"
        )

        assert "Error sending email" in result
        assert "Connection failed" in result

    @patch("app.agents.tools.instagram.get_instagram_client")
    def test_instagram_tool_exception_handling(self, mock_get_client):
        """Test that Instagram tool handles exceptions gracefully"""
        mock_get_client.side_effect = Exception("API error")

        result = send_instagram_dm(recipient_id="test_user", message="Test message")

        assert "Error sending Instagram DM" in result
        assert "API error" in result


class TestIntegrationWithExistingSystem:
    """Test integration with existing agent system"""

    def test_enhanced_agents_have_original_tools(self):
        """Test that enhanced agents still have original CRM tools"""
        volatile_store = TestInMemoryStore()
        memory_manager = MemoryManager(volatile_store, volatile_store)

        agents = create_agents_with_memory(memory_manager, "test_workflow")

        # Check that we still have the original specialist agents
        assert "coordinator" in agents
        assert "lead_qualifier" in agents
        assert "meeting_scheduler" in agents

        # Check that lead qualifier still has its tools
        lead_qualifier = agents["lead_qualifier"]
        lead_tools = [tool.name for tool in lead_qualifier.tools]
        assert "get_crm_lead_data" in lead_tools
        assert "analyze_lead_opportunity" in lead_tools
        assert "update_lead_qualification" in lead_tools

        # Check that meeting scheduler still has its tools
        meeting_scheduler = agents["meeting_scheduler"]
        meeting_tools = [tool.name for tool in meeting_scheduler.tools]
        assert "get_crm_lead_data" in meeting_tools
        assert "schedule_meeting_for_lead" in meeting_tools

    def test_handoff_system_preserved(self):
        """Test that handoff system is preserved in enhanced agents"""
        volatile_store = TestInMemoryStore()
        memory_manager = MemoryManager(volatile_store, volatile_store)

        agents = create_agents_with_memory(memory_manager, "test_workflow")
        coordinator = agents["coordinator"]

        # Check that coordinator still has handoffs
        assert len(coordinator.handoffs) > 0

        # Check handoff targets
        handoff_targets = [handoff.agent.name for handoff in coordinator.handoffs]
        assert "Lead Qualification Specialist" in handoff_targets
        assert "Meeting Scheduling Specialist" in handoff_targets


@pytest.mark.asyncio
class TestAsyncIntegration:
    """Test async integration points (requires mocking for full tests)"""

    async def test_modern_agents_async_interface(self):
        """Test that async methods exist and are callable"""
        agents = ModernAgents()

        # Test that async methods exist
        assert hasattr(agents, "handle_incoming_message")
        assert hasattr(agents, "handle_email_message")
        assert hasattr(agents, "handle_instagram_message")
        assert hasattr(agents, "handle_twitter_message")

        # Test that they are coroutines
        import inspect

        assert inspect.iscoroutinefunction(agents.handle_incoming_message)
        assert inspect.iscoroutinefunction(agents.handle_email_message)
        assert inspect.iscoroutinefunction(agents.handle_instagram_message)
        assert inspect.iscoroutinefunction(agents.handle_twitter_message)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
