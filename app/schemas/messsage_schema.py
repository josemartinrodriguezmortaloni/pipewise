from pydantic import BaseModel, Optional, Any
from uuid import UUID


class MessageCreate(BaseModel):
    conversation_id: UUID
    sender: str
    content: str
    message_type: Optional[str] = "text"
    metadata: Optional[Any] = None


class LeadResponse(BaseModel):
    id: str
    status: str
    qualified: bool
    contacted: bool
    meeting_scheduled: bool
