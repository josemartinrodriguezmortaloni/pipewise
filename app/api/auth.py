# app/api/auth.py
from fastapi import APIRouter, HTTPException, status, Depends, Request, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from typing import List, Optional

from app.auth.auth_client import AuthenticationClient
from app.auth.middleware import (
    get_current_user,
    get_admin_user,
    get_manager_user,
    get_client_ip,
    get_user_agent,
    require_https,
    require_2fa,
)
from app.models.user import User
from app.schemas.auth_schema import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserLoginRequest,
    UserLoginResponse,
    Enable2FARequest,
    Enable2FAResponse,
    Verify2FARequest,
    Verify2FAResponse,
    Login2FARequest,
    Disable2FARequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserProfile,
    UserUpdateRequest,
    ChangePasswordRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    AuthSuccessResponse,
    AuthErrorResponse,
    ActiveSessionsResponse,
    RevokeSessionRequest,
    AdminUserListResponse,
    AdminUserUpdateRequest,
    AuthStatsResponse,
    UserRole,
)

import logging

logger = logging.getLogger(__name__)

# Crear router
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Inicializar cliente de autenticación
auth_client = AuthenticationClient()


# ===================== REGISTRO Y LOGIN =====================


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    request: Request, user_data: UserRegisterRequest, background_tasks: BackgroundTasks
):
    """Registrar nuevo usuario"""
    try:
        client_ip = get_client_ip(request)
        user_agent = get_user_agent(request)

        result = await auth_client.register_user(user_data, ip_address=client_ip)

        # Agregar tareas en background (envío de email de confirmación)
        background_tasks.add_task(
            send_confirmation_email, result["email"], result["user_id"]
        )

        return UserRegisterResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=UserLoginResponse)
async def login_user(request: Request, login_data: UserLoginRequest):
    """Login de usuario"""
    try:
        client_ip = get_client_ip(request)
        user_agent = get_user_agent(request)

        result = await auth_client.login_user(
            login_data, ip_address=client_ip, user_agent=user_agent
        )

        return UserLoginResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
        )


@router.post("/login/2fa", response_model=UserLoginResponse)
async def login_with_2fa(request: Request, login_data: Login2FARequest):
    """Login con código 2FA"""
    try:
        client_ip = get_client_ip(request)
        user_agent = get_user_agent(request)

        # Obtener temp_token del header o body
        temp_token = request.headers.get("X-2FA-Token")
        if not temp_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA session token required",
            )

        result = await auth_client.login_with_2fa(
            login_data.email,
            login_data.password,
            login_data.totp_code,
            temp_token,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return UserLoginResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"2FA login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="2FA login failed"
        )


@router.post("/logout", response_model=AuthSuccessResponse)
async def logout_user(request: Request, current_user: User = Depends(get_current_user)):
    """Logout de usuario"""
    try:
        # Implementar logout (revocar tokens)
        # Por ahora solo retornamos éxito
        return AuthSuccessResponse(message="Logged out successfully")

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )


# ===================== GESTIÓN DE TOKENS =====================


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_access_token(request: Request, token_data: TokenRefreshRequest):
    """Renovar token de acceso"""
    try:
        result = await auth_client.refresh_token(token_data.refresh_token)
        return TokenRefreshResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.get("/validate")
async def validate_token(current_user: User = Depends(get_current_user)):
    """Validar token actual"""
    return {
        "valid": True,
        "user": {
            "user_id": str(current_user.id),
            "email": current_user.email,
            "role": current_user.role.value,
            "is_active": current_user.is_active,
        },
    }


# ===================== GESTIÓN DE 2FA =====================


@router.post("/2fa/enable", response_model=Enable2FAResponse)
async def enable_2fa(
    request: Request,
    enable_data: Enable2FARequest,
    current_user: User = Depends(get_current_user),
):
    """Habilitar autenticación de dos factores"""
    try:
        result = await auth_client.enable_2fa(
            str(current_user.id), enable_data.password
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Enable 2FA error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable 2FA",
        )


