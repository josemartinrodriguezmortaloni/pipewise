from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class LeadCreate(BaseModel):
    name: str
    email: EmailStr
    company: str
    phone: Optional[str] = None
    message: Optional[str] = None
    source: Optional[str] = None
    user_id: Optional[UUID] = None
    utm_params: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    message: Optional[str] = None
    qualified: Optional[bool] = None
    contacted: Optional[bool] = None
    meeting_scheduled: Optional[bool] = None
    status: Optional[str] = None
    user_id: Optional[UUID] = None
    utm_params: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="allow")


class LeadResponse(BaseModel):
    """Schema completo para respuestas de Lead - incluye todos los campos de la base de datos"""

    id: UUID
    name: str
    email: str
    company: str
    phone: Optional[str] = None
    message: Optional[str] = None
    qualified: bool = False
    contacted: bool = False
    meeting_scheduled: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    source: Optional[str] = None
    status: str = "new"
    owner_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    utm_params: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True, extra="allow")


class LeadAnalysis(BaseModel):
    """Schema for lead analysis results"""

    lead_id: str
    qualification_score: float = Field(ge=0, le=100)
    qualification_reason: str
    recommended_actions: list[str]
    urgency_level: str = Field(pattern="^(low|medium|high|urgent)$")

    model_config = ConfigDict(from_attributes=True, extra="allow")


class MeetingScheduleResult(BaseModel):
    """Schema for meeting scheduling results"""

    success: bool
    meeting_url: Optional[str] = None
    meeting_time: Optional[str] = None
    error_message: Optional[str] = None
    follow_up_required: bool = False

    model_config = ConfigDict(from_attributes=True, extra="allow")
