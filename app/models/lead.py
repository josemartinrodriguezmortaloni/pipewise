from pydantic import BaseModel, ConfigDict, field_validator
from uuid import UUID
from typing import Optional
from datetime import datetime


class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID | None = None
    name: str
    email: str
    company: str
    phone: str | None = None
    message: str | None = None
    qualified: bool = False
    contacted: bool = False
    meeting_scheduled: bool = False
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None  # Campo faltante
    source: str | None = None
    status: str = "new"
    owner_id: UUID | None = None
    user_id: UUID | None = None  # Campo faltante
    utm_params: dict | None = None
    metadata: dict | None = None

    @field_validator("contacted", mode="before")
    @classmethod
    def validate_contacted(cls, v):
        """Convertir None a False para contacted"""
        if v is None:
            return False
        return v

    @field_validator("meeting_scheduled", mode="before")
    @classmethod
    def validate_meeting_scheduled(cls, v):
        """Convertir None a False para meeting_scheduled"""
        if v is None:
            return False
        return v

    @field_validator("qualified", mode="before")
    @classmethod
    def validate_qualified(cls, v):
        """Convertir None a False para qualified"""
        if v is None:
            return False
        return v
