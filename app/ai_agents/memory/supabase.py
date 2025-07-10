"""
Supabase implementation of MemoryStore for persistent memory.

Provides durable storage for long-term agent and workflow memories.
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
from supabase import Client

from .base import MemoryStore, MemoryEntry

logger = logging.getLogger(__name__)


def serialize_for_json(obj: Any) -> Any:
    """Safely serialize objects for JSON storage."""
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        # For complex objects, convert to string representation
        return str(obj)
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # Fallback to string representation for any other type
        return str(obj)


class SupabaseMemoryStore(MemoryStore):
    """
    Supabase implementation for persistent memory storage.

    Features:
    - Durable PostgreSQL storage
    - Efficient querying with indexes
    - JSON storage for flexible content
    - Transaction support for consistency
    """

    def __init__(self, supabase_client: Client, table_name: str = "agent_memories"):
        """
        Initialize Supabase memory store.

        Args:
            supabase_client: Configured Supabase client
            table_name: Name of the memories table
        """
        self.client = supabase_client
        self.table_name = table_name
        logger.info(f"SupabaseMemoryStore initialized with table '{table_name}'")

    def _dict_to_memory_entry(self, data: Dict[str, Any]) -> MemoryEntry:
        """Convert database row to MemoryEntry object."""
        return MemoryEntry(
            id=data["id"],
            agent_id=data["agent_id"],
            workflow_id=data["workflow_id"],
            content=data["content"]
            if isinstance(data["content"], dict)
            else json.loads(data["content"]),
            timestamp=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            tags=data["tags"] or [],
            metadata=data["metadata"]
            if isinstance(data["metadata"], dict)
            else json.loads(data["metadata"] or "{}"),
        )

    async def save(
        self,
        agent_id: str,
        workflow_id: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save a memory entry to Supabase."""
        memory_id = str(uuid.uuid4())

        try:
            result = (
                self.client.table(self.table_name)
                .insert(
                    {
                        "id": memory_id,
                        "agent_id": agent_id,
                        "workflow_id": workflow_id,
                        "content": serialize_for_json(content),
                        "tags": tags or [],
                        "metadata": serialize_for_json(metadata or {}),
                        "created_at": datetime.now().isoformat(),
                    }
                )
                .execute()
            )

            if result.data:
                logger.debug(
                    f"Saved persistent memory {memory_id} for agent {agent_id}, workflow {workflow_id}"
                )
                return memory_id
            else:
                raise Exception(f"Failed to save memory: {result}")

        except Exception as e:
            logger.error(f"Error saving memory to Supabase: {e}")
            raise

    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a specific memory entry."""
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("id", memory_id)
                .execute()
            )

            if result.data and len(result.data) > 0:
                return self._dict_to_memory_entry(result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error getting memory {memory_id}: {e}")
            return None

    async def get_by_agent(
        self, agent_id: str, workflow_id: Optional[str] = None, limit: int = 100
    ) -> List[MemoryEntry]:
        """Get memories for a specific agent."""
        try:
            query = (
                self.client.table(self.table_name).select("*").eq("agent_id", agent_id)
            )

            if workflow_id:
                query = query.eq("workflow_id", workflow_id)

            result = query.order("created_at", desc=True).limit(limit).execute()

            if result.data:
                return [self._dict_to_memory_entry(row) for row in result.data]
            return []

        except Exception as e:
            logger.error(f"Error getting memories for agent {agent_id}: {e}")
            return []

    async def get_by_workflow(self, workflow_id: str) -> List[MemoryEntry]:
        """Get all memories for a workflow."""
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .eq("workflow_id", workflow_id)
                .order("created_at", desc=True)
                .execute()
            )

            if result.data:
                return [self._dict_to_memory_entry(row) for row in result.data]
            return []

        except Exception as e:
            logger.error(f"Error getting memories for workflow {workflow_id}: {e}")
            return []

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        try:
            result = (
                self.client.table(self.table_name)
                .delete()
                .eq("id", memory_id)
                .execute()
            )

            if result.data and len(result.data) > 0:
                logger.debug(f"Deleted memory {memory_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return False

    async def clear_workflow(self, workflow_id: str) -> int:
        """Clear all memories for a workflow."""
        try:
            result = (
                self.client.table(self.table_name)
                .delete()
                .eq("workflow_id", workflow_id)
                .execute()
            )

            count = len(result.data) if result.data else 0
            logger.debug(
                f"Cleared {count} persistent memories for workflow {workflow_id}"
            )
            return count

        except Exception as e:
            logger.error(f"Error clearing memories for workflow {workflow_id}: {e}")
            return 0

    async def get_memories_by_tags(
        self,
        tags: List[str],
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[MemoryEntry]:
        """
        Get memories by tags (additional functionality for Supabase).

        Args:
            tags: List of tags to search for
            agent_id: Optional agent filter
            workflow_id: Optional workflow filter
            limit: Maximum results
        """
        try:
            query = self.client.table(self.table_name).select("*")

            # Use PostgreSQL array operators to find overlapping tags
            query = query.overlaps("tags", tags)

            if agent_id:
                query = query.eq("agent_id", agent_id)
            if workflow_id:
                query = query.eq("workflow_id", workflow_id)

            result = query.order("created_at", desc=True).limit(limit).execute()

            if result.data:
                return [self._dict_to_memory_entry(row) for row in result.data]
            return []

        except Exception as e:
            logger.error(f"Error getting memories by tags {tags}: {e}")
            return []

    async def search_content(
        self,
        search_term: str,
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """
        Search memories by content (uses PostgreSQL full-text search).

        Args:
            search_term: Text to search for in content
            agent_id: Optional agent filter
            workflow_id: Optional workflow filter
            limit: Maximum results
        """
        try:
            # Use PostgreSQL's JSONB operators for content search
            query = self.client.table(self.table_name).select("*")

            # Search in content JSONB field - this could be enhanced with PostgreSQL FTS
            query = query.contains("content", {"search": search_term})

            if agent_id:
                query = query.eq("agent_id", agent_id)
            if workflow_id:
                query = query.eq("workflow_id", workflow_id)

            result = query.order("created_at", desc=True).limit(limit).execute()

            if result.data:
                return [self._dict_to_memory_entry(row) for row in result.data]
            return []

        except Exception as e:
            logger.error(f"Error searching memories for '{search_term}': {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memories."""
        try:
            # Get total count - use basic select and count the results
            total_result = self.client.table(self.table_name).select("id").execute()
            total_count = total_result.count or 0

            # Get unique agents count
            agents_result = self.client.rpc(
                "count_distinct_agents", {"table_name": self.table_name}
            ).execute()
            unique_agents = agents_result.data[0] if agents_result.data else 0

            # Get unique workflows count
            workflows_result = self.client.rpc(
                "count_distinct_workflows", {"table_name": self.table_name}
            ).execute()
            unique_workflows = workflows_result.data[0] if workflows_result.data else 0

            return {
                "total_memories": total_count,
                "unique_agents": unique_agents,
                "unique_workflows": unique_workflows,
                "table_name": self.table_name,
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "total_memories": 0,
                "unique_agents": 0,
                "unique_workflows": 0,
                "table_name": self.table_name,
                "error": str(e),
            }
