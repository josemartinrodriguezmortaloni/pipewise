"""
Base interfaces and classes for the dual memory system.

Defines MemoryStore interface and MemoryManager coordinator.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Individual memory entry with metadata."""

    id: str
    agent_id: str
    workflow_id: str
    content: Dict[str, Any]
    timestamp: datetime
    tags: List[str]
    metadata: Dict[str, Any]


class MemoryStore(ABC):
    """Abstract interface for memory storage implementations."""

    @abstractmethod
    async def save(
        self,
        agent_id: str,
        workflow_id: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save a memory entry.

        Args:
            agent_id: Unique agent identifier
            workflow_id: Workflow session identifier
            content: Memory content data
            tags: Optional tags for categorization
            metadata: Additional metadata

        Returns:
            str: Memory entry ID
        """
        pass

    @abstractmethod
    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve a specific memory entry.

        Args:
            memory_id: Memory entry identifier

        Returns:
            MemoryEntry or None if not found
        """
        pass

    @abstractmethod
    async def get_by_agent(
        self, agent_id: str, workflow_id: Optional[str] = None, limit: int = 100
    ) -> List[MemoryEntry]:
        """
        Get memories for a specific agent.

        Args:
            agent_id: Agent identifier
            workflow_id: Optional workflow filter
            limit: Maximum number of entries

        Returns:
            List of memory entries
        """
        pass

    @abstractmethod
    async def get_by_workflow(self, workflow_id: str) -> List[MemoryEntry]:
        """
        Get all memories for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            List of memory entries
        """
        pass

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """
        Delete a memory entry.

        Args:
            memory_id: Memory entry identifier

        Returns:
            bool: True if deleted successfully
        """
        pass

    @abstractmethod
    async def clear_workflow(self, workflow_id: str) -> int:
        """
        Clear all memories for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            int: Number of entries deleted
        """
        pass


class MemoryManager:
    """
    Coordinates between volatile and persistent memory stores.

    Manages the dual memory system for agents and workflows.
    """

    def __init__(self, volatile_store: MemoryStore, persistent_store: MemoryStore):
        """
        Initialize memory manager.

        Args:
            volatile_store: In-memory store for workflow sessions
            persistent_store: Persistent store for long-term data
        """
        self.volatile = volatile_store
        self.persistent = persistent_store
        logger.info("MemoryManager initialized with dual storage")

    async def save_volatile(
        self,
        agent_id: str,
        workflow_id: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Save to volatile memory only.

        Used for temporary workflow data that doesn't need persistence.
        """
        return await self.volatile.save(
            agent_id=agent_id,
            workflow_id=workflow_id,
            content=content,
            tags=tags or [],
            metadata={"type": "volatile"},
        )

    async def save_persistent(
        self,
        agent_id: str,
        workflow_id: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save to persistent memory only.

        Used for long-term data that should be preserved across sessions.
        """
        return await self.persistent.save(
            agent_id=agent_id,
            workflow_id=workflow_id,
            content=content,
            tags=tags or [],
            metadata=metadata or {"type": "persistent"},
        )

    async def save_both(
        self,
        agent_id: str,
        workflow_id: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Save to both volatile and persistent memory.

        Returns:
            Dict with 'volatile_id' and 'persistent_id' keys
        """
        volatile_id = await self.save_volatile(agent_id, workflow_id, content, tags)
        persistent_id = await self.save_persistent(
            agent_id, workflow_id, content, tags, metadata
        )

        return {"volatile_id": volatile_id, "persistent_id": persistent_id}

    async def get_agent_context(
        self, agent_id: str, workflow_id: str
    ) -> Dict[str, List[MemoryEntry]]:
        """
        Get complete memory context for an agent in a workflow.

        Returns both volatile and persistent memories.
        """
        volatile_memories = await self.volatile.get_by_agent(agent_id, workflow_id)
        persistent_memories = await self.persistent.get_by_agent(agent_id, workflow_id)

        return {"volatile": volatile_memories, "persistent": persistent_memories}

    async def get_workflow_context(
        self, workflow_id: str
    ) -> Dict[str, List[MemoryEntry]]:
        """
        Get complete memory context for a workflow.

        Returns memories from all agents in the workflow.
        """
        volatile_memories = await self.volatile.get_by_workflow(workflow_id)
        persistent_memories = await self.persistent.get_by_workflow(workflow_id)

        return {"volatile": volatile_memories, "persistent": persistent_memories}

    async def clear_workflow_volatile(self, workflow_id: str) -> int:
        """Clear volatile memories for a workflow (end of session)."""
        return await self.volatile.clear_workflow(workflow_id)

    async def archive_workflow(self, workflow_id: str) -> Dict[str, int]:
        """
        Archive workflow: move volatile to persistent and clear volatile.

        Returns:
            Dict with counts of archived and cleared entries
        """
        volatile_memories = await self.volatile.get_by_workflow(workflow_id)
        archived_count = 0

        # Move volatile memories to persistent with archive metadata
        for memory in volatile_memories:
            await self.persistent.save(
                agent_id=memory.agent_id,
                workflow_id=memory.workflow_id,
                content=memory.content,
                tags=memory.tags + ["archived"],
                metadata={
                    **memory.metadata,
                    "archived_from": "volatile",
                    "archived_at": datetime.now().isoformat(),
                },
            )
            archived_count += 1

        # Clear volatile memories
        cleared_count = await self.volatile.clear_workflow(workflow_id)

        logger.info(
            f"Archived workflow {workflow_id}: {archived_count} entries moved, {cleared_count} cleared"
        )

        return {"archived": archived_count, "cleared": cleared_count}


class TestInMemoryStore(MemoryStore):
    """
    Simple in-memory implementation for testing purposes.

    No TTL, no background tasks, just basic storage for tests.
    """

    def __init__(self) -> None:
        """Initialize test memory store."""
        self._memories: Dict[str, MemoryEntry] = {}
        self._counter = 0

    async def save(
        self,
        agent_id: str,
        workflow_id: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save a memory entry."""
        self._counter += 1
        memory_id = f"test_memory_{self._counter}"

        memory_entry = MemoryEntry(
            id=memory_id,
            agent_id=agent_id,
            workflow_id=workflow_id,
            content=content,
            timestamp=datetime.now(),
            tags=tags or [],
            metadata=metadata or {},
        )

        self._memories[memory_id] = memory_entry
        return memory_id

    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a specific memory entry."""
        return self._memories.get(memory_id)

    async def get_by_agent(
        self, agent_id: str, workflow_id: Optional[str] = None, limit: int = 100
    ) -> List[MemoryEntry]:
        """Get memories for a specific agent."""
        memories = [
            memory
            for memory in self._memories.values()
            if memory.agent_id == agent_id
            and (workflow_id is None or memory.workflow_id == workflow_id)
        ]
        return memories[:limit]

    async def get_by_workflow(self, workflow_id: str) -> List[MemoryEntry]:
        """Get all memories for a workflow."""
        return [
            memory
            for memory in self._memories.values()
            if memory.workflow_id == workflow_id
        ]

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False

    async def clear_workflow(self, workflow_id: str) -> int:
        """Clear all memories for a workflow."""
        to_delete = [
            memory_id
            for memory_id, memory in self._memories.items()
            if memory.workflow_id == workflow_id
        ]

        for memory_id in to_delete:
            del self._memories[memory_id]

        return len(to_delete)
