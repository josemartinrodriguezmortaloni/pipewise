from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID


class LeadCreate(BaseModel):
    name: str
    email: EmailStr
    company: str
    phone: Optional[str] = None
    message: Optional[str] = None
    source: Optional[str] = None
    utm_params: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


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
    owner_id: Optional[UUID] = None
    utm_params: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


class LeadAnalysis(BaseModel):
    """Schema for lead analysis results"""

    lead_id: str
    qualification_score: float = Field(ge=0, le=100)
    qualification_reason: str
    recommended_actions: list[str]
    urgency_level: str = Field(pattern="^(low|medium|high|urgent)$")

    model_config = ConfigDict(from_attributes=True)


class MeetingScheduleResult(BaseModel):
    """Schema for meeting scheduling results"""

    success: bool
    meeting_url: Optional[str] = None
    meeting_time: Optional[str] = None
    error_message: Optional[str] = None
    follow_up_required: bool = False

    model_config = ConfigDict(from_attributes=True)
