"""
Test suite for the memory and handoff system.

Tests the complete integration of:
- Dual memory system (volatile + persistent)
- Handoff callbacks with memory tracking
- Agent communication and context preservation
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.agents.memory import MemoryManager, InMemoryStore, SupabaseMemoryStore
from app.agents.callbacks import create_handoff_callback, HandoffData
from app.agents.agents import (
    ModernAgents,
    ModernLeadProcessor,
    TenantContext,
    create_agents_with_memory,
)


class TestInMemoryStore(InMemoryStore):
    """Test version of InMemoryStore without automatic cleanup task."""

    def _start_cleanup_task(self) -> None:
        """Override to prevent automatic cleanup task in tests."""
        self._cleanup_task = None


class TestMemorySystem:
    """Test the dual memory system functionality."""

    @pytest.fixture
    def memory_manager(self) -> MemoryManager:
        """Create a test memory manager with mocked stores."""
        # Use test version without automatic cleanup
        volatile_store = TestInMemoryStore(default_ttl=300)

        # Mock Supabase store for testing
        mock_supabase_client = Mock()
        persistent_store = SupabaseMemoryStore(mock_supabase_client)

        # Mock the persistent store methods
        persistent_store.save = AsyncMock(return_value="persistent-123")
        persistent_store.get = AsyncMock(return_value=None)
        persistent_store.get_by_agent = AsyncMock(return_value=[])
        persistent_store.get_by_workflow = AsyncMock(return_value=[])
        persistent_store.delete = AsyncMock(return_value=True)
        persistent_store.clear_workflow = AsyncMock(return_value=0)

        return MemoryManager(volatile_store, persistent_store)

    @pytest.mark.asyncio
    async def test_volatile_memory_storage(self, memory_manager: MemoryManager) -> None:
        """Test volatile memory storage and retrieval."""
        agent_id = "test_agent"
        workflow_id = "test_workflow"
        content = {"message": "test message", "value": 42}

        # Save to volatile memory
        memory_id = await memory_manager.save_volatile(
            agent_id=agent_id,
            workflow_id=workflow_id,
            content=content,
            tags=["test", "volatile"],
        )

        assert memory_id is not None

        # Retrieve from volatile memory
        agent_memories = await memory_manager.get_agent_context(agent_id, workflow_id)

        assert len(agent_memories["volatile"]) == 1
        assert agent_memories["volatile"][0].content == content
        assert "test" in agent_memories["volatile"][0].tags

    @pytest.mark.asyncio
    async def test_persistent_memory_storage(
        self, memory_manager: MemoryManager
    ) -> None:
        """Test persistent memory storage."""
        agent_id = "test_agent"
        workflow_id = "test_workflow"
        content = {"important": "data", "score": 85.5}

        # Save to persistent memory
        memory_id = await memory_manager.save_persistent(
            agent_id=agent_id,
            workflow_id=workflow_id,
            content=content,
            tags=["test", "persistent"],
            metadata={"importance": "high"},
        )

        # Verify memory ID was returned
        assert memory_id == "persistent-123"  # From mock

        # Verify the mock was called correctly
        memory_manager.persistent.save.assert_called_once()
        call_args = memory_manager.persistent.save.call_args

        assert call_args[1]["agent_id"] == agent_id
        assert call_args[1]["workflow_id"] == workflow_id
        assert call_args[1]["content"] == content
        assert "persistent" in call_args[1]["tags"]

    @pytest.mark.asyncio
    async def test_dual_memory_save(self, memory_manager: MemoryManager) -> None:
        """Test saving to both volatile and persistent memory."""
        agent_id = "test_agent"
        workflow_id = "test_workflow"
        content = {"dual": "memory", "timestamp": datetime.now().isoformat()}

        # Save to both stores
        result = await memory_manager.save_both(
            agent_id=agent_id,
            workflow_id=workflow_id,
            content=content,
            tags=["dual", "test"],
        )

        assert "volatile_id" in result
        assert "persistent_id" in result
        assert result["volatile_id"] is not None
        assert result["persistent_id"] == "persistent-123"  # From mock

    @pytest.mark.asyncio
    async def test_memory_ttl_cleanup(self) -> None:
        """Test TTL-based cleanup in volatile memory."""
        volatile_store = InMemoryStore(default_ttl=1)  # 1 second TTL
        persistent_store = Mock()
        memory_manager = MemoryManager(volatile_store, persistent_store)

        # Save with short TTL
        memory_id = await memory_manager.save_volatile(
            agent_id="test_agent",
            workflow_id="test_workflow",
            content={"ephemeral": "data"},
        )

        # Verify it exists initially
        memory = await volatile_store.get(memory_id)
        assert memory is not None

        # Wait for TTL expiration
        await asyncio.sleep(2)

        # Verify it's been cleaned up
        memory = await volatile_store.get(memory_id)
        assert memory is None


class TestHandoffSystem:
    """Test the handoff callback system."""

    @pytest.fixture
    async def handoff_callback(self, memory_manager: MemoryManager):
        """Create a test handoff callback."""
        return create_handoff_callback(
            memory_manager=memory_manager,
            from_agent_id="agent_a",
            to_agent_id="agent_b",
            workflow_id="test_workflow",
            tenant_context={"tenant_id": "test_tenant"},
        )

    @pytest.mark.asyncio
    async def test_handoff_callback_execution(
        self, memory_manager: MemoryManager, handoff_callback
    ) -> None:
        """Test handoff callback execution and memory storage."""
        # Mock context wrapper
        mock_ctx = Mock()

        # Create handoff data
        handoff_data = HandoffData(
            reason="Lead qualification complete",
            priority="high",
            additional_context={"score": 85, "qualified": True},
        )

        # Execute handoff callback
        result = await handoff_callback(mock_ctx, handoff_data)

        assert result.success is True
        assert result.from_agent == "agent_a"
        assert result.to_agent == "agent_b"
        assert result.input_data == handoff_data
        assert result.handoff_id is not None

        # Verify memory storage
        workflow_context = await memory_manager.get_workflow_context("test_workflow")
        handoff_memories = [
            m for m in workflow_context["volatile"] if "handoff" in m.tags
        ]

        assert len(handoff_memories) > 0
        handoff_memory = handoff_memories[0]
        assert handoff_memory.content["from_agent"] == "agent_a"
        assert handoff_memory.content["to_agent"] == "agent_b"

    @pytest.mark.asyncio
    async def test_handoff_error_handling(self, memory_manager: MemoryManager) -> None:
        """Test handoff error handling and error storage."""
        # Create callback that will fail
        callback = create_handoff_callback(
            memory_manager=memory_manager,
            from_agent_id="agent_a",
            to_agent_id="agent_b",
            workflow_id="test_workflow",
        )

        # Mock memory_manager to raise an exception
        memory_manager.save_both = AsyncMock(side_effect=Exception("Memory error"))

        mock_ctx = Mock()
        handoff_data = HandoffData(reason="Test handoff")

        # Execute handoff - should handle error gracefully
        result = await callback(mock_ctx, handoff_data)

        assert result.success is False
        assert "Memory error" in result.result_summary


class TestAgentIntegration:
    """Test the complete agent integration with memory and handoffs."""

    @pytest.fixture
    def tenant_context(self, memory_manager: MemoryManager) -> TenantContext:
        """Create test tenant context with memory manager."""
        return TenantContext(
            tenant_id="test_tenant",
            user_id="test_user",
            is_premium=True,
            api_limits={"calls_per_hour": 1000},
            features_enabled=["qualification", "meetings"],
            memory_manager=memory_manager,
        )

    @pytest.mark.asyncio
    async def test_create_agents_with_memory(
        self, memory_manager: MemoryManager
    ) -> None:
        """Test creation of memory-enabled agents."""
        workflow_id = "test_workflow"

        agents = create_agents_with_memory(memory_manager, workflow_id)

        assert "coordinator" in agents
        assert "lead_qualifier" in agents
        assert "meeting_scheduler" in agents

        # Verify agents have handoffs configured
        coordinator = agents["coordinator"]
        assert (
            len(coordinator.handoffs) == 2
        )  # To specialist agents (no outbound agent)

    @pytest.mark.asyncio
    @patch("app.agents.agents.Runner.run")
    async def test_modern_lead_processor_with_memory(
        self,
        mock_runner_run: AsyncMock,
        memory_manager: MemoryManager,
        tenant_context: TenantContext,
    ) -> None:
        """Test ModernLeadProcessor with memory system."""
        # Mock the Runner.run result
        mock_result = Mock()
        mock_result.final_output = {"status": "qualified", "score": 85}
        mock_runner_run.return_value = mock_result

        processor = ModernLeadProcessor(tenant_context)

        lead_data = {
            "id": "lead-123",
            "email": "test@example.com",
            "company": "Test Corp",
            "message": "Interested in your CRM solution",
        }

        # Process workflow
        result = await processor.process_lead_workflow(lead_data)

        assert result["status"] == "completed"
        assert "workflow_id" in result
        assert "memory_summary" in result
        assert result["workflow_completed"] is True

        # Verify memory storage
        workflow_context = await memory_manager.get_workflow_context(
            result["workflow_id"]
        )

        # Should have workflow initialization and completion memories
        workflow_memories = (
            workflow_context["volatile"] + workflow_context["persistent"]
        )
        assert len(workflow_memories) >= 2

        # Verify workflow start memory
        start_memories = [m for m in workflow_memories if "workflow_start" in m.tags]
        assert len(start_memories) > 0
        assert start_memories[0].content["lead_data"] == lead_data

    @pytest.mark.asyncio
    @patch("app.supabase.supabase_client.SupabaseCRMClient")
    async def test_modern_agents_initialization(
        self, mock_supabase_client: Mock
    ) -> None:
        """Test ModernAgents initialization with default memory manager."""
        mock_client_instance = Mock()
        mock_supabase_client.return_value.client = mock_client_instance

        # Test with no tenant context (should create default)
        modern_agents = ModernAgents()

        assert modern_agents.tenant_context is not None
        assert modern_agents.tenant_context.memory_manager is not None
        assert modern_agents.tenant_context.tenant_id == "default"

        # Test with provided tenant context but no memory manager
        tenant_context = TenantContext(
            tenant_id="custom_tenant",
            user_id="custom_user",
            is_premium=False,
            api_limits={"calls_per_hour": 500},
            features_enabled=["basic"],
        )

        modern_agents_custom = ModernAgents(tenant_context)

        assert modern_agents_custom.tenant_context.tenant_id == "custom_tenant"
        assert modern_agents_custom.tenant_context.memory_manager is not None


class TestWorkflowMemoryPersistence:
    """Test workflow-level memory persistence and retrieval."""

    @pytest.mark.asyncio
    async def test_workflow_memory_archival(
        self, memory_manager: MemoryManager
    ) -> None:
        """Test archiving workflow memories from volatile to persistent."""
        workflow_id = "test_workflow"

        # Create some volatile memories
        await memory_manager.save_volatile(
            agent_id="agent_1",
            workflow_id=workflow_id,
            content={"step": 1, "data": "qualification"},
            tags=["qualification"],
        )

        await memory_manager.save_volatile(
            agent_id="agent_2",
            workflow_id=workflow_id,
            content={"step": 2, "data": "outbound"},
            tags=["outbound"],
        )

        # Archive the workflow
        archive_result = await memory_manager.archive_workflow(workflow_id)

        assert archive_result["archived"] == 2
        assert archive_result["cleared"] == 2

        # Verify volatile memories are cleared
        volatile_memories = await memory_manager.volatile.get_by_workflow(workflow_id)
        assert len(volatile_memories) == 0

        # Verify persistent store was called for archiving
        assert memory_manager.persistent.save.call_count >= 2

    @pytest.mark.asyncio
    async def test_cross_agent_memory_sharing(
        self, memory_manager: MemoryManager
    ) -> None:
        """Test that handoffs create accessible memories for target agents."""
        workflow_id = "test_workflow"

        # Create handoff callback
        callback = create_handoff_callback(
            memory_manager=memory_manager,
            from_agent_id="agent_a",
            to_agent_id="agent_b",
            workflow_id=workflow_id,
        )

        # Execute handoff
        mock_ctx = Mock()
        handoff_data = HandoffData(
            reason="Qualification complete, ready for outbound",
            priority="normal",
            additional_context={"qualified": True, "score": 90},
        )

        await callback(mock_ctx, handoff_data)

        # Verify target agent can access handoff context
        agent_b_memories = await memory_manager.get_agent_context(
            "agent_b", workflow_id
        )

        handoff_received = [
            m for m in agent_b_memories["volatile"] if "handoff_received" in m.tags
        ]

        assert len(handoff_received) > 0
        received_memory = handoff_received[0]
        assert received_memory.content["from_agent"] == "agent_a"
        assert (
            received_memory.content["input_data"]["additional_context"]["qualified"]
            is True
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
