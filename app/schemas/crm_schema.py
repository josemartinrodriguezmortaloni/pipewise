# app/schemas/crm_schema.py - Esquemas para el sistema CRM
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from enum import Enum


# ===================== ENUMS =====================


class LeadStatus(str, Enum):
    """Estados de los leads"""

    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    proposal = "proposal"
    negotiation = "negotiation"
    closed_won = "closed_won"
    closed_lost = "closed_lost"


class LeadSource(str, Enum):
    """Fuentes de los leads"""

    website = "website"
    social_media = "social_media"
    email_campaign = "email_campaign"
    referral = "referral"
    cold_call = "cold_call"
    trade_show = "trade_show"
    api = "api"
    other = "other"


class OpportunityStage(str, Enum):
    """Etapas de las oportunidades"""

    qualification = "qualification"
    needs_analysis = "needs_analysis"
    value_proposition = "value_proposition"
    id_decision_makers = "id_decision_makers"
    perception_analysis = "perception_analysis"
    proposal = "proposal"
    negotiation = "negotiation"
    closed_won = "closed_won"
    closed_lost = "closed_lost"


class ActivityType(str, Enum):
    """Tipos de actividades"""

    call = "call"
    email = "email"
    meeting = "meeting"
    demo = "demo"
    proposal = "proposal"
    follow_up = "follow_up"
    task = "task"
    note = "note"


class ActivityStatus(str, Enum):
    """Estados de las actividades"""

    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class ReportType(str, Enum):
    """Tipos de reportes"""

    leads = "leads"
    opportunities = "opportunities"
    activities = "activities"
    revenue = "revenue"
    conversion = "conversion"
    performance = "performance"


# ===================== ESQUEMAS DE LEADS =====================


class LeadCreateRequest(BaseModel):
    """Esquema para crear un nuevo lead"""

    name: str = Field(..., min_length=1, max_length=255, description="Nombre del lead")
    email: EmailStr = Field(..., description="Email del lead")
    phone: Optional[str] = Field(None, max_length=20, description="Teléfono del lead")
    company: Optional[str] = Field(None, max_length=255, description="Empresa del lead")
    position: Optional[str] = Field(
        None, max_length=100, description="Posición del lead"
    )
    source: Optional[LeadSource] = Field(LeadSource.api, description="Fuente del lead")
    notes: Optional[str] = Field(
        None, max_length=2000, description="Notas sobre el lead"
    )
    custom_fields: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Campos personalizados"
    )

    @validator("phone")
    def validate_phone(cls, v):
        if v and len(v.replace(" ", "").replace("-", "").replace("+", "")) < 7:
            raise ValueError("Phone number must be valid")
        return v


class LeadUpdateRequest(BaseModel):
    """Esquema para actualizar un lead"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=255)
    position: Optional[str] = Field(None, max_length=100)
    status: Optional[LeadStatus] = None
    score: Optional[int] = Field(None, ge=0, le=100, description="Lead score (0-100)")
    notes: Optional[str] = Field(None, max_length=2000)
    custom_fields: Optional[Dict[str, Any]] = None


class LeadResponse(BaseModel):
    """Esquema de respuesta para leads"""

    id: str
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    status: LeadStatus
    score: int = 0
    source: LeadSource
    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None
    created_by: str
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_activity: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Esquema de respuesta para lista de leads"""

    leads: List[LeadResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# ===================== ESQUEMAS DE OPORTUNIDADES =====================


class OpportunityCreateRequest(BaseModel):
    """Esquema para crear una nueva oportunidad"""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Nombre de la oportunidad"
    )
    amount: float = Field(..., ge=0, description="Valor de la oportunidad")
    stage: Optional[OpportunityStage] = Field(
        OpportunityStage.qualification, description="Etapa de la oportunidad"
    )
    probability: Optional[int] = Field(
        25, ge=0, le=100, description="Probabilidad de cierre (0-100)"
    )
    close_date: date = Field(..., description="Fecha esperada de cierre")
    lead_id: Optional[str] = Field(None, description="ID del lead asociado")
    description: Optional[str] = Field(
        None, max_length=2000, description="Descripción de la oportunidad"
    )
    custom_fields: Optional[Dict[str, Any]] = Field(default_factory=dict)


