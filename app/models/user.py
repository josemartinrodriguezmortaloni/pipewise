# app/models/user.py
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from app.schemas.auth_schema import UserRole, AuthProvider


class User(BaseModel):
    """Modelo de usuario principal"""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    email: EmailStr
    full_name: str
    company: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True
    email_confirmed: bool = False

    # Campos de autenticación
    auth_provider: AuthProvider = AuthProvider.EMAIL
    password_hash: Optional[str] = None  # Solo para auth local
    external_id: Optional[str] = None  # Para OAuth providers

    # 2FA
    has_2fa: bool = False
    totp_secret: Optional[str] = None
    backup_codes: Optional[list[str]] = None

    # Metadatos
    metadata: Optional[Dict[str, Any]] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    last_activity: Optional[datetime] = None

    # Configuración de cuenta
    preferences: Optional[Dict[str, Any]] = None
    timezone: Optional[str] = "UTC"
    language: Optional[str] = "en"


class UserSession(BaseModel):
    """Modelo de sesión de usuario"""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    user_id: UUID
    session_token: str
    refresh_token: str

    # Información del dispositivo/cliente
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Timestamps y expiración
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    expires_at: datetime

    # Estado
    is_active: bool = True
    revoked: bool = False
    revoked_at: Optional[datetime] = None


class AuthAuditLog(BaseModel):
    """Modelo para logs de auditoría de autenticación"""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    user_id: Optional[UUID] = None
    email: Optional[str] = None

    # Acción realizada
    action: str  # login, logout, register, password_change, 2fa_enable, etc.
    success: bool
    error_message: Optional[str] = None

    # Contexto de la acción
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[str] = None

    # Detalles adicionales
    details: Optional[Dict[str, Any]] = None

    # Timestamp
    timestamp: Optional[datetime] = None


class PasswordResetToken(BaseModel):
    """Modelo para tokens de reset de contraseña"""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    user_id: UUID
    token: str
    expires_at: datetime
    used: bool = False
    used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class EmailConfirmationToken(BaseModel):
    """Modelo para tokens de confirmación de email"""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    user_id: UUID
    email: str
    token: str
    expires_at: datetime
    confirmed: bool = False
    confirmed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class UserInvitation(BaseModel):
    """Modelo para invitaciones de usuario"""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    email: EmailStr
    invited_by: UUID  # User ID que envió la invitación
    role: UserRole = UserRole.USER
    company: Optional[str] = None

    # Token y expiración
    token: str
    expires_at: datetime

    # Estado
    accepted: bool = False
    accepted_at: Optional[datetime] = None

    # Timestamps
    created_at: Optional[datetime] = None

    # Metadatos
    metadata: Optional[Dict[str, Any]] = None


class OAuth2State(BaseModel):
    """Modelo para mantener estado de OAuth2"""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    state: str
    provider: AuthProvider
    redirect_uri: str
    user_id: Optional[UUID] = None  # Para linking accounts

    # Datos adicionales
    code_verifier: Optional[str] = None  # Para PKCE
    nonce: Optional[str] = None

    # Expiración
    expires_at: datetime
    created_at: Optional[datetime] = None


class UserPreferences(BaseModel):
    """Modelo para preferencias de usuario"""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID

    # Preferencias de notificaciones
    email_notifications: bool = True
    push_notifications: bool = True
    marketing_emails: bool = False

    # Preferencias de UI
    theme: str = "light"  # light, dark, auto
    language: str = "en"
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    time_format: str = "24"  # 12 or 24

    # Preferencias de seguridad
    session_timeout: int = 3600  # segundos
    require_2fa_for_sensitive: bool = False

    # Preferencias del CRM
    default_lead_view: str = "list"  # list, kanban, table
    leads_per_page: int = 50
    auto_follow_leads: bool = True

    # Metadatos
    updated_at: Optional[datetime] = None


class APIKey(BaseModel):
    """Modelo para API Keys de usuario"""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    user_id: UUID
    name: str  # Nombre descriptivo del API key
    key_hash: str  # Hash del API key
    key_prefix: str  # Primeros caracteres para identificación

    # Permisos y restricciones
    scopes: list[str] = []  # Permisos específicos
    rate_limit: Optional[int] = None  # Requests por minuto
    ip_whitelist: Optional[list[str]] = None

    # Estado
    is_active: bool = True

    # Uso y estadísticas
    last_used: Optional[datetime] = None
    usage_count: int = 0

    # Expiración
    expires_at: Optional[datetime] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LoginAttempt(BaseModel):
    """Modelo para tracking de intentos de login"""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    email: str
    ip_address: str
    user_agent: Optional[str] = None

    # Resultado del intento
    success: bool
    failure_reason: Optional[str] = None  # wrong_password, account_locked, etc.

    # Contexto de seguridad
    suspicious: bool = False
    blocked: bool = False

    # Timestamp
    attempted_at: Optional[datetime] = None

    # Metadatos adicionales
    metadata: Optional[Dict[str, Any]] = None


class SecurityAlert(BaseModel):
    """Modelo para alertas de seguridad"""

    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    user_id: UUID
    alert_type: str  # suspicious_login, new_device, password_change, etc.
    severity: str  # low, medium, high, critical

    # Descripción
    title: str
    description: str

    # Contexto
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    location: Optional[str] = None

    # Estado
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    # Metadatos
    metadata: Optional[Dict[str, Any]] = None

    # Timestamp
    created_at: Optional[datetime] = None
