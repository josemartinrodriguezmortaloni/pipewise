"""
Contact and outreach message schemas for PipeWise CRM.
Defines the data models for contact management and outreach messaging.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class ContactPlatform(str, Enum):
    """Available contact platforms."""

    EMAIL = "email"
    PHONE = "phone"
    WHATSAPP = "whatsapp"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"


class ContactStatus(str, Enum):
    """Contact status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    UNSUBSCRIBED = "unsubscribed"


class OutreachStatus(str, Enum):
    """Outreach message status values."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    REPLIED = "replied"
    FAILED = "failed"


class ContactCreate(BaseModel):
    """Schema for creating a new contact."""

    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)

    # Platform-specific data
    platform: ContactPlatform
    platform_id: str = Field(..., min_length=1, max_length=100)
    platform_username: Optional[str] = Field(None, max_length=100)

    # Contact information
    company: Optional[str] = Field(None, max_length=200)
    position: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=100)

    # Status and preferences
    status: ContactStatus = ContactStatus.ACTIVE
    preferences: Optional[Dict[str, Any]] = None

    # Metadata
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    # User association
    user_id: Optional[str] = None


class ContactUpdate(BaseModel):
    """Schema for updating an existing contact."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)

    platform_username: Optional[str] = Field(None, max_length=100)

    company: Optional[str] = Field(None, max_length=200)
    position: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=100)

    status: Optional[ContactStatus] = None
    preferences: Optional[Dict[str, Any]] = None

    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ContactResponse(BaseModel):
    """Schema for contact response data."""

    id: UUID
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

    platform: ContactPlatform
    platform_id: str
    platform_username: Optional[str] = None

    company: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None

    status: ContactStatus
    preferences: Optional[Dict[str, Any]] = None

    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    user_id: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None
    last_contacted: Optional[datetime] = None


class OutreachMessageCreate(BaseModel):
    """Schema for creating an outreach message."""

    contact_id: UUID
    message_text: str = Field(..., min_length=1, max_length=10000)
    subject: Optional[str] = Field(None, max_length=200)

    # Message type and priority
    message_type: str = Field(default="outreach", max_length=50)
    priority: str = Field(default="normal", max_length=20)

    # Scheduling
    scheduled_for: Optional[datetime] = None

    # Template and personalization
    template_id: Optional[str] = None
    personalization_data: Optional[Dict[str, Any]] = None

    # Metadata
    campaign_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    # User association
    user_id: Optional[str] = None


class OutreachMessageUpdate(BaseModel):
    """Schema for updating an outreach message."""

    message_text: Optional[str] = Field(None, min_length=1, max_length=10000)
    subject: Optional[str] = Field(None, max_length=200)

    status: Optional[OutreachStatus] = None
    priority: Optional[str] = Field(None, max_length=20)

    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None

    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OutreachMessageResponse(BaseModel):
    """Schema for outreach message response data."""

    id: UUID
    contact_id: UUID
    message_text: str
    subject: Optional[str] = None

    status: OutreachStatus
    message_type: str
    priority: str

    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None

    template_id: Optional[str] = None
    personalization_data: Optional[Dict[str, Any]] = None

    campaign_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    error_message: Optional[str] = None
    user_id: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None


class ContactListResponse(BaseModel):
    """Schema for paginated contact list response."""

    contacts: List[ContactResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class ContactStatsResponse(BaseModel):
    """Schema for contact statistics response."""

    total_contacts: int
    active_contacts: int
    blocked_contacts: int
    unsubscribed_contacts: int

    # Platform breakdown
    platform_stats: Dict[str, int]

    # Recent activity
    contacts_added_today: int
    contacts_added_this_week: int
    contacts_added_this_month: int

    # Outreach stats
    messages_sent_today: int
    messages_sent_this_week: int
    messages_sent_this_month: int

    # Response rates
    total_messages_sent: int
    total_responses_received: int
    response_rate: float

    # Last activity
    last_contact_added: Optional[datetime] = None
    last_message_sent: Optional[datetime] = None


class OutreachCampaignCreate(BaseModel):
    """Schema for creating an outreach campaign."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

    # Campaign settings
    platform: ContactPlatform
    message_template: str = Field(..., min_length=1, max_length=10000)
    subject_template: Optional[str] = Field(None, max_length=200)

    # Targeting
    target_tags: Optional[List[str]] = None
    target_metadata: Optional[Dict[str, Any]] = None

    # Scheduling
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Settings
    max_messages_per_day: int = Field(default=50, ge=1, le=1000)
    time_between_messages_minutes: int = Field(default=30, ge=1, le=1440)

    # Status
    is_active: bool = True

    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


class OutreachCampaignResponse(BaseModel):
    """Schema for outreach campaign response data."""

    id: UUID
    name: str
    description: Optional[str] = None

    platform: ContactPlatform
    message_template: str
    subject_template: Optional[str] = None

    target_tags: Optional[List[str]] = None
    target_metadata: Optional[Dict[str, Any]] = None

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    max_messages_per_day: int
    time_between_messages_minutes: int

    is_active: bool

    # Campaign stats
    total_contacts: int
    messages_sent: int
    messages_pending: int
    responses_received: int

    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None
