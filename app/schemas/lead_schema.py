from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID


class LeadCreate(BaseModel):
    name: str
    email: EmailStr
    company: str
    phone: str | None = None
    message: str | None = None
    source: str | None = None
    utm_params: dict | None = None
    metadata: dict | None = None


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
    utm_params: Optional[dict] = None
    metadata: Optional[dict] = None
