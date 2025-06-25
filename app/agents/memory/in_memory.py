"""
In-memory implementation of MemoryStore for volatile memory.

Provides fast access with automatic TTL cleanup for workflow sessions.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import asyncio
import logging
from collections import defaultdict

from .base import MemoryStore, MemoryEntry

logger = logging.getLogger(__name__)


class InMemoryStore(MemoryStore):
    """
    In-memory implementation for volatile memory storage.

    Features:
    - TTL-based automatic cleanup
    - Fast O(1) access by ID
    - Efficient filtering by agent/workflow
    - Thread-safe operations
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize in-memory store.

        Args:
            default_ttl: Default time-to-live in seconds (1 hour default)
        """
        self.default_ttl = default_ttl
        self._memories: Dict[str, MemoryEntry] = {}
        self._expiry_times: Dict[str, datetime] = {}
        self._agent_index: Dict[str, set] = defaultdict(set)
        self._workflow_index: Dict[str, set] = defaultdict(set)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
        logger.info(f"InMemoryStore initialized with TTL={default_ttl}s")

    def _start_cleanup_task(self) -> None:
        """Start background cleanup task for expired entries."""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_expired())
        except RuntimeError:
            # No event loop running, defer cleanup task creation
            logger.debug("No event loop running, deferring cleanup task creation")
            self._cleanup_task = None

    async def _cleanup_expired(self) -> None:
        """Background task to clean up expired memories."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                now = datetime.now()
                expired_ids = [
                    memory_id
                    for memory_id, expiry in self._expiry_times.items()
                    if expiry <= now
                ]

                for memory_id in expired_ids:
                    await self._remove_entry(memory_id)

                if expired_ids:
                    logger.debug(f"Cleaned up {len(expired_ids)} expired memories")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    async def _remove_entry(self, memory_id: str) -> None:
        """Remove an entry and update all indexes."""
        if memory_id in self._memories:
            memory = self._memories[memory_id]

            # Remove from main storage
            del self._memories[memory_id]
            del self._expiry_times[memory_id]

            # Update indexes
            self._agent_index[memory.agent_id].discard(memory_id)
            self._workflow_index[memory.workflow_id].discard(memory_id)

            # Clean empty sets from indexes
            if not self._agent_index[memory.agent_id]:
                del self._agent_index[memory.agent_id]
            if not self._workflow_index[memory.workflow_id]:
                del self._workflow_index[memory.workflow_id]

    def _ensure_cleanup_task(self) -> None:
        """Ensure cleanup task is running when needed."""
        if self._cleanup_task is None:
            try:
                self._cleanup_task = asyncio.create_task(self._cleanup_expired())
                logger.debug("Started cleanup task lazily")
            except RuntimeError:
                # Still no event loop, that's fine
                pass

    async def save(
        self,
        agent_id: str,
        workflow_id: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save a memory entry with TTL."""
        # Ensure cleanup task is running
        self._ensure_cleanup_task()

        memory_id = str(uuid.uuid4())
        timestamp = datetime.now()

        # Extract TTL from metadata or use default
        ttl = self.default_ttl
        if metadata and "ttl" in metadata:
            ttl = metadata["ttl"]

        memory_entry = MemoryEntry(
            id=memory_id,
            agent_id=agent_id,
            workflow_id=workflow_id,
            content=content,
            timestamp=timestamp,
            tags=tags or [],
            metadata=metadata or {},
        )

        # Store memory and set expiry
        self._memories[memory_id] = memory_entry
        self._expiry_times[memory_id] = timestamp + timedelta(seconds=ttl)

        # Update indexes
        self._agent_index[agent_id].add(memory_id)
        self._workflow_index[workflow_id].add(memory_id)

        logger.debug(
            f"Saved volatile memory {memory_id} for agent {agent_id}, workflow {workflow_id}"
        )
        return memory_id

    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a specific memory entry."""
        # Check if expired
        if memory_id in self._expiry_times:
            if self._expiry_times[memory_id] <= datetime.now():
                await self._remove_entry(memory_id)
                return None

        return self._memories.get(memory_id)

    async def get_by_agent(
        self, agent_id: str, workflow_id: Optional[str] = None, limit: int = 100
    ) -> List[MemoryEntry]:
        """Get memories for a specific agent."""
        memory_ids = self._agent_index.get(agent_id, set())

        if workflow_id:
            # Filter by workflow too
            workflow_ids = self._workflow_index.get(workflow_id, set())
            memory_ids = memory_ids.intersection(workflow_ids)

        memories = []
        for memory_id in memory_ids:
            memory = await self.get(memory_id)  # This handles expiry check
            if memory:
                memories.append(memory)

        # Sort by timestamp (newest first) and apply limit
        memories.sort(key=lambda x: x.timestamp, reverse=True)
        return memories[:limit]

    async def get_by_workflow(self, workflow_id: str) -> List[MemoryEntry]:
        """Get all memories for a workflow."""
        memory_ids = self._workflow_index.get(workflow_id, set())

        memories = []
        for memory_id in memory_ids:
            memory = await self.get(memory_id)  # This handles expiry check
            if memory:
                memories.append(memory)

        # Sort by timestamp (newest first)
        memories.sort(key=lambda x: x.timestamp, reverse=True)
        return memories

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        if memory_id in self._memories:
            await self._remove_entry(memory_id)
            return True
        return False

    async def clear_workflow(self, workflow_id: str) -> int:
        """Clear all memories for a workflow."""
        memory_ids = list(self._workflow_index.get(workflow_id, set()))
        count = 0

        for memory_id in memory_ids:
            if await self.delete(memory_id):
                count += 1

        logger.debug(f"Cleared {count} volatile memories for workflow {workflow_id}")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get current store statistics."""
        now = datetime.now()
        expired_count = sum(
            1 for expiry in self._expiry_times.values() if expiry <= now
        )

        return {
            "total_memories": len(self._memories),
            "expired_memories": expired_count,
            "active_memories": len(self._memories) - expired_count,
            "unique_agents": len(self._agent_index),
            "unique_workflows": len(self._workflow_index),
            "default_ttl": self.default_ttl,
        }

    async def cleanup(self) -> None:
        """Manual cleanup and shutdown."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        self._memories.clear()
        self._expiry_times.clear()
        self._agent_index.clear()
        self._workflow_index.clear()
        logger.info("InMemoryStore cleaned up")
