"""
Agent Configuration Models for PipeWise

NOTE: This file is temporarily simplified as we're using Supabase instead of SQLAlchemy.
These models will be converted to Pydantic schemas in future versions.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID, uuid4


class AgentTypeEnum(str, Enum):
    """Agent type enumeration"""

    COORDINATOR = "coordinator"
    LEAD_GENERATOR = "lead_generator"
    OUTBOUND_CONTACT = "outbound_contact"
    MEETING_SCHEDULER = "meeting_scheduler"
    WHATSAPP_AGENT = "whatsapp_agent"


class AgentPrompt:
    """
    Simplified AgentPrompt class for compatibility.
    In production, this should be replaced with Pydantic schemas for Supabase.
    """

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.tenant_id = kwargs.get("tenant_id")
        self.agent_type = kwargs.get("agent_type")
        self.prompt_name = kwargs.get("prompt_name", "")
        self.prompt_content = kwargs.get("prompt_content", "")
        self.is_active = kwargs.get("is_active", True)
        self.is_default = kwargs.get("is_default", False)
        self.version = kwargs.get("version", 1)
        self.created_by = kwargs.get("created_by")
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.updated_at = kwargs.get("updated_at", datetime.utcnow())

    def __repr__(self) -> str:
        return f"<AgentPrompt(id={self.id}, agent_type={self.agent_type}, tenant_id={self.tenant_id})>"


class AgentConfiguration:
    """
    Simplified AgentConfiguration class for compatibility.
    In production, this should be replaced with Pydantic schemas for Supabase.
    """

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.tenant_id = kwargs.get("tenant_id")
        self.agent_type = kwargs.get("agent_type")
        self.config_name = kwargs.get("config_name", "")
        self.settings = kwargs.get("settings", {})
        self.prompt_id = kwargs.get("prompt_id")
        self.is_active = kwargs.get("is_active", True)
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.updated_at = kwargs.get("updated_at", datetime.utcnow())

    def __repr__(self) -> str:
        return f"<AgentConfiguration(id={self.id}, agent_type={self.agent_type}, tenant_id={self.tenant_id})>"


class AgentPerformanceMetrics:
    """
    Simplified AgentPerformanceMetrics class for compatibility.
    In production, this should be replaced with Pydantic schemas for Supabase.
    """

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.tenant_id = kwargs.get("tenant_id")
        self.agent_type = kwargs.get("agent_type")
        self.prompt_id = kwargs.get("prompt_id")
        self.total_processed = kwargs.get("total_processed", 0)
        self.successful_executions = kwargs.get("successful_executions", 0)
        self.failed_executions = kwargs.get("failed_executions", 0)
        self.avg_response_time_ms = kwargs.get("avg_response_time_ms", 0)
        self.date = kwargs.get("date", datetime.utcnow())
        self.custom_metrics = kwargs.get("custom_metrics", {})
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.updated_at = kwargs.get("updated_at", datetime.utcnow())

    def __repr__(self) -> str:
        return f"<AgentPerformanceMetrics(id={self.id}, agent_type={self.agent_type}, date={self.date})>"

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_processed == 0:
            return 0.0
        return (self.successful_executions / self.total_processed) * 100
