"""
Agent Configuration API Endpoints

FastAPI routes for managing AI agent configurations and custom prompts.
Following multi-tenant architecture patterns.

NOTE: This file is temporarily simplified for Supabase migration.
All endpoints return mock data and will be reimplemented with Supabase client.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import JSONResponse

from app.core.dependencies import get_current_tenant, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.agent_schema import (
    AgentPromptCreate,
    AgentPromptUpdate,
    AgentPromptResponse,
    AgentOverviewResponse,
    AgentListResponse,
    PromptTestRequest,
    PromptTestResponse,
    AgentTypeEnum,
)

router = APIRouter(prefix="/agents", tags=["agent-configuration"])


# Agent Prompt Endpoints
@router.get("/prompts", response_model=List[AgentPromptResponse])
async def list_prompts(
    agent_type: Optional[AgentTypeEnum] = Query(
        None, description="Filter by agent type"
    ),
    active_only: bool = Query(True, description="Return only active prompts"),
    tenant: Tenant = Depends(get_current_tenant),
):
    """List all prompts for the current tenant."""
    # Mock response for now
    mock_prompts = [
        AgentPromptResponse(
            id=uuid4(),
            tenant_id=uuid4(),
            agent_type=AgentTypeEnum.LEAD_GENERATOR,  # Changed from LEAD_QUALIFIER
            prompt_name="Default Lead Generator",  # Updated name
            prompt_content="You are an expert lead generation agent...",  # Updated content
            is_active=True,
            is_default=True,
            version=1,
            created_by=uuid4(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_modified="2024-01-15",
        )
    ]

    if agent_type:
        mock_prompts = [p for p in mock_prompts if p.agent_type == agent_type]

    return mock_prompts


@router.post(
    "/prompts", response_model=AgentPromptResponse, status_code=status.HTTP_201_CREATED
)
async def create_prompt(
    prompt_data: AgentPromptCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
):
    """Create a new custom prompt."""
    # Mock response
    return AgentPromptResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        agent_type=prompt_data.agent_type,
        prompt_name=prompt_data.prompt_name,
        prompt_content=prompt_data.prompt_content,
        is_active=prompt_data.is_active,
        is_default=prompt_data.is_default,
        version=1,
        created_by=uuid4(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        last_modified=datetime.now().strftime("%Y-%m-%d"),
    )


@router.get("/prompts/{prompt_id}", response_model=AgentPromptResponse)
async def get_prompt(prompt_id: UUID, tenant: Tenant = Depends(get_current_tenant)):
    """Get a specific prompt by ID."""
    # Mock response
    return AgentPromptResponse(
        id=prompt_id,
        tenant_id=uuid4(),
        agent_type=AgentTypeEnum.LEAD_GENERATOR,
        prompt_name="Lead Generator Prompt",
        prompt_content="You are an expert lead generation agent...",
        is_active=True,
        is_default=True,
        version=1,
        created_by=uuid4(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        last_modified="2024-01-15",
    )


@router.put("/prompts/{prompt_id}", response_model=AgentPromptResponse)
async def update_prompt(
    prompt_id: UUID,
    updates: AgentPromptUpdate,
    tenant: Tenant = Depends(get_current_tenant),
):
    """Update an existing prompt."""
    # Mock response
    return AgentPromptResponse(
        id=prompt_id,
        tenant_id=uuid4(),
        agent_type=AgentTypeEnum.LEAD_GENERATOR,
        prompt_name=updates.prompt_name or "Updated Prompt",
        prompt_content=updates.prompt_content or "Updated content...",
        is_active=updates.is_active if updates.is_active is not None else True,
        is_default=True,
        version=2,
        created_by=uuid4(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        last_modified=datetime.now().strftime("%Y-%m-%d"),
    )


@router.post("/prompts/{prompt_id}/activate")
async def activate_prompt(
    prompt_id: UUID, tenant: Tenant = Depends(get_current_tenant)
):
    """Activate a prompt and deactivate others of the same type."""
    return {"success": True, "message": f"Prompt {prompt_id} activated successfully"}


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: UUID, tenant: Tenant = Depends(get_current_tenant)):
    """Delete a prompt."""
    return {"success": True, "message": "Prompt deleted successfully"}


# Agent Overview Endpoints
@router.get("/overview", response_model=AgentListResponse)
async def get_agents_overview(tenant: Tenant = Depends(get_current_tenant)):
    """Get overview of all agents with their current configurations."""

    # Mock agent configurations
    mock_agents = [
        AgentOverviewResponse(
            id="lead_generator",  # Changed from lead_qualifier
            name="Lead Generator",  # Changed name
            description="Generates qualified leads from conversation data",  # Updated description
            status="active",
            category="Lead Management",
            current_prompt="Enhanced lead generation with advanced qualification criteria",  # Updated
            default_prompt="Standard lead generation prompt",  # Updated
            last_modified="2024-12-08",
            performance={
                "success_rate": 92.0,
                "total_processed": 847,
                "avg_response_time": 850,
                "qualification_accuracy": 88.5,
            },
        ),
        AgentOverviewResponse(
            id="outbound_contact",
            name="Outbound Contact",
            description="Creates personalized outreach messages for qualified leads",
            status="active",
            category="outbound",
            current_prompt="You are a professional outbound sales agent for PipeWise...",
            default_prompt="You are a professional outbound sales agent for PipeWise...",
            last_modified="2024-01-15",
            performance={
                "successRate": 34,
                "avgResponseTime": "2.1s",
                "totalProcessed": 892,
            },
        ),
        AgentOverviewResponse(
            id="meeting_scheduler",
            name="Meeting Scheduler",
            description="Handles meeting coordination and calendar management",
            status="active",
            category="scheduling",
            current_prompt="You are a professional meeting scheduler for PipeWise...",
            default_prompt="You are a professional meeting scheduler for PipeWise...",
            last_modified="2024-01-15",
            performance={
                "successRate": 92,
                "avgResponseTime": "0.8s",
                "totalProcessed": 456,
            },
        ),
        AgentOverviewResponse(
            id="whatsapp_agent",
            name="WhatsApp Agent",
            description="Manages WhatsApp Business communications and lead engagement",
            status="active",
            category="communication",
            current_prompt="You are a WhatsApp Business communication agent for PipeWise...",
            default_prompt="You are a WhatsApp Business communication agent for PipeWise...",
            last_modified="2024-01-15",
            performance={
                "successRate": 78,
                "avgResponseTime": "0.5s",
                "totalProcessed": 2341,
            },
        ),
    ]

    total_processed = sum(agent.performance["totalProcessed"] for agent in mock_agents)
    avg_success_rate = sum(
        agent.performance["successRate"] for agent in mock_agents
    ) / len(mock_agents)

    return AgentListResponse(
        agents=mock_agents,
        total=len(mock_agents),
        active_count=len(mock_agents),
        avg_success_rate=round(avg_success_rate, 1),
        total_processed=total_processed,
    )


# Prompt Testing Endpoint
@router.post("/test-prompt", response_model=PromptTestResponse)
async def test_prompt(
    test_request: PromptTestRequest, tenant: Tenant = Depends(get_current_tenant)
):
    """Test a prompt with sample data."""
    import time

    start_time = time.time()

    try:
        # Basic validation
        if len(test_request.prompt_content.strip()) < 10:
            return PromptTestResponse(
                success=False,
                test_type=test_request.test_type,
                execution_time_ms=int((time.time() - start_time) * 1000),
                result={},
                errors=["Prompt content is too short (minimum 10 characters)"],
            )

        # Simulate prompt execution
        import asyncio

        await asyncio.sleep(0.5)  # Simulate processing time

        # Mock successful test result
        test_result = {
            "validation": "passed",
            "prompt_length": len(test_request.prompt_content),
            "estimated_tokens": len(test_request.prompt_content.split()) * 1.3,
            "readability_score": 85,
            "agent_type": test_request.agent_type,
            "sample_output": "Mock response from agent based on the provided prompt...",
        }

        execution_time = int((time.time() - start_time) * 1000)

        return PromptTestResponse(
            success=True,
            test_type=test_request.test_type,
            execution_time_ms=execution_time,
            result=test_result,
            suggestions=[
                "Consider adding more specific instructions for edge cases",
                "You might want to include examples of desired output format",
            ],
        )

    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        return PromptTestResponse(
            success=False,
            test_type=test_request.test_type,
            execution_time_ms=execution_time,
            result={},
            errors=[f"Test execution failed: {str(e)}"],
        )


# Performance Metrics Endpoints (simplified)
@router.get("/metrics/{agent_type}")
async def get_agent_metrics(
    agent_type: AgentTypeEnum,
    days: int = Query(
        30, ge=1, le=365, description="Number of days of metrics to retrieve"
    ),
    tenant: Tenant = Depends(get_current_tenant),
):
    """Get performance metrics for a specific agent type."""
    # Mock metrics response
    mock_metrics = [
        {
            "id": str(uuid4()),
            "tenant_id": tenant.id,
            "agent_type": agent_type,
            "date": datetime.now().isoformat(),
            "total_processed": 100,
            "successful_executions": 85,
            "failed_executions": 15,
            "success_rate": 85.0,
            "avg_response_time_ms": 1200,
            "custom_metrics": {},
        }
    ]

    return mock_metrics
