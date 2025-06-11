"""
Agent Configuration Schemas for PipeWise API

Pydantic models for validating and serializing agent configuration data.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, validator
from app.models.agent_config import AgentType


class AgentTypeEnum(str, Enum):
    """Agent type enumeration for API."""
    LEAD_QUALIFIER = "lead_qualifier"
    OUTBOUND_CONTACT = "outbound_contact"
    MEETING_SCHEDULER = "meeting_scheduler"
    WHATSAPP_AGENT = "whatsapp_agent"


# Agent Prompt Schemas
class AgentPromptBase(BaseModel):
    """Base schema for agent prompts."""
    agent_type: AgentTypeEnum
    prompt_name: str = Field(..., min_length=1, max_length=255)
    prompt_content: str = Field(..., min_length=10, max_length=50000)
    is_active: bool = True
    is_default: bool = False


class AgentPromptCreate(AgentPromptBase):
    """Schema for creating agent prompts."""
    pass

    @validator('prompt_content')
    def validate_prompt_content(cls, v):
        """Validate prompt content."""
        if not v.strip():
            raise ValueError('Prompt content cannot be empty')
        if len(v.strip()) < 10:
            raise ValueError('Prompt content must be at least 10 characters')
        return v.strip()

    @validator('prompt_name')
    def validate_prompt_name(cls, v):
        """Validate prompt name."""
        if not v.strip():
            raise ValueError('Prompt name cannot be empty')
        return v.strip()


class AgentPromptUpdate(BaseModel):
    """Schema for updating agent prompts."""
    prompt_name: Optional[str] = Field(None, min_length=1, max_length=255)
    prompt_content: Optional[str] = Field(None, min_length=10, max_length=50000)
    is_active: Optional[bool] = None

    @validator('prompt_content')
    def validate_prompt_content(cls, v):
        """Validate prompt content if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('Prompt content cannot be empty')
            if len(v.strip()) < 10:
                raise ValueError('Prompt content must be at least 10 characters')
            return v.strip()
        return v

    @validator('prompt_name')
    def validate_prompt_name(cls, v):
        """Validate prompt name if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('Prompt name cannot be empty')
            return v.strip()
        return v


class AgentPromptResponse(AgentPromptBase):
    """Schema for agent prompt responses."""
    id: UUID
    tenant_id: UUID
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    last_modified: str

    class Config:
        from_attributes = True

    @validator('last_modified', pre=True)
    def format_last_modified(cls, v):
        """Format last modified date."""
        if isinstance(v, datetime):
            return v.strftime('%Y-%m-%d')
        return v


# Agent Configuration Schemas
class AgentConfigurationBase(BaseModel):
    """Base schema for agent configurations."""
    agent_type: AgentTypeEnum
    config_name: str = Field(..., min_length=1, max_length=255)
    settings: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class AgentConfigurationCreate(AgentConfigurationBase):
    """Schema for creating agent configurations."""
    prompt_id: Optional[UUID] = None


class AgentConfigurationUpdate(BaseModel):
    """Schema for updating agent configurations."""
    config_name: Optional[str] = Field(None, min_length=1, max_length=255)
    settings: Optional[Dict[str, Any]] = None
    prompt_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class AgentConfigurationResponse(AgentConfigurationBase):
    """Schema for agent configuration responses."""
    id: UUID
    tenant_id: UUID
    prompt_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    prompt: Optional[AgentPromptResponse] = None

    class Config:
        from_attributes = True


# Performance Metrics Schemas
class AgentPerformanceMetricsBase(BaseModel):
    """Base schema for agent performance metrics."""
    agent_type: AgentTypeEnum
    total_processed: int = Field(ge=0)
    successful_executions: int = Field(ge=0)
    failed_executions: int = Field(ge=0)
    avg_response_time_ms: int = Field(ge=0)
    custom_metrics: Dict[str, Any] = Field(default_factory=dict)


class AgentPerformanceMetricsCreate(AgentPerformanceMetricsBase):
    """Schema for creating performance metrics."""
    date: datetime
    prompt_id: Optional[UUID] = None


class AgentPerformanceMetricsResponse(AgentPerformanceMetricsBase):
    """Schema for performance metrics responses."""
    id: UUID
    tenant_id: UUID
    prompt_id: Optional[UUID]
    date: datetime
    success_rate: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Combined Response Schemas
class AgentOverviewResponse(BaseModel):
    """Schema for agent overview with all related data."""
    id: str
    name: str
    description: str
    status: str
    category: str
    current_prompt: str
    default_prompt: str
    last_modified: str
    performance: Dict[str, Any]


class AgentListResponse(BaseModel):
    """Schema for listing agents."""
    agents: List[AgentOverviewResponse]
    total: int
    active_count: int
    avg_success_rate: float
    total_processed: int


# Test Prompt Schemas
class PromptTestRequest(BaseModel):
    """Schema for testing prompts."""
    agent_type: AgentTypeEnum
    prompt_content: str = Field(..., min_length=10, max_length=50000)
    test_data: Dict[str, Any] = Field(default_factory=dict)
    test_type: str = Field(default="validation", regex="^(validation|execution|performance)$")


class PromptTestResponse(BaseModel):
    """Schema for prompt test results."""
    success: bool
    test_type: str
    execution_time_ms: int
    result: Dict[str, Any]
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# Bulk Operations Schemas
class BulkPromptUpdate(BaseModel):
    """Schema for bulk prompt updates."""
    agent_ids: List[UUID]
    updates: AgentPromptUpdate


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation responses."""
    success: bool
    updated_count: int
    failed_count: int
    errors: List[Dict[str, str]] = Field(default_factory=list)


# Agent Status Schemas
class AgentStatusUpdate(BaseModel):
    """Schema for updating agent status."""
    is_active: bool
    reason: Optional[str] = None


class AgentStatusResponse(BaseModel):
    """Schema for agent status responses."""
    agent_type: AgentTypeEnum
    is_active: bool
    last_status_change: datetime
    status_reason: Optional[str] = None