from pydantic import BaseModel, ConfigDict
from uuid import UUID


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
    created_at: str | None = None
    source: str | None = None
    status: str = "new"
    owner_id: UUID | None = None
    utm_params: dict | None = None
    metadata: dict | None = None