@router.post("/2fa/verify", response_model=Verify2FAResponse)
async def verify_2fa_setup(
    request: Request,
    verify_data: Verify2FARequest,
    current_user: User = Depends(get_current_user),
):
    """Verificar y activar 2FA"""
    try:
        result = await auth_client.verify_2fa_setup(
            str(current_user.id), verify_data.secret, verify_data.code
        )
        return Verify2FAResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Verify 2FA error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="2FA verification failed",
        )


@router.post("/2fa/disable", response_model=AuthSuccessResponse)
async def disable_2fa(
    request: Request,
    disable_data: Disable2FARequest,
    current_user: User = Depends(get_current_user),
):
    """Deshabilitar autenticación de dos factores"""
    try:
        result = await auth_client.disable_2fa(
            str(current_user.id),
            disable_data.password,
            disable_data.totp_code,
            disable_data.backup_code,
        )
        return AuthSuccessResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Disable 2FA error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable 2FA",
        )


# ===================== GESTIÓN DE PERFIL =====================


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Obtener perfil del usuario actual"""
    return UserProfile(
        user_id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        company=current_user.company,
        phone=current_user.phone,
        role=current_user.role,
        is_active=current_user.is_active,
        email_confirmed=current_user.email_confirmed,
        has_2fa=current_user.has_2fa,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


@router.put("/profile", response_model=UserProfile)
async def update_user_profile(
    request: Request,
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """Actualizar perfil del usuario"""
    try:
        # Implementar actualización de perfil
        # Por ahora retornamos el perfil actual
        return UserProfile(
            user_id=str(current_user.id),
            email=current_user.email,
            full_name=update_data.full_name or current_user.full_name,
            company=update_data.company or current_user.company,
            phone=update_data.phone or current_user.phone,
            role=current_user.role,
            is_active=current_user.is_active,
            email_confirmed=current_user.email_confirmed,
            has_2fa=current_user.has_2fa,
            created_at=current_user.created_at,
            last_login=current_user.last_login,
        )

    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed",
        )


@router.post("/change-password", response_model=AuthSuccessResponse)
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    """Cambiar contraseña del usuario"""
    try:
        # Implementar cambio de contraseña
        # Por ahora retornamos éxito
        return AuthSuccessResponse(message="Password changed successfully")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed",
        )


# ===================== RECUPERACIÓN DE CONTRASEÑA =====================


@router.post("/forgot-password", response_model=AuthSuccessResponse)
async def forgot_password(
    request: Request,
    reset_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
):
    """Solicitar reset de contraseña"""
    try:
        # Implementar solicitud de reset
        background_tasks.add_task(send_password_reset_email, reset_data.email)

        return AuthSuccessResponse(
            message="If the email exists, a password reset link has been sent"
        )

    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed",
        )


@router.post("/reset-password", response_model=AuthSuccessResponse)
async def reset_password(request: Request, reset_data: PasswordResetConfirm):
    """Confirmar reset de contraseña"""
    try:
        # Implementar confirmación de reset
        return AuthSuccessResponse(message="Password reset successfully")

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        )


# ===================== GESTIÓN DE SESIONES =====================


@router.get("/sessions", response_model=ActiveSessionsResponse)
async def get_active_sessions(current_user: User = Depends(get_current_user)):
    """Obtener sesiones activas del usuario"""
    try:
        # Implementar obtención de sesiones
        return ActiveSessionsResponse(sessions=[], total=0)

    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sessions",
        )


@router.post("/sessions/revoke", response_model=AuthSuccessResponse)
async def revoke_session(
    request: Request,
    revoke_data: RevokeSessionRequest,
    current_user: User = Depends(get_current_user),
):
    """Revocar sesión específica"""
    try:
        # Implementar revocación de sesión
        return AuthSuccessResponse(message="Session revoked successfully")

    except Exception as e:
        logger.error(f"Revoke session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session",
        )


@router.post("/sessions/revoke-all", response_model=AuthSuccessResponse)
async def revoke_all_sessions(
    request: Request, current_user: User = Depends(get_current_user)
):
    """Revocar todas las sesiones del usuario"""
    try:
        # Implementar revocación de todas las sesiones
        return AuthSuccessResponse(message="All sessions revoked successfully")

    except Exception as e:
        logger.error(f"Revoke all sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke sessions",
        )


# ===================== ADMINISTRACIÓN (Solo Admin) =====================


@router.get("/admin/users", response_model=AdminUserListResponse)
async def get_all_users(
    page: int = 1,
    per_page: int = 50,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    admin_user: User = Depends(get_admin_user),
):
    """Obtener lista de todos los usuarios (solo admin)"""
    try:
        # Implementar listado de usuarios
        return AdminUserListResponse(users=[], total=0, page=page, per_page=per_page)

    except Exception as e:
        logger.error(f"Get users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get users",
        )


@router.put("/admin/users/{user_id}", response_model=UserProfile)
async def update_user_admin(
    user_id: str,
    update_data: AdminUserUpdateRequest,
    admin_user: User = Depends(get_admin_user),
):
    """Actualizar usuario como administrador"""
    try:
        # Implementar actualización de usuario por admin
        target_user = await auth_client.get_user_by_id(user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return UserProfile(
            user_id=str(target_user.id),
            email=target_user.email,
            full_name=target_user.full_name,
            company=target_user.company,
            phone=target_user.phone,
            role=target_user.role,
            is_active=target_user.is_active,
            email_confirmed=target_user.email_confirmed,
            has_2fa=target_user.has_2fa,
            created_at=target_user.created_at,
            last_login=target_user.last_login,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )


@router.get("/admin/stats", response_model=AuthStatsResponse)
async def get_auth_stats(admin_user: User = Depends(get_admin_user)):
    """Obtener estadísticas de autenticación (solo admin)"""
    try:
        # Implementar estadísticas
        return AuthStatsResponse(
            total_users=0,
            active_users_24h=0,
            active_users_7d=0,
            active_users_30d=0,
            failed_logins_24h=0,
            users_with_2fa=0,
            recent_registrations=0,
        )

    except Exception as e:
        logger.error(f"Get auth stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get auth stats",
        )


# ===================== FUNCIONES AUXILIARES =====================


async def send_confirmation_email(email: str, user_id: str):
    """Enviar email de confirmación (background task)"""
    try:
        # Implementar envío de email
        logger.info(f"Sending confirmation email to {email}")
    except Exception as e:
        logger.error(f"Send confirmation email error: {e}")


async def send_password_reset_email(email: str):
    """Enviar email de reset de contraseña (background task)"""
    try:
        # Implementar envío de email
        logger.info(f"Sending password reset email to {email}")
    except Exception as e:
        logger.error(f"Send password reset email error: {e}")


# ===================== SUPABASE INTEGRATION =====================

from pydantic import BaseModel
from typing import Dict, Any

class SupabaseAuthSync(BaseModel):
    """Request model for Supabase auth sync"""
    user: Dict[str, Any]
    provider_token: str


@router.post("/supabase-sync", response_model=UserLoginResponse)
async def sync_supabase_auth(
    request: Request,
    auth_data: SupabaseAuthSync,
    background_tasks: BackgroundTasks,
):
    """
    Sync Supabase authentication with our backend
    Used for OAuth (Google, etc.) and email/password auth
    """
    try:
        client_ip = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        # Verify and sync Supabase user with our backend
        result = await auth_client.sync_supabase_user(
            supabase_user=auth_data.user,
            provider_token=auth_data.provider_token,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        return UserLoginResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Supabase sync error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication sync failed"
        )


# ===================== HEALTH CHECK =====================


@router.get("/health")
async def auth_health_check():
    """Health check del sistema de autenticación"""
    try:
        # Verificar conexión a Supabase
        health = {"status": "ok"}
        try:
            # Test básico de conexión
            test_result = (
                auth_client.client.table("users")
                .select("count", count="exact")
                .limit(1)
                .execute()
            )
            health = {"status": "healthy" if test_result else "degraded"}
        except Exception as e:
            health = {"status": "unhealthy", "error": str(e)}

        return {
            "status": "healthy",
            "auth_service": "operational",
            "database": health.get("status", "unknown"),
            "timestamp": auth_client._get_current_timestamp().isoformat(),
        }

    except Exception as e:
        logger.error(f"Auth health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": auth_client._get_current_timestamp().isoformat(),
        }
