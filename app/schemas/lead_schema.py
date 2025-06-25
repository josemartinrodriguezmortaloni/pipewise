from pydantic import BaseModel, EmailStr
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

    class Config:
        extra = "forbid"


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

    class Config:
        extra = "forbid"
