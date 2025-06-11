"""
Agent Configuration API Endpoints

FastAPI routes for managing AI agent configurations and custom prompts.
Following multi-tenant architecture patterns.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db, get_current_tenant, get_current_user
from app.models.agent_config import AgentPrompt, AgentConfiguration, AgentPerformanceMetrics, AgentType
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.agent_schema import (
    AgentPromptCreate, AgentPromptUpdate, AgentPromptResponse,
    AgentConfigurationCreate, AgentConfigurationUpdate, AgentConfigurationResponse,
    AgentPerformanceMetricsResponse, AgentOverviewResponse, AgentListResponse,
    PromptTestRequest, PromptTestResponse, BulkPromptUpdate, BulkOperationResponse,
    AgentStatusUpdate, AgentStatusResponse, AgentTypeEnum
)

router = APIRouter(prefix="/agents", tags=["agent-configuration"])


# Agent Prompt Endpoints
@router.get("/prompts", response_model=List[AgentPromptResponse])
async def list_prompts(
    agent_type: Optional[AgentTypeEnum] = Query(None, description="Filter by agent type"),
    active_only: bool = Query(True, description="Return only active prompts"),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    """List all prompts for the current tenant."""
    query = select(AgentPrompt).where(AgentPrompt.tenant_id == tenant.id)
    
    if agent_type:
        query = query.where(AgentPrompt.agent_type == agent_type)
    
    if active_only:
        query = query.where(AgentPrompt.is_active == True)
    
    query = query.order_by(AgentPrompt.agent_type, AgentPrompt.created_at.desc())
    
    result = await db.execute(query)
    prompts = result.scalars().all()
    
    return [
        AgentPromptResponse(
            **prompt.__dict__,
            last_modified=prompt.updated_at.strftime('%Y-%m-%d')
        )
        for prompt in prompts
    ]


@router.post("/prompts", response_model=AgentPromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt_data: AgentPromptCreate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user)
):
    """Create a new custom prompt."""
    # Check if this is the first prompt for this agent type (make it default)
    existing_query = select(AgentPrompt).where(
        and_(
            AgentPrompt.tenant_id == tenant.id,
            AgentPrompt.agent_type == prompt_data.agent_type
        )
    )
    existing_result = await db.execute(existing_query)
    existing_prompts = existing_result.scalars().all()
    
    is_first_prompt = len(existing_prompts) == 0
    
    new_prompt = AgentPrompt(
        tenant_id=tenant.id,
        agent_type=prompt_data.agent_type,
        prompt_name=prompt_data.prompt_name,
        prompt_content=prompt_data.prompt_content,
        is_active=prompt_data.is_active,
        is_default=prompt_data.is_default or is_first_prompt,
        created_by=user.id
    )
    
    # If this is being set as default, deactivate other defaults
    if new_prompt.is_default:
        await db.execute(
            select(AgentPrompt)
            .where(
                and_(
                    AgentPrompt.tenant_id == tenant.id,
                    AgentPrompt.agent_type == prompt_data.agent_type,
                    AgentPrompt.is_default == True
                )
            )
        )
        for prompt in existing_prompts:
            if prompt.is_default:
                prompt.is_default = False
    
    db.add(new_prompt)
    await db.commit()
    await db.refresh(new_prompt)
    
    return AgentPromptResponse(
        **new_prompt.__dict__,
        last_modified=new_prompt.updated_at.strftime('%Y-%m-%d')
    )


@router.get("/prompts/{prompt_id}", response_model=AgentPromptResponse)
async def get_prompt(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get a specific prompt by ID."""
    query = select(AgentPrompt).where(
        and_(
            AgentPrompt.id == prompt_id,
            AgentPrompt.tenant_id == tenant.id
        )
    )
    
    result = await db.execute(query)
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    
    return AgentPromptResponse(
        **prompt.__dict__,
        last_modified=prompt.updated_at.strftime('%Y-%m-%d')
    )


