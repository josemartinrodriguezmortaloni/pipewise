from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from uuid import UUID


class Message(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: Optional[UUID] = None
    conversation_id: UUID
    sender: str
    content: str
    sent_at: str | None = None
    message_type: Optional[str] = "text"
    metadata: Optional[Any] = None
