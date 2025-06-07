# app/auth/middleware.py
import logging
from typing import Optional, List, Callable
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import wraps

from app.auth.auth_client import AuthenticationClient
from app.auth.utils import get_client_ip, get_user_agent
from app.schemas.auth_schema import UserRole, TokenValidationResponse
from app.models.user import User

logger = logging.getLogger(__name__)

# Inicializar esquema de seguridad
security = HTTPBearer()


class AuthMiddleware:
    """Middleware de autenticación para FastAPI"""

    def __init__(self):
        self.auth_client = AuthenticationClient()

    async def get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> User:
        """Obtener usuario actual desde el token"""
        try:
            # Validar token
            token_data = await self.auth_client.validate_token(credentials.credentials)

            if not token_data.valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Obtener usuario completo
            user = await self.auth_client.get_user_by_id(token_data.user_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is disabled",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def get_current_active_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> User:
        """Obtener usuario activo (wrapper para compatibilidad)"""
        return await self.get_current_user(credentials)

    def require_roles(self, allowed_roles: List[UserRole]):
        """Decorator para requerir roles específicos"""

        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Buscar el usuario en los argumentos
                current_user = None
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break

                if not current_user:
                    for value in kwargs.values():
                        if isinstance(value, User):
                            current_user = value
                            break

                if not current_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )

                if current_user.role not in allowed_roles:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions. Required roles: {[role.value for role in allowed_roles]}",
                    )

                return await func(*args, **kwargs)

            return wrapper

        return decorator

    def require_admin(self):
        """Decorator que requiere rol de administrador"""
        return self.require_roles([UserRole.ADMIN])

    def require_manager_or_admin(self):
        """Decorator que requiere rol de manager o admin"""
        return self.require_roles([UserRole.ADMIN, UserRole.MANAGER])

    async def get_optional_user(self, request: Request) -> Optional[User]:
        """Obtener usuario opcional (no requerido)"""
        try:
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            token = auth_header.split(" ")[1]
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=token
            )
            return await self.get_current_user(credentials)
        except HTTPException:
            return None
        except Exception as e:
            logger.warning(f"Optional auth error: {e}")
            return None


# Instancia global del middleware
auth_middleware = AuthMiddleware()

# Dependencias para usar en las rutas
get_current_user = auth_middleware.get_current_user
get_current_active_user = auth_middleware.get_current_active_user
get_optional_user = auth_middleware.get_optional_user
require_roles = auth_middleware.require_roles
require_admin = auth_middleware.require_admin
require_manager_or_admin = auth_middleware.require_manager_or_admin


# ===================== DEPENDENCIAS ESPECÍFICAS =====================


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Obtener usuario con rol de administrador"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user


async def get_manager_user(current_user: User = Depends(get_current_user)) -> User:
    """Obtener usuario con rol de manager o superior"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Manager access required"
        )
    return current_user


async def get_agent_user(current_user: User = Depends(get_current_user)) -> User:
    """Obtener usuario con rol de agente o superior"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Agent access required"
        )
    return current_user


# ===================== MIDDLEWARE DE LOGGING =====================


class RequestLoggingMiddleware:
    """Middleware para logging de requests autenticados"""

    def __init__(self):
        self.auth_client = AuthenticationClient()

    async def log_request(self, request: Request, current_user: Optional[User] = None):
        """Registrar request en logs de auditoría"""
        try:
            if current_user:
                details = {
                    "method": request.method,
                    "url": str(request.url),
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                }

                await self.auth_client._log_auth_event(
                    user_id=str(current_user.id),
                    email=current_user.email,
                    action="api_request",
                    success=True,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    details=details,
                )
        except Exception as e:
            logger.error(f"Request logging error: {e}")


# ===================== RATE LIMITING =====================


class RateLimitMiddleware:
    """Middleware básico de rate limiting"""

    def __init__(self):
        self.requests = {}  # En producción usar Redis

    async def check_rate_limit(
        self, request: Request, current_user: Optional[User] = None, limit: int = 100
    ):
        """Verificar límite de requests"""
        try:
            # Identificar cliente
            if current_user:
                client_id = f"user:{current_user.id}"
            else:
                client_id = f"ip:{request.client.host if request.client else 'unknown'}"

            # Verificar límite (implementación básica)
            # En producción implementar con Redis y sliding window
            current_count = self.requests.get(client_id, 0)

            if current_count >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )

            self.requests[client_id] = current_count + 1

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limit error: {e}")


# ===================== UTILIDADES DE SEGURIDAD =====================
# Las funciones get_client_ip y get_user_agent se importan desde app.auth.utils


def is_secure_request(request: Request) -> bool:
    """Verificar si el request es seguro (HTTPS)"""
    return (
        request.url.scheme == "https"
        or request.headers.get("X-Forwarded-Proto") == "https"
    )


# ===================== DECORADORES DE SEGURIDAD =====================


def require_https(func: Callable):
    """Decorator que requiere HTTPS"""

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not is_secure_request(request):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="HTTPS required"
            )
        return await func(request, *args, **kwargs)

    return wrapper


def require_2fa(func: Callable):
    """Decorator que requiere 2FA habilitado"""

    @wraps(func)
    async def wrapper(current_user: User, *args, **kwargs):
        if not current_user.has_2fa:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Two-factor authentication required for this action",
            )
        return await func(current_user, *args, **kwargs)

    return wrapper


# ===================== INSTANCIAS GLOBALES =====================

request_logger = RequestLoggingMiddleware()
rate_limiter = RateLimitMiddleware()


# ===================== FUNCIONES DE VALIDACIÓN =====================


async def validate_api_key(api_key: str) -> Optional[User]:
    """Validar API key y retornar usuario asociado"""
    try:
        # Implementar validación de API key
        # Por ahora retornamos None
        return None
    except Exception as e:
        logger.error(f"API key validation error: {e}")
        return None


async def validate_webhook_signature(request: Request, secret: str) -> bool:
    """Validar firma de webhook"""
    try:
        # Implementar validación de firma de webhook
        # Por ahora retornamos True
        return True
    except Exception as e:
        logger.error(f"Webhook signature validation error: {e}")
        return False


# ===================== EXCEPCIONES PERSONALIZADAS =====================


class AuthenticationError(Exception):
    """Error de autenticación personalizado"""

    pass


class InsufficientPermissionsError(Exception):
    """Error de permisos insuficientes"""

    pass


class RateLimitExceededError(Exception):
    """Error de límite de requests excedido"""

    pass


class SecurityViolationError(Exception):
    """Error de violación de seguridad"""

    pass
