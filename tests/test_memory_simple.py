"""
Simple test to validate the memory system functionality.
"""

import pytest
from unittest.mock import Mock

from app.agents.memory import MemoryManager, InMemoryStore, SupabaseMemoryStore


@pytest.mark.asyncio
async def test_volatile_memory_basic():
    """Test basic volatile memory functionality."""
    # Create in-memory store
    volatile_store = InMemoryStore(default_ttl=300)

    # Mock persistent store
    mock_client = Mock()
    persistent_store = SupabaseMemoryStore(mock_client)

    # Create memory manager
    memory_manager = MemoryManager(volatile_store, persistent_store)

    # Test saving to volatile memory
    memory_id = await memory_manager.save_volatile(
        agent_id="test_agent",
        workflow_id="test_workflow",
        content={"message": "test", "value": 42},
        tags=["test"],
    )

    assert memory_id is not None

    # Test retrieval
    context = await memory_manager.get_agent_context("test_agent", "test_workflow")

    assert len(context["volatile"]) == 1
    assert context["volatile"][0].content["message"] == "test"
    assert context["volatile"][0].content["value"] == 42


def test_memory_imports():
    """Test that all memory components can be imported."""
    from app.agents.memory import (
        MemoryStore,
        MemoryManager,
        InMemoryStore,
        SupabaseMemoryStore,
    )
    from app.agents.callbacks import create_handoff_callback, HandoffData
    from app.agents.agents import create_agents_with_memory, ModernAgents, TenantContext

    assert MemoryStore is not None
    assert MemoryManager is not None
    assert InMemoryStore is not None
    assert SupabaseMemoryStore is not None
    assert create_handoff_callback is not None
    assert HandoffData is not None
    assert create_agents_with_memory is not None
    assert ModernAgents is not None
    assert TenantContext is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
