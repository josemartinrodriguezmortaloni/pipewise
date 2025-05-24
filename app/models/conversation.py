from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID


class Conversation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID | None = None
    lead_id: UUID
    agent_id: Optional[UUID] = (
        None  # CORREGIDO: Ahora es opcional en lugar de requerido
    )
    started_at: str | None = None
    ended_at: Optional[str] = None
    status: str = "active"
    summary: Optional[str] = None
    channel: Optional[str] = "system"