class OpportunityUpdateRequest(BaseModel):
    """Esquema para actualizar una oportunidad"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[float] = Field(None, ge=0)
    stage: Optional[OpportunityStage] = None
    probability: Optional[int] = Field(None, ge=0, le=100)
    close_date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=2000)
    custom_fields: Optional[Dict[str, Any]] = None


class OpportunityResponse(BaseModel):
    """Esquema de respuesta para oportunidades"""

    id: str
    name: str
    amount: float
    stage: OpportunityStage
    probability: int
    close_date: date
    lead_id: Optional[str] = None
    owner_id: str
    description: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===================== ESQUEMAS DE CONTACTOS =====================


class ContactCreateRequest(BaseModel):
    """Esquema para crear un nuevo contacto"""

    first_name: str = Field(
        ..., min_length=1, max_length=100, description="Nombre del contacto"
    )
    last_name: str = Field(
        ..., min_length=1, max_length=100, description="Apellido del contacto"
    )
    email: EmailStr = Field(..., description="Email del contacto")
    phone: Optional[str] = Field(
        None, max_length=20, description="Teléfono del contacto"
    )
    company: Optional[str] = Field(
        None, max_length=255, description="Empresa del contacto"
    )
    position: Optional[str] = Field(
        None, max_length=100, description="Posición del contacto"
    )
    lead_id: Optional[str] = Field(None, description="ID del lead asociado")
    notes: Optional[str] = Field(
        None, max_length=2000, description="Notas sobre el contacto"
    )


class ContactUpdateRequest(BaseModel):
    """Esquema para actualizar un contacto"""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=255)
    position: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=2000)


class ContactResponse(BaseModel):
    """Esquema de respuesta para contactos"""

    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    lead_id: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===================== ESQUEMAS DE ACTIVIDADES =====================


class ActivityCreateRequest(BaseModel):
    """Esquema para crear una nueva actividad"""

    type: ActivityType = Field(..., description="Tipo de actividad")
    subject: str = Field(
        ..., min_length=1, max_length=255, description="Asunto de la actividad"
    )
    description: Optional[str] = Field(
        None, max_length=2000, description="Descripción de la actividad"
    )
    due_date: Optional[datetime] = Field(None, description="Fecha de vencimiento")
    lead_id: Optional[str] = Field(None, description="ID del lead asociado")
    opportunity_id: Optional[str] = Field(
        None, description="ID de la oportunidad asociada"
    )
    contact_id: Optional[str] = Field(None, description="ID del contacto asociado")


class ActivityUpdateRequest(BaseModel):
    """Esquema para actualizar una actividad"""

    type: Optional[ActivityType] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[ActivityStatus] = None
    due_date: Optional[datetime] = None


class ActivityResponse(BaseModel):
    """Esquema de respuesta para actividades"""

    id: str
    type: ActivityType
    subject: str
    description: Optional[str] = None
    status: ActivityStatus
    due_date: Optional[datetime] = None
    lead_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    contact_id: Optional[str] = None
    assigned_to: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ===================== ESQUEMAS DE DASHBOARD Y MÉTRICAS =====================


class PipelineResponse(BaseModel):
    """Esquema de respuesta para pipeline"""

    stage: str
    count: int
    total_value: float
    average_value: float


class DashboardResponse(BaseModel):
    """Esquema de respuesta para dashboard"""

    leads_count: int
    opportunities_count: int
    revenue_total: float
    conversion_rate: float
    recent_activities: List[ActivityResponse]
    pipeline_stats: List[PipelineResponse]
    period: str


# ===================== ESQUEMAS DE REPORTES =====================


class ReportRequest(BaseModel):
    """Esquema para solicitar un reporte"""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Nombre del reporte"
    )
    type: ReportType = Field(..., description="Tipo de reporte")
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="Filtros del reporte"
    )
    date_from: Optional[date] = Field(None, description="Fecha de inicio")
    date_to: Optional[date] = Field(None, description="Fecha de fin")
    format: Optional[str] = Field(
        "json", description="Formato del reporte (json, csv, pdf)"
    )

    @validator("date_to")
    def validate_date_range(cls, v, values):
        if v and "date_from" in values and values["date_from"]:
            if v < values["date_from"]:
                raise ValueError("date_to must be after date_from")
        return v


class ReportResponse(BaseModel):
    """Esquema de respuesta para reportes"""

    id: str
    name: str
    type: ReportType
    filters: Dict[str, Any]
    data: List[Dict[str, Any]]
    generated_at: datetime
    generated_by: str
    format: str = "json"

    class Config:
        from_attributes = True


# ===================== ESQUEMAS DE BÚSQUEDA Y FILTROS =====================


class SearchRequest(BaseModel):
    """Esquema para búsquedas"""

    query: str = Field(
        ..., min_length=1, max_length=255, description="Término de búsqueda"
    )
    entity_types: Optional[List[str]] = Field(
        default=["leads", "contacts", "opportunities"],
        description="Tipos de entidades a buscar",
    )
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Filtros adicionales"
    )


class SearchResult(BaseModel):
    """Resultado de búsqueda"""

    entity_type: str
    entity_id: str
    title: str
    description: Optional[str] = None
    score: float
    highlights: Optional[Dict[str, List[str]]] = None


class SearchResponse(BaseModel):
    """Esquema de respuesta para búsquedas"""

    results: List[SearchResult]
    total: int
    query: str
    took: float  # Tiempo en segundos


# ===================== ESQUEMAS DE INTEGRACIÓN =====================


class WebhookEvent(BaseModel):
    """Esquema para eventos de webhook"""

    event_type: str
    entity_type: str
    entity_id: str
    data: Dict[str, Any]
    timestamp: datetime
    source: str


class IntegrationConfig(BaseModel):
    """Configuración de integración"""

    name: str
    type: str
    enabled: bool
    config: Dict[str, Any]
    webhook_url: Optional[str] = None


# ===================== ESQUEMAS DE NOTIFICACIONES =====================


class NotificationRequest(BaseModel):
    """Esquema para crear notificaciones"""

    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=1000)
    type: str = Field(
        "info", description="Tipo de notificación (info, warning, error, success)"
    )
    user_id: Optional[str] = Field(
        None, description="ID del usuario (si es None, se envía a todos)"
    )
    entity_type: Optional[str] = Field(None, description="Tipo de entidad relacionada")
    entity_id: Optional[str] = Field(None, description="ID de la entidad relacionada")


class NotificationResponse(BaseModel):
    """Esquema de respuesta para notificaciones"""

    id: str
    title: str
    message: str
    type: str
    read: bool
    user_id: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ===================== ESQUEMAS PARA INTEGRACIONES EXTERNAS =====================


class ExternalLeadImport(BaseModel):
    """Esquema para importar leads externos"""

    source: str
    leads: List[Dict[str, Any]]
    mapping: Dict[str, str]  # Mapeo de campos externos a campos internos
    import_options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ImportResult(BaseModel):
    """Resultado de importación"""

    total_records: int
    successful_imports: int
    failed_imports: int
    errors: List[Dict[str, Any]]
    import_id: str
    status: str
