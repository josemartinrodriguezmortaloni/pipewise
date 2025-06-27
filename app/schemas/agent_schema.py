"""
Agent Configuration Schemas for PipeWise API

Pydantic models for validating and serializing agent configuration data.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict
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

    # Validators temporarily removed for testing compatibility


class AgentPromptUpdate(BaseModel):
    """Schema for updating agent prompts."""

    prompt_name: Optional[str] = Field(None, min_length=1, max_length=255)
    prompt_content: Optional[str] = Field(None, min_length=10, max_length=50000)
    is_active: Optional[bool] = None

    @field_validator("prompt_content")
    @classmethod
    def validate_prompt_content(cls, v):
        """Validate prompt content if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError("Prompt content cannot be empty")
            if len(v.strip()) < 10:
                raise ValueError("Prompt content must be at least 10 characters")
            return v.strip()
        return v

    @field_validator("prompt_name")
    @classmethod
    def validate_prompt_name(cls, v):
        """Validate prompt name if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError("Prompt name cannot be empty")
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

    model_config = ConfigDict(from_attributes=True)

    @field_validator("last_modified", mode="before")
    @classmethod
    def format_last_modified(cls, v):
        """Format last modified date."""
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d")
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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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
    test_type: str = Field(
        default="validation", pattern="^(validation|execution|performance)$"
    )


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


class CoordinatorConfig(BaseModel):
    """Configuration schema for the Coordinator Agent"""

    # LLM Configuration
    model: str = Field(default="gpt-4o", description="LLM model to use")
    temperature: float = Field(
        default=0.2, ge=0.0, le=2.0, description="Model temperature"
    )
    max_tokens: Optional[int] = Field(
        default=1000, ge=1, description="Maximum tokens per response"
    )

    # Lead qualification settings
    qualification_threshold: float = Field(
        default=70.0, ge=0.0, le=100.0, description="Minimum score to qualify a lead"
    )
    auto_qualify: bool = Field(
        default=True, description="Automatically qualify leads above threshold"
    )

    # Handoff settings
    auto_handoff_to_qualifier: bool = Field(
        default=True, description="Auto handoff to Lead Qualifier"
    )
    auto_handoff_to_scheduler: bool = Field(
        default=False,
        description="Auto handoff to Meeting Scheduler after qualification",
    )
    require_human_approval: bool = Field(
        default=False, description="Require human approval for handoffs"
    )

    # Communication settings
    response_timeout: int = Field(
        default=30, ge=5, le=300, description="Response timeout in seconds"
    )
    max_conversation_turns: int = Field(
        default=10, ge=1, le=50, description="Maximum conversation turns"
    )

    # Integration settings
    enable_crm_sync: bool = Field(default=True, description="Sync lead data with CRM")
    enable_email_notifications: bool = Field(
        default=True, description="Send email notifications"
    )

    # Validation and quality settings
    validate_email_format: bool = Field(
        default=True, description="Validate email format"
    )
    validate_phone_format: bool = Field(
        default=True, description="Validate phone format"
    )
    require_company_info: bool = Field(
        default=False, description="Require company information"
    )

    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, str_strip_whitespace=True
    )


class LeadQualifierConfig(BaseModel):
    """Configuration schema for the Lead Qualifier Agent"""

    # LLM Configuration
    model: str = Field(default="gpt-4o", description="LLM model to use")
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Model temperature for consistent scoring",
    )
    max_tokens: Optional[int] = Field(
        default=800, ge=1, description="Maximum tokens per response"
    )

    # Qualification criteria
    budget_weight: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Weight for budget consideration"
    )
    authority_weight: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Weight for decision-making authority"
    )
    need_weight: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Weight for need assessment"
    )
    timeline_weight: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Weight for timeline urgency"
    )

    # Scoring thresholds
    minimum_score: float = Field(
        default=60.0, ge=0.0, le=100.0, description="Minimum qualification score"
    )
    high_priority_score: float = Field(
        default=85.0, ge=0.0, le=100.0, description="High priority threshold"
    )

    # Analysis settings
    require_budget_info: bool = Field(
        default=True, description="Require budget information for qualification"
    )
    require_timeline_info: bool = Field(
        default=True, description="Require timeline information"
    )
    deep_analysis_mode: bool = Field(
        default=False, description="Enable detailed lead analysis"
    )

    # Handoff settings
    auto_schedule_qualified: bool = Field(
        default=True, description="Auto schedule meetings for qualified leads"
    )
    notify_sales_team: bool = Field(
        default=True, description="Notify sales team of qualified leads"
    )

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class MeetingSchedulerConfig(BaseModel):
    """Configuration schema for the Meeting Scheduler Agent"""

    # LLM Configuration
    model: str = Field(default="gpt-4o-mini", description="LLM model to use")
    temperature: float = Field(
        default=0.1, ge=0.0, le=2.0, description="Model temperature"
    )
    max_tokens: Optional[int] = Field(
        default=600, ge=1, description="Maximum tokens per response"
    )

    # Calendar integration
    calendly_integration: bool = Field(
        default=True, description="Enable Calendly integration"
    )
    google_calendar_integration: bool = Field(
        default=False, description="Enable Google Calendar integration"
    )
    default_meeting_duration: int = Field(
        default=30, ge=15, le=120, description="Default meeting duration in minutes"
    )

    # Scheduling preferences
    business_hours_only: bool = Field(
        default=True, description="Only schedule during business hours"
    )
    timezone_auto_detect: bool = Field(
        default=True, description="Auto-detect lead's timezone"
    )
    buffer_time_minutes: int = Field(
        default=15, ge=0, le=60, description="Buffer time between meetings"
    )

    # Meeting types
    demo_meeting_enabled: bool = Field(default=True, description="Enable demo meetings")
    consultation_meeting_enabled: bool = Field(
        default=True, description="Enable consultation meetings"
    )
    follow_up_meeting_enabled: bool = Field(
        default=True, description="Enable follow-up meetings"
    )

    # Notification settings
    send_calendar_invite: bool = Field(
        default=True, description="Send calendar invites"
    )
    send_reminder_emails: bool = Field(default=True, description="Send reminder emails")
    reminder_hours_before: int = Field(
        default=24, ge=1, le=168, description="Hours before meeting to send reminder"
    )

    # Fallback settings
    manual_scheduling_fallback: bool = Field(
        default=True, description="Fallback to manual scheduling if auto fails"
    )
    max_scheduling_attempts: int = Field(
        default=3, ge=1, le=10, description="Maximum auto-scheduling attempts"
    )

    model_config = ConfigDict(extra="forbid", validate_assignment=True)
