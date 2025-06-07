# app/schemas/auth_schema.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """Roles de usuario en el sistema"""

    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    USER = "user"


class AuthProvider(str, Enum):
    """Proveedores de autenticación"""

    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"


# ===================== ESQUEMAS DE REGISTRO =====================


class UserRegisterRequest(BaseModel):
    """Esquema para registro de usuario"""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    company: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: UserRole = UserRole.USER

    @validator("password")
    def validate_password(cls, v):
        """Validar complejidad de contraseña"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class UserRegisterResponse(BaseModel):
    """Respuesta de registro exitoso"""

    user_id: str
    email: str
    full_name: str
    role: UserRole
    email_confirmed: bool = False
    message: str = (
        "User registered successfully. Please check your email for confirmation."
    )


# ===================== ESQUEMAS DE LOGIN =====================


class UserLoginRequest(BaseModel):
    """Esquema para login de usuario"""

    email: EmailStr
    password: str
    remember_me: bool = False


class UserLoginResponse(BaseModel):
    """Respuesta de login exitoso"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserProfile"
    requires_2fa: bool = False

    class Config:
        from_attributes = True


# ===================== ESQUEMAS DE 2FA =====================


class Enable2FARequest(BaseModel):
    """Solicitud para habilitar 2FA"""

    password: str  # Confirmar identidad


class Enable2FAResponse(BaseModel):
    """Respuesta con datos para configurar 2FA"""

    secret: str
    qr_code_url: str
    backup_codes: list[str]
    message: str = "Scan QR code with Google Authenticator and verify with a code"


class Verify2FARequest(BaseModel):
    """Verificar código 2FA durante setup"""

    secret: str
    code: str = Field(..., min_length=6, max_length=6)


class Verify2FAResponse(BaseModel):
    """Respuesta de verificación 2FA"""

    success: bool
    message: str
    backup_codes: Optional[list[str]] = None


class Login2FARequest(BaseModel):
    """Login con código 2FA"""

    email: EmailStr
    password: str
    totp_code: str = Field(..., min_length=6, max_length=6)
    remember_me: bool = False


class Disable2FARequest(BaseModel):
    """Deshabilitar 2FA"""

    password: str
    totp_code: Optional[str] = None  # Si está habilitado
    backup_code: Optional[str] = None  # Alternativa


# ===================== ESQUEMAS DE TOKEN =====================


class TokenRefreshRequest(BaseModel):
    """Renovar token de acceso"""

    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Nueva respuesta de token"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenValidationResponse(BaseModel):
    """Respuesta de validación de token"""

    valid: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    expires_at: Optional[datetime] = None


# ===================== ESQUEMAS DE USUARIO =====================


class UserProfile(BaseModel):
    """Perfil público del usuario"""

    user_id: str
    email: str
    full_name: str
    company: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    email_confirmed: bool
    has_2fa: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """Actualizar perfil de usuario"""

    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    company: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class ChangePasswordRequest(BaseModel):
    """Cambiar contraseña"""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @validator("new_password")
    def validate_new_password(cls, v):
        """Validar complejidad de nueva contraseña"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


# ===================== ESQUEMAS DE RECUPERACIÓN =====================


class PasswordResetRequest(BaseModel):
    """Solicitar reset de contraseña"""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirmar reset de contraseña"""

    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @validator("new_password")
    def validate_password(cls, v):
        """Validar nueva contraseña"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class EmailConfirmRequest(BaseModel):
    """Confirmar email"""

    token: str


# ===================== ESQUEMAS DE SESIÓN =====================


class SessionInfo(BaseModel):
    """Información de sesión activa"""

    session_id: str
    user_id: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_current: bool = False


class ActiveSessionsResponse(BaseModel):
    """Lista de sesiones activas"""

    sessions: list[SessionInfo]
    total: int


class RevokeSessionRequest(BaseModel):
    """Revocar sesión específica"""

    session_id: str


# ===================== ESQUEMAS DE ADMINISTRACIÓN =====================


class AdminUserListResponse(BaseModel):
    """Lista de usuarios para admin"""

    users: list[UserProfile]
    total: int
    page: int
    per_page: int


class AdminUserUpdateRequest(BaseModel):
    """Actualizar usuario como admin"""

    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    email_confirmed: Optional[bool] = None


# ===================== ESQUEMAS DE OAUTH =====================


class OAuthLoginRequest(BaseModel):
    """Login con OAuth (Google, GitHub, etc.)"""

    provider: AuthProvider
    code: str
    state: Optional[str] = None
    redirect_uri: str


class OAuthLoginResponse(BaseModel):
    """Respuesta de login OAuth"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile
    is_new_user: bool = False


# ===================== ESQUEMAS DE RESPUESTA GENERAL =====================


class AuthErrorResponse(BaseModel):
    """Respuesta de error de autenticación"""

    error: str
    error_description: str
    error_code: Optional[str] = None


class AuthSuccessResponse(BaseModel):
    """Respuesta de éxito general"""

    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


# ===================== ESQUEMAS DE AUDITORÍA =====================


class AuthAuditLog(BaseModel):
    """Log de auditoría de autenticación"""

    log_id: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    action: str  # login, logout, register, password_change, etc.
    success: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime


class AuthStatsResponse(BaseModel):
    """Estadísticas de autenticación"""

    total_users: int
    active_users_24h: int
    active_users_7d: int
    active_users_30d: int
    failed_logins_24h: int
    users_with_2fa: int
    recent_registrations: int


# Update forward references
UserLoginResponse.model_rebuild()
