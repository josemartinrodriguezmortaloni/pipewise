"""
Handoff callback system for PipeWise agents.

Implements the on_handoff pattern from OpenAI Agent SDK to track
communication and results between agents.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel
import logging

from agents import RunContextWrapper
from ..memory import MemoryManager

logger = logging.getLogger(__name__)


class HandoffData(BaseModel):
    """Data structure for handoff input and results."""

    reason: str
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    additional_context: Optional[Dict[str, Any]] = None


class HandoffResult(BaseModel):
    """Result from a handoff operation."""

    handoff_id: str
    from_agent: str
    to_agent: str
    timestamp: datetime
    input_data: Optional[HandoffData]
    success: bool
    result_summary: str
    execution_time_ms: int
    memory_entries: Dict[str, str]  # volatile_id, persistent_id


def create_handoff_callback(
    memory_manager: MemoryManager,
    from_agent_id: str,
    to_agent_id: str,
    workflow_id: str,
    tenant_context: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    Create a handoff callback function for a specific agent transition.

    Following the OpenAI Agent SDK pattern for on_handoff callbacks.

    Args:
        memory_manager: Memory manager for storing handoff data
        from_agent_id: Source agent identifier
        to_agent_id: Target agent identifier
        workflow_id: Current workflow session ID
        tenant_context: Optional tenant context data

    Returns:
        Configured callback function for use in handoff()
    """

    async def on_handoff(
        ctx: RunContextWrapper, input_data: Optional[HandoffData] = None
    ) -> HandoffResult:
        """
        Callback executed when handoff is invoked.

        This function:
        1. Logs the handoff event
        2. Stores handoff data in both volatile and persistent memory
        3. Updates workflow context
        4. Returns structured result for coordinator

        Args:
            ctx: OpenAI Agent SDK run context
            input_data: Optional handoff input data from LLM

        Returns:
            HandoffResult with execution details
        """
        start_time = datetime.now()
        handoff_id = str(uuid.uuid4())

        try:
            logger.info(
                f"🔄 Handoff {handoff_id}: {from_agent_id} → {to_agent_id} "
                f"(workflow: {workflow_id})"
            )

            # Prepare handoff content for memory storage
            handoff_content = {
                "handoff_id": handoff_id,
                "from_agent": from_agent_id,
                "to_agent": to_agent_id,
                "workflow_id": workflow_id,
                "timestamp": start_time.isoformat(),
                "input_data": input_data.model_dump() if input_data else None,
                "context_summary": f"Handoff from {from_agent_id} to {to_agent_id}",
                "tenant_context": tenant_context,
            }

            # Store in both volatile (for workflow session) and persistent (for history)
            memory_results = await memory_manager.save_both(
                agent_id=from_agent_id,  # Handoff is attributed to source agent
                workflow_id=workflow_id,
                content=handoff_content,
                tags=["handoff", "transition", f"to_{to_agent_id}"],
                metadata={
                    "type": "handoff",
                    "handoff_id": handoff_id,
                    "target_agent": to_agent_id,
                    "priority": input_data.priority if input_data else "normal",
                },
            )

            # Also store a copy for the target agent (for context retrieval)
            await memory_manager.save_volatile(
                agent_id=to_agent_id,
                workflow_id=workflow_id,
                content={
                    **handoff_content,
                    "role": "handoff_received",
                    "from_agent": from_agent_id,
                },
                tags=["handoff_received", "context", f"from_{from_agent_id}"],
            )

            end_time = datetime.now()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            result = HandoffResult(
                handoff_id=handoff_id,
                from_agent=from_agent_id,
                to_agent=to_agent_id,
                timestamp=start_time,
                input_data=input_data,
                success=True,
                result_summary=f"Successfully handed off from {from_agent_id} to {to_agent_id}",
                execution_time_ms=execution_time,
                memory_entries=memory_results,
            )

            logger.info(
                f"✅ Handoff {handoff_id} completed in {execution_time}ms: "
                f"{result.result_summary}"
            )

            return result

        except Exception as e:
            end_time = datetime.now()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            error_result = HandoffResult(
                handoff_id=handoff_id,
                from_agent=from_agent_id,
                to_agent=to_agent_id,
                timestamp=start_time,
                input_data=input_data,
                success=False,
                result_summary=f"Handoff failed: {str(e)}",
                execution_time_ms=execution_time,
                memory_entries={},
            )

            logger.error(
                f"❌ Handoff {handoff_id} failed after {execution_time}ms: {e}"
            )

            # Store error in memory for debugging
            try:
                await memory_manager.save_persistent(
                    agent_id=from_agent_id,
                    workflow_id=workflow_id,
                    content={
                        "handoff_id": handoff_id,
                        "error": str(e),
                        "from_agent": from_agent_id,
                        "to_agent": to_agent_id,
                        "timestamp": start_time.isoformat(),
                    },
                    tags=["handoff_error", "error"],
                    metadata={"type": "handoff_error", "handoff_id": handoff_id},
                )
            except Exception as memory_error:
                logger.error(f"Failed to store handoff error in memory: {memory_error}")

            return error_result

    return on_handoff


def create_workflow_handoff_tracker(
    memory_manager: MemoryManager, workflow_id: str
) -> Dict[str, Any]:
    """
    Create a workflow-level handoff tracker.

    Tracks all handoffs within a workflow for analytics and debugging.

    Args:
        memory_manager: Memory manager instance
        workflow_id: Workflow session identifier

    Returns:
        Dictionary with tracking functions and state
    """

    handoff_count = 0
    start_time = datetime.now()

    async def track_handoff(handoff_result: HandoffResult) -> None:
        """Track a handoff result at workflow level."""
        nonlocal handoff_count
        handoff_count += 1

        await memory_manager.save_volatile(
            agent_id="workflow_coordinator",
            workflow_id=workflow_id,
            content={
                "handoff_sequence": handoff_count,
                "handoff_result": handoff_result.model_dump(),
                "workflow_elapsed_time": (datetime.now() - start_time).total_seconds(),
            },
            tags=["workflow_tracking", "handoff_sequence"],
        )

        logger.debug(
            f"📊 Workflow {workflow_id}: Tracked handoff #{handoff_count} "
            f"({handoff_result.from_agent} → {handoff_result.to_agent})"
        )

    async def get_handoff_summary() -> Dict[str, Any]:
        """Get summary of all handoffs in the workflow."""
        workflow_memories = await memory_manager.get_workflow_context(workflow_id)

        handoff_memories = [
            memory
            for memory in workflow_memories["volatile"]
            if "handoff" in memory.tags
        ]

        return {
            "workflow_id": workflow_id,
            "total_handoffs": handoff_count,
            "handoff_chain": [
                f"{m.content.get('from_agent', 'unknown')} → {m.content.get('to_agent', 'unknown')}"
                for m in handoff_memories
                if m.content.get("type") == "handoff"
            ],
            "total_workflow_time": (datetime.now() - start_time).total_seconds(),
            "start_time": start_time.isoformat(),
        }

    return {
        "track_handoff": track_handoff,
        "get_summary": get_handoff_summary,
        "workflow_id": workflow_id,
        "start_time": start_time,
    }
