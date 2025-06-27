"""
Agent handoff system for passing context and data between agents.
"""

from typing import Dict, Any, Optional, Callable, Awaitable
from pydantic import BaseModel, ConfigDict
from .base import MemoryManager
import logging

logger = logging.getLogger(__name__)


class HandoffData(BaseModel):
    """Data structure for agent handoff information."""

    reason: str
    priority: str = "medium"
    additional_context: Optional[Dict[str, Any]] = None


async def create_handoff_callback(
    memory_manager: MemoryManager,
    from_agent_id: str,
    to_agent_id: str,
    workflow_id: str,
) -> Callable[[Any, HandoffData], Awaitable[Dict[str, Any]]]:
    """
    Create a handoff callback function for agent transitions.

    Args:
        memory_manager: Memory manager instance
        from_agent_id: ID of the source agent
        to_agent_id: ID of the target agent
        workflow_id: Current workflow ID

    Returns:
        Async callback function for handoffs
    """

    async def handoff_callback(ctx: Any, handoff_data: HandoffData) -> Dict[str, Any]:
        """Execute the handoff between agents."""
        try:
            # Store handoff information in memory
            handoff_memory = {
                "from_agent": from_agent_id,
                "to_agent": to_agent_id,
                "reason": handoff_data.reason,
                "priority": handoff_data.priority,
                "context": handoff_data.additional_context or {},
                "timestamp": "now()",
            }

            await memory_manager.save_volatile(
                agent_id=from_agent_id,
                workflow_id=workflow_id,
                content=handoff_memory,
                tags=["handoff", f"to_{to_agent_id}"],
            )

            logger.info(
                f"Handoff executed: {from_agent_id} -> {to_agent_id}, reason: {handoff_data.reason}"
            )

            return {
                "status": "handoff_completed",
                "from_agent": from_agent_id,
                "to_agent": to_agent_id,
                "reason": handoff_data.reason,
            }

        except Exception as e:
            logger.error(f"Handoff failed: {e}")
            return {"status": "handoff_failed", "error": str(e)}

    return handoff_callback
