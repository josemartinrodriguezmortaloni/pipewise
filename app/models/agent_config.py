"""
Agent Configuration Models for PipeWise

This module provides database models for storing and managing custom agent configurations
and prompts for the multi-tenant PipeWise system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime, 
    JSON, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AgentType(str, Enum):
    """Enumeration of available agent types."""
    LEAD_QUALIFIER = "lead_qualifier"
    OUTBOUND_CONTACT = "outbound_contact"
    MEETING_SCHEDULER = "meeting_scheduler"
    WHATSAPP_AGENT = "whatsapp_agent"


class AgentPrompt(Base):
    """
    Model for storing custom agent prompts.
    
    Supports multi-tenancy and versioning of prompts for different agent types.
    """
    __tablename__ = "agent_prompts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    agent_type = Column(SQLEnum(AgentType), nullable=False)
    
    # Prompt metadata
    prompt_name = Column(String(255), nullable=False)
    prompt_content = Column(Text, nullable=False)
    
    # Status and versioning
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    
    # Audit fields
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="agent_prompts")
    created_by_user = relationship("User", foreign_keys=[created_by])
    agent_configurations = relationship("AgentConfiguration", back_populates="prompt")

    def __repr__(self) -> str:
        return f"<AgentPrompt(id={self.id}, agent_type={self.agent_type}, tenant_id={self.tenant_id})>"


class AgentConfiguration(Base):
    """
    Model for storing agent configurations and settings.
    
    Links prompts with additional configuration options per tenant.
    """
    __tablename__ = "agent_configurations"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    agent_type = Column(SQLEnum(AgentType), nullable=False)
    
    # Configuration metadata
    config_name = Column(String(255), nullable=False)
    settings = Column(JSON, default=dict, nullable=False)
    
    # Link to prompt
    prompt_id = Column(PGUUID(as_uuid=True), ForeignKey("agent_prompts.id"), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="agent_configurations")
    prompt = relationship("AgentPrompt", back_populates="agent_configurations")

    def __repr__(self) -> str:
        return f"<AgentConfiguration(id={self.id}, agent_type={self.agent_type}, tenant_id={self.tenant_id})>"


class AgentPerformanceMetrics(Base):
    """
    Model for tracking agent performance metrics.
    
    Stores analytics data for monitoring and optimization.
    """
    __tablename__ = "agent_performance_metrics"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    agent_type = Column(SQLEnum(AgentType), nullable=False)
    prompt_id = Column(PGUUID(as_uuid=True), ForeignKey("agent_prompts.id"), nullable=True)
    
    # Performance metrics
    total_processed = Column(Integer, default=0, nullable=False)
    successful_executions = Column(Integer, default=0, nullable=False)
    failed_executions = Column(Integer, default=0, nullable=False)
    avg_response_time_ms = Column(Integer, default=0, nullable=False)
    
    # Time period
    date = Column(DateTime(timezone=True), nullable=False)
    
    # Additional metrics (JSON for flexibility)
    custom_metrics = Column(JSON, default=dict, nullable=False)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    tenant = relationship("Tenant")
    prompt = relationship("AgentPrompt")

    def __repr__(self) -> str:
        return f"<AgentPerformanceMetrics(id={self.id}, agent_type={self.agent_type}, date={self.date})>"

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_processed == 0:
            return 0.0
        return (self.successful_executions / self.total_processed) * 100