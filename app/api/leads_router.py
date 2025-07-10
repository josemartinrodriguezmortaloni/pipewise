"""
Leads Router for PipeWise API
Handles lead processing requests from the frontend
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import asyncio
from datetime import datetime

# Import our agents system
from app.ai_agents.agents import ModernAgents, TenantContext
from app.ai_agents.memory import MemoryManager, InMemoryStore, SupabaseMemoryStore
from app.supabase.supabase_client import SupabaseCRMClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["leads"])


class LeadProcessRequest(BaseModel):
    """Request model for lead processing"""

    workflow_type: str = "single_lead"
    email: str
    name: str
    company: Optional[str] = ""
    phone: Optional[str] = ""
    message: Optional[str] = ""
    force_real_workflow: bool = True
    debug_mode: bool = False
    prospect_list: Optional[list] = None


@router.post("/process-lead")
async def process_lead(request: LeadProcessRequest):
    """
    Process a lead using our AI agents system.
    This endpoint is called by the frontend to trigger agent workflows.
    """
    try:
        logger.info(f"🔧 Processing lead request: {request.name} ({request.email})")

        # Create memory system for agents
        db_client = SupabaseCRMClient()
        volatile_store = InMemoryStore(default_ttl=3600)  # 1 hour TTL
        persistent_store = SupabaseMemoryStore(db_client.client)
        memory_manager = MemoryManager(volatile_store, persistent_store)

        # Create tenant context
        tenant_context = TenantContext(
            tenant_id="frontend_request",
            user_id=f"frontend_user_{int(datetime.now().timestamp())}",
            is_premium=False,
            api_limits={"calls_per_hour": 100},
            features_enabled=[
                "basic_qualification",
                "meeting_scheduling",
                "communication",
            ],
            memory_manager=memory_manager,
        )

        # Initialize modern agents
        agents = ModernAgents(tenant_context)

        # Prepare lead data for processing
        lead_data = {
            "name": request.name,
            "email": request.email,
            "company": request.company or "",
            "phone": request.phone or "",
            "message": request.message or "",
            "source": "frontend_api",
            "workflow_type": request.workflow_type,
            "debug_mode": request.debug_mode,
            "force_real_workflow": request.force_real_workflow,
        }

        # Add prospect list if provided (for outreach workflows)
        if request.prospect_list:
            lead_data["prospect_list"] = request.prospect_list
            lead_data["workflow_type"] = "prospect_list"

        logger.info(f"🚀 Starting agent workflow for: {request.name}")

        # Run the agent workflow
        result = await agents.run_workflow(lead_data)

        logger.info(f"✅ Workflow completed: {result.get('status', 'unknown')}")

        # Return formatted response
        return {
            "success": True,
            "workflow_id": result.get("workflow_id", "unknown"),
            "status": result.get("status", "completed"),
            "lead_id": result.get("lead_id", request.email),
            "workflow_type": result.get("workflow_type", request.workflow_type),
            "agents_used": result.get("agents_used", []),
            "mcp_servers_available": result.get("mcp_servers_available", 0),
            "mcp_servers_connected": result.get("mcp_servers_connected", 0),
            "message": "Lead processed successfully by AI agents",
            "result": result.get("result", "Workflow completed"),
            "debug_info": result.get("debug_info", {}) if request.debug_mode else None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error processing lead: {e}", exc_info=True)

        # Return error response
        error_response = {
            "success": False,
            "error": str(e),
            "message": "Failed to process lead",
            "timestamp": datetime.now().isoformat(),
        }

        # Add debug info if enabled
        if request.debug_mode:
            error_response["debug_info"] = {
                "error_type": type(e).__name__,
                "request_data": request.dict(),
            }

        raise HTTPException(status_code=500, detail=error_response)


@router.get("/health")
async def health_check():
    """Health check endpoint for the leads API"""
    return {
        "status": "healthy",
        "service": "leads_processor",
        "timestamp": datetime.now().isoformat(),
    }
