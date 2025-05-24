from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class ConversationCreate(BaseModel):
    lead_id: UUID
    agent_id: Optional[UUID] = None  # CORREGIDO: Ahora es opcional
    channel: Optional[str] = "system"
    status: Optional[str] = "active"


class ConversationUpdate(BaseModel):
    agent_id: Optional[UUID] = None
    ended_at: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    channel: Optional[str] = None