@router.put("/prompts/{prompt_id}", response_model=AgentPromptResponse)
async def update_prompt(
    prompt_id: UUID,
    updates: AgentPromptUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Update an existing prompt."""
    query = select(AgentPrompt).where(
        and_(
            AgentPrompt.id == prompt_id,
            AgentPrompt.tenant_id == tenant.id
        )
    )
    
    result = await db.execute(query)
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    
    # Update fields
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prompt, field, value)
    
    # Increment version
    prompt.version += 1
    
    await db.commit()
    await db.refresh(prompt)
    
    return AgentPromptResponse(
        **prompt.__dict__,
        last_modified=prompt.updated_at.strftime('%Y-%m-%d')
    )


@router.post("/prompts/{prompt_id}/activate")
async def activate_prompt(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Activate a prompt and deactivate others of the same type."""
    query = select(AgentPrompt).where(
        and_(
            AgentPrompt.id == prompt_id,
            AgentPrompt.tenant_id == tenant.id
        )
    )
    
    result = await db.execute(query)
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    
    # Deactivate all other prompts of the same type
    other_prompts_query = select(AgentPrompt).where(
        and_(
            AgentPrompt.tenant_id == tenant.id,
            AgentPrompt.agent_type == prompt.agent_type,
            AgentPrompt.id != prompt_id
        )
    )
    
    other_result = await db.execute(other_prompts_query)
    other_prompts = other_result.scalars().all()
    
    for other_prompt in other_prompts:
        other_prompt.is_active = False
        other_prompt.is_default = False
    
    # Activate and set as default
    prompt.is_active = True
    prompt.is_default = True
    
    await db.commit()
    
    return {"success": True, "message": f"Prompt {prompt.prompt_name} activated successfully"}


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Delete a prompt."""
    query = select(AgentPrompt).where(
        and_(
            AgentPrompt.id == prompt_id,
            AgentPrompt.tenant_id == tenant.id
        )
    )
    
    result = await db.execute(query)
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    
    # Don't allow deletion of the last remaining prompt for an agent type
    count_query = select(func.count(AgentPrompt.id)).where(
        and_(
            AgentPrompt.tenant_id == tenant.id,
            AgentPrompt.agent_type == prompt.agent_type
        )
    )
    
    count_result = await db.execute(count_query)
    prompt_count = count_result.scalar()
    
    if prompt_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last prompt for this agent type"
        )
    
    await db.delete(prompt)
    await db.commit()
    
    return {"success": True, "message": "Prompt deleted successfully"}


# Agent Overview Endpoints
@router.get("/overview", response_model=AgentListResponse)
async def get_agents_overview(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get overview of all agents with their current configurations."""
    
    # Default agent configurations
    default_agents = [
        {
            "id": "lead_qualifier",
            "name": "Lead Qualifier",
            "description": "Analyzes and scores incoming leads based on your criteria",
            "status": "active",
            "category": "qualification",
            "default_prompt": """You are an expert lead qualification agent for PipeWise. Your role is to analyze incoming leads and determine their quality and potential value.

Analyze each lead based on:
1. Company size and industry relevance
2. Budget indicators and decision-making authority
3. Timeline and urgency signals
4. Engagement level and interest indicators

Provide a qualification score from 1-100 and categorize as:
- Hot (80-100): Ready to buy, high intent
- Warm (60-79): Interested, needs nurturing
- Cold (40-59): Low priority, long-term
- Unqualified (0-39): Not a good fit

Return your analysis in a structured format with reasoning."""
        },
        {
            "id": "outbound_contact",
            "name": "Outbound Contact",
            "description": "Creates personalized outreach messages for qualified leads",
            "status": "active",
            "category": "outbound",
            "default_prompt": """You are a professional outbound sales agent for PipeWise. Create personalized, engaging outreach messages that convert leads into conversations.

For each qualified lead, craft a message that:
1. Addresses them by name and references their company
2. Demonstrates understanding of their business challenges
3. Clearly articulates how PipeWise solves their specific pain points
4. Includes a clear, compelling call-to-action
5. Maintains a professional yet conversational tone

Keep messages concise (150-200 words) and avoid being overly salesy. Focus on value and building rapport."""
        },
        {
            "id": "meeting_scheduler",
            "name": "Meeting Scheduler",
            "description": "Handles meeting coordination and calendar management",
            "status": "active",
            "category": "scheduling",
            "default_prompt": """You are a professional meeting scheduler for PipeWise. Your role is to coordinate meetings between prospects and sales team members efficiently.

When a prospect expresses interest in scheduling a meeting:
1. Offer 3-4 specific time slots within the next 3-5 business days
2. Confirm timezone and preferred meeting format
3. Send calendar invitation with agenda and relevant materials
4. Follow up with confirmation and any pre-meeting questions"""
        },
        {
            "id": "whatsapp_agent",
            "name": "WhatsApp Agent",
            "description": "Manages WhatsApp Business communications and lead engagement",
            "status": "active",
            "category": "communication",
            "default_prompt": """You are a WhatsApp Business communication agent for PipeWise. Handle customer inquiries and lead engagement through WhatsApp with professionalism and efficiency.

Guidelines for WhatsApp interactions:
1. Respond promptly and professionally
2. Keep messages concise and clear
3. Capture lead information when appropriate
4. Log all interactions in CRM system"""
        }
    ]
    
    agents_overview = []
    total_processed = 0
    success_rates = []
    
    for agent_def in default_agents:
        # Get active prompt for this agent type
        prompt_query = select(AgentPrompt).where(
            and_(
                AgentPrompt.tenant_id == tenant.id,
                AgentPrompt.agent_type == agent_def["id"],
                AgentPrompt.is_active == True
            )
        ).order_by(AgentPrompt.updated_at.desc())
        
        prompt_result = await db.execute(prompt_query)
        active_prompt = prompt_result.scalar_one_or_none()
        
        # Get performance metrics
        metrics_query = select(AgentPerformanceMetrics).where(
            and_(
                AgentPerformanceMetrics.tenant_id == tenant.id,
                AgentPerformanceMetrics.agent_type == agent_def["id"]
            )
        ).order_by(AgentPerformanceMetrics.date.desc()).limit(1)
        
        metrics_result = await db.execute(metrics_query)
        latest_metrics = metrics_result.scalar_one_or_none()
        
        # Build performance data
        if latest_metrics:
            performance = {
                "successRate": latest_metrics.success_rate,
                "avgResponseTime": f"{latest_metrics.avg_response_time_ms / 1000:.1f}s",
                "totalProcessed": latest_metrics.total_processed
            }
            total_processed += latest_metrics.total_processed
            success_rates.append(latest_metrics.success_rate)
        else:
            # Default metrics for demo
            default_metrics = {
                "lead_qualifier": {"successRate": 87, "avgResponseTime": "1.2s", "totalProcessed": 1247},
                "outbound_contact": {"successRate": 34, "avgResponseTime": "2.1s", "totalProcessed": 892},
                "meeting_scheduler": {"successRate": 92, "avgResponseTime": "0.8s", "totalProcessed": 456},
                "whatsapp_agent": {"successRate": 78, "avgResponseTime": "0.5s", "totalProcessed": 2341}
            }
            performance = default_metrics.get(agent_def["id"], {"successRate": 75, "avgResponseTime": "1.0s", "totalProcessed": 100})
            total_processed += performance["totalProcessed"]
            success_rates.append(performance["successRate"])
        
        agent_overview = AgentOverviewResponse(
            id=agent_def["id"],
            name=agent_def["name"],
            description=agent_def["description"],
            status=agent_def["status"],
            category=agent_def["category"],
            current_prompt=active_prompt.prompt_content if active_prompt else agent_def["default_prompt"],
            default_prompt=agent_def["default_prompt"],
            last_modified=active_prompt.updated_at.strftime('%Y-%m-%d') if active_prompt else "Default",
            performance=performance
        )
        
        agents_overview.append(agent_overview)
    
    avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
    active_count = len([a for a in agents_overview if a.status == "active"])
    
    return AgentListResponse(
        agents=agents_overview,
        total=len(agents_overview),
        active_count=active_count,
        avg_success_rate=round(avg_success_rate, 1),
        total_processed=total_processed
    )


# Prompt Testing Endpoint
@router.post("/test-prompt", response_model=PromptTestResponse)
async def test_prompt(
    test_request: PromptTestRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
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
                errors=["Prompt content is too short (minimum 10 characters)"]
            )
        
        # Simulate prompt execution (replace with actual AI call)
        await asyncio.sleep(0.5)  # Simulate processing time
        
        # Mock successful test result
        test_result = {
            "validation": "passed",
            "prompt_length": len(test_request.prompt_content),
            "estimated_tokens": len(test_request.prompt_content.split()) * 1.3,
            "readability_score": 85,
            "agent_type": test_request.agent_type,
            "sample_output": "Mock response from agent based on the provided prompt..."
        }
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return PromptTestResponse(
            success=True,
            test_type=test_request.test_type,
            execution_time_ms=execution_time,
            result=test_result,
            suggestions=[
                "Consider adding more specific instructions for edge cases",
                "You might want to include examples of desired output format"
            ]
        )
        
    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        return PromptTestResponse(
            success=False,
            test_type=test_request.test_type,
            execution_time_ms=execution_time,
            result={},
            errors=[f"Test execution failed: {str(e)}"]
        )


# Performance Metrics Endpoints
@router.get("/metrics/{agent_type}", response_model=List[AgentPerformanceMetricsResponse])
async def get_agent_metrics(
    agent_type: AgentTypeEnum,
    days: int = Query(30, ge=1, le=365, description="Number of days of metrics to retrieve"),
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get performance metrics for a specific agent type."""
    from datetime import timedelta
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(AgentPerformanceMetrics).where(
        and_(
            AgentPerformanceMetrics.tenant_id == tenant.id,
            AgentPerformanceMetrics.agent_type == agent_type,
            AgentPerformanceMetrics.date >= start_date
        )
    ).order_by(AgentPerformanceMetrics.date.desc())
    
    result = await db.execute(query)
    metrics = result.scalars().all()
    
    return [
        AgentPerformanceMetricsResponse(**metric.__dict__)
        for metric in metrics
    ]


import asyncio