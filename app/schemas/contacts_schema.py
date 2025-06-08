from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class ContactBase(BaseModel):
    """Schema base para contactos"""

    name: str = Field(..., description="Nombre del contacto")
    email: Optional[EmailStr] = Field(None, description="Email del contacto")
    phone: Optional[str] = Field(None, description="Teléfono del contacto")
    platform: PlatformType = Field(
        ...,
        description="Plataforma donde se contactó (whatsapp, instagram, twitter, email)",
    )
    platform_id: str = Field(..., description="ID del contacto en la plataforma")
    username: Optional[str] = Field(None, description="Username en la plataforma")
    profile_url: Optional[str] = Field(None, description="URL del perfil")


class ContactCreate(ContactBase):
    """Schema para crear un nuevo contacto"""

    lead_id: Optional[UUID] = Field(None, description="ID del lead asociado")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Metadatos adicionales"
    )


class ContactUpdate(BaseModel):
    """Schema para actualizar un contacto"""

    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    profile_url: Optional[str] = None
    lead_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class ContactResponse(ContactBase):
    """Schema de respuesta para contactos"""

    id: UUID
    lead_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class OutreachMessageBase(BaseModel):
    """Schema base para mensajes de outreach"""

    contact_id: UUID = Field(..., description="ID del contacto")
    platform: str = Field(..., description="Plataforma usada")
    message_type: MessageType = Field(
        ..., description="Tipo de mensaje (text, template, interactive)"
    )
    subject: Optional[str] = Field(None, description="Asunto (para emails)")
    content: str = Field(..., description="Contenido del mensaje")
    template_name: Optional[str] = Field(None, description="Nombre del template usado")


class OutreachMessageCreate(OutreachMessageBase):
    """Schema para crear un mensaje de outreach"""

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Metadatos del mensaje"
    )


class OutreachMessageResponse(OutreachMessageBase):
    """Schema de respuesta para mensajes de outreach"""

    id: UUID
    message_id: Optional[str] = Field(
        None, description="ID del mensaje en la plataforma"
    )
    status: str = Field(default="sent", description="Estado del mensaje")
    sent_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True

from pydantic import BaseModel, Field, EmailStr, field_validator
 
 class ContactStatsResponse(BaseModel):
     """Schema para estadísticas de contactos"""

     total_contacts: int
     contacts_by_platform: Dict[str, int]
     messages_sent: int
     meetings_scheduled: int
    conversion_rate: float = Field(..., ge=0.0, le=1.0, description="Conversion rate between 0 and 1")
     last_contact_date: Optional[datetime]


class ContactWithMessages(ContactResponse):
    """Schema de contacto con sus mensajes"""

    messages: List[OutreachMessageResponse] = Field(default_factory=list)
    last_message_at: Optional[datetime] = None
    meeting_scheduled: bool = False
    meeting_url: Optional[str] = None


class ContactWithMessages(ContactResponse):
    """Schema de contacto con sus mensajes"""

    messages: List[OutreachMessageResponse] = Field(default_factory=list)
    last_message_at: Optional[datetime] = None
    meeting_scheduled: bool = False
    meeting_url: Optional[str] = None
