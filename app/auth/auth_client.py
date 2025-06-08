# app/auth/auth_client.py
import os
import jwt
import pyotp
import qrcode
import secrets
import hashlib
import logging
from io import BytesIO
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID, uuid4
import base64

from supabase import create_client, Client
from gotrue.errors import AuthApiError
from passlib.context import CryptContext
from passlib.hash import bcrypt

from app.models.user import User, UserSession, AuthAuditLog
from app.schemas.auth_schema import (
    UserRegisterRequest,
    UserLoginRequest,
    UserRole,
    AuthProvider,
    Enable2FAResponse,
    TokenValidationResponse,
    UserProfile,
)

logger = logging.getLogger(__name__)


class AuthenticationClient:
    """Cliente completo de autenticación con Supabase y 2FA"""

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_ANON_KEY")
        self.jwt_secret = os.getenv("JWT_SECRET", "your-super-secret-jwt-key")
        self.jwt_algorithm = "HS256"
        self.access_token_expire_minutes = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )
        self.refresh_token_expire_days = int(
            os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")
        )

        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY environment variables required"
            )

        # Inicializar cliente Supabase
        self.client: Client = create_client(self.supabase_url, self.supabase_key)

        # Configurar encriptación de contraseñas
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        logger.info("Authentication client initialized")

    def _get_current_timestamp(self) -> datetime:
        """Obtener timestamp actual"""
        return datetime.now(timezone.utc)

    def _hash_password(self, password: str) -> str:
        """Generar hash de contraseña"""
        return self.pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar contraseña"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def _generate_secure_token(self, length: int = 32) -> str:
        """Generar token seguro aleatorio"""
        return secrets.token_urlsafe(length)

    def _generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generar códigos de respaldo para 2FA"""
        return [secrets.token_hex(4).upper() for _ in range(count)]

    # ===================== REGISTRO Y LOGIN =====================

    async def register_user(
        self, user_data: UserRegisterRequest, ip_address: str = None
    ) -> Dict[str, Any]:
        """Registrar nuevo usuario"""
        try:
            # Verificar si el usuario ya existe
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user:
                await self._log_auth_event(
                    email=user_data.email,
                    action="register_attempt",
                    success=False,
                    ip_address=ip_address,
                    error_message="Email already registered",
                )
                raise ValueError("Email already registered")

            # Crear usuario en Supabase Auth
            auth_response = self.client.auth.sign_up(
                {
                    "email": user_data.email,
                    "password": user_data.password,
                    "options": {
                        "data": {
                            "full_name": user_data.full_name,
                            "company": user_data.company,
                            "phone": user_data.phone,
                            "role": user_data.role.value,
                        }
                    },
                }
            )

            if not auth_response.user:
                raise Exception("Failed to create user in Supabase Auth")

            # Crear registro en nuestra tabla de usuarios
            user_dict = {
                "id": auth_response.user.id,
                "email": user_data.email,
                "full_name": user_data.full_name,
                "company": user_data.company,
                "phone": user_data.phone,
                "role": user_data.role.value,
                "auth_provider": AuthProvider.EMAIL.value,
                "password_hash": self._hash_password(user_data.password),
                "is_active": True,
                "email_confirmed": False,
                "has_2fa": False,
                "created_at": self._get_current_timestamp().isoformat(),
                "updated_at": self._get_current_timestamp().isoformat(),
                "preferences": {"theme": "light", "language": "en", "timezone": "UTC"},
            }

            result = self.client.table("users").insert(user_dict).execute()

            if not result.data:
                raise Exception("Failed to create user record")

            user = User(**result.data[0])

            # Log del evento de registro exitoso
            await self._log_auth_event(
                user_id=str(user.id),
                email=user.email,
                action="register",
                success=True,
                ip_address=ip_address,
            )

            # Iniciar sesión automáticamente después del registro
            access_token, refresh_token = await self._create_user_session(
                user, remember_me=True, ip_address=ip_address
            )

            # Log del evento de login
            await self._log_auth_event(
                user_id=str(user.id),
                email=user.email,
                action="login",
                success=True,
                ip_address=ip_address,
                details={"method": "after_registration"},
            )

            # Preparar perfil de usuario para la respuesta
            user_profile = self._user_to_profile(user)

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user_profile.model_dump(),
                "message": "User registered and logged in successfully.",
            }

        except AuthApiError as e:
            logger.error(f"Supabase Auth error during registration: {e}")
            await self._log_auth_event(
                email=user_data.email,
                action="register_attempt",
                success=False,
                ip_address=ip_address,
                error_message=str(e),
            )
            raise Exception(f"Registration failed: {e.message}")
        except Exception as e:
            logger.error(f"Registration error: {e}")
            raise

    async def login_user(
        self,
        login_data: UserLoginRequest,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Dict[str, Any]:
        """Login de usuario"""
        try:
            # Autenticar con Supabase Auth
            auth_response = self.client.auth.sign_in_with_password(
                {"email": login_data.email, "password": login_data.password}
            )

            if not auth_response.user:
                await self._log_auth_event(
                    email=login_data.email,
                    action="login_attempt",
                    success=False,
                    ip_address=ip_address,
                    error_message="Invalid credentials",
                )
                raise ValueError("Invalid email or password")

            # Obtener datos completos del usuario
            user = await self.get_user_by_id(auth_response.user.id)
            if not user:
                raise Exception("User not found in database")

            if not user.is_active:
                await self._log_auth_event(
                    user_id=str(user.id),
                    email=user.email,
                    action="login_attempt",
                    success=False,
                    ip_address=ip_address,
                    error_message="Account disabled",
                )
                raise ValueError("Account is disabled")

            # Verificar si requiere 2FA
            if user.has_2fa:
                # Generar token temporal para 2FA
                temp_token = self._generate_secure_token()

                # Guardar estado temporal (puedes usar Redis o base de datos)
                await self._store_2fa_temp_session(
                    user.id, temp_token, ip_address, user_agent
                )

                return {
                    "requires_2fa": True,
                    "temp_token": temp_token,
                    "message": "2FA code required",
                }

            # Generar tokens de sesión
            access_token, refresh_token = await self._create_user_session(
                user, login_data.remember_me, ip_address, user_agent
            )

            # Actualizar último login
            await self._update_last_login(user.id)

            # Log del evento
            await self._log_auth_event(
                user_id=str(user.id),
                email=user.email,
                action="login",
                success=True,
                ip_address=ip_address,
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
                "user": self._user_to_profile(user),
                "requires_2fa": False,
            }

        except AuthApiError as e:
            logger.error(f"Supabase Auth error during login: {e}")
            await self._log_auth_event(
                email=login_data.email,
                action="login_attempt",
                success=False,
                ip_address=ip_address,
                error_message=str(e),
            )
            raise ValueError("Invalid email or password")
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise

    async def login_with_2fa(
        self,
        email: str,
        password: str,
        totp_code: str,
        temp_token: str,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Dict[str, Any]:
        """Login con código 2FA"""
        try:
            # Verificar token temporal
            temp_session = await self._get_2fa_temp_session(temp_token)
            if not temp_session:
                raise ValueError("Invalid or expired 2FA session")

            # Obtener usuario
            user = await self.get_user_by_id(temp_session["user_id"])
            if not user or user.email != email:
                raise ValueError("Invalid 2FA session")

            # Verificar código TOTP
            if not self._verify_totp_code(user.totp_secret, totp_code):
                await self._log_auth_event(
                    user_id=str(user.id),
                    email=user.email,
                    action="2fa_login_attempt",
                    success=False,
                    ip_address=ip_address,
                    error_message="Invalid 2FA code",
                )
                raise ValueError("Invalid 2FA code")

            # Limpiar sesión temporal
            await self._cleanup_2fa_temp_session(temp_token)

            # Crear sesión completa
            access_token, refresh_token = await self._create_user_session(
                user, False, ip_address, user_agent
            )

            # Actualizar último login
            await self._update_last_login(user.id)

            # Log del evento
            await self._log_auth_event(
                user_id=str(user.id),
                email=user.email,
                action="2fa_login",
                success=True,
                ip_address=ip_address,
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
                "user": self._user_to_profile(user),
            }

        except Exception as e:
            logger.error(f"2FA login error: {e}")
            raise

    # ===================== GESTIÓN DE TOKENS =====================

    def _create_access_token(self, user_id: str, email: str, role: str) -> str:
        """Crear token de acceso JWT"""
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": self._get_current_timestamp()
            + timedelta(minutes=self.access_token_expire_minutes),
            "iat": self._get_current_timestamp(),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def _create_refresh_token(self, user_id: str) -> str:
        """Crear token de refresh"""
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": self._get_current_timestamp()
            + timedelta(days=self.refresh_token_expire_days),
            "iat": self._get_current_timestamp(),
            "jti": str(uuid4()),  # JWT ID único
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    async def validate_token(self, token: str) -> TokenValidationResponse:
        """Validar token de acceso"""
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )

            if payload.get("type") != "access":
                return TokenValidationResponse(valid=False)

            # Verificar que el usuario existe y está activo
            user = await self.get_user_by_id(payload["sub"])
            if not user or not user.is_active:
                return TokenValidationResponse(valid=False)

            return TokenValidationResponse(
                valid=True,
                user_id=payload["sub"],
                email=payload["email"],
                role=UserRole(payload["role"]),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            )

        except jwt.ExpiredSignatureError:
            return TokenValidationResponse(valid=False)
        except jwt.InvalidTokenError:
            return TokenValidationResponse(valid=False)
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return TokenValidationResponse(valid=False)

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Renovar token de acceso"""
        try:
            payload = jwt.decode(
                refresh_token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )

            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")

            # Verificar que la sesión existe y está activa
            session = await self._get_session_by_refresh_token(refresh_token)
            if not session or not session.is_active or session.revoked:
                raise ValueError("Invalid or revoked session")

            # Obtener usuario
            user = await self.get_user_by_id(payload["sub"])
            if not user or not user.is_active:
                raise ValueError("User not found or inactive")

            # Crear nuevo access token
            access_token = self._create_access_token(
                str(user.id), user.email, user.role.value
            )

            # Actualizar actividad de la sesión
            await self._update_session_activity(session.id)

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
            }

        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid refresh token")
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise

    # ===================== GESTIÓN DE 2FA =====================

    async def enable_2fa(self, user_id: str, password: str) -> Enable2FAResponse:
        """Habilitar 2FA para un usuario"""
        try:
            # Verificar usuario y contraseña
            user = await self.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")

            if not self._verify_password(password, user.password_hash):
                raise ValueError("Invalid password")

            if user.has_2fa:
                raise ValueError("2FA already enabled")

            # Generar secreto TOTP
            secret = pyotp.random_base32()

            # Generar códigos de respaldo
            backup_codes = self._generate_backup_codes()

            # Crear URL para QR code
            totp = pyotp.TOTP(secret)
            qr_url = totp.provisioning_uri(name=user.email, issuer_name="PipeWise CRM")

            # Generar código QR
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

            # Guardar temporalmente (no activar hasta verificar)
            await self._store_pending_2fa(user_id, secret, backup_codes)

            return Enable2FAResponse(
                secret=secret,
                qr_code_url=f"data:image/png;base64,{qr_code_base64}",
                backup_codes=backup_codes,
                message="Scan QR code with Google Authenticator and verify with a code",
            )

        except Exception as e:
            logger.error(f"Enable 2FA error: {e}")
            raise

    async def verify_2fa_setup(
        self, user_id: str, secret: str, code: str
    ) -> Dict[str, Any]:
        """Verificar y activar 2FA"""
        try:
            # Verificar código
            if not self._verify_totp_code(secret, code):
                raise ValueError("Invalid verification code")

            # Obtener datos pendientes
            pending_data = await self._get_pending_2fa(user_id)
            if not pending_data or pending_data["secret"] != secret:
                raise ValueError("Invalid setup session")

            # Activar 2FA en la base de datos
            hashed_backup_codes = [
                self._hash_password(code) for code in pending_data["backup_codes"]
            ]

            update_data = {
                "has_2fa": True,
                "totp_secret": secret,
                "backup_codes": hashed_backup_codes,
                "updated_at": self._get_current_timestamp().isoformat(),
            }

            result = (
                self.client.table("users")
                .update(update_data)
                .eq("id", user_id)
                .execute()
            )

            if not result.data:
                raise Exception("Failed to update user 2FA settings")

            # Limpiar datos pendientes
            await self._cleanup_pending_2fa(user_id)

            # Log del evento
            await self._log_auth_event(
                user_id=user_id, action="2fa_enable", success=True
            )

            return {
                "success": True,
                "message": "2FA enabled successfully",
                "backup_codes": pending_data["backup_codes"],
            }

        except Exception as e:
            logger.error(f"2FA verification error: {e}")
            raise

    def _verify_totp_code(self, secret: str, code: str) -> bool:
        """Verificar código TOTP"""
        if not secret or not code:
            return False

        try:
            totp = pyotp.TOTP(secret)
            # Verificar código actual y códigos anteriores/siguientes (window=1)
            return totp.verify(code, valid_window=1)
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return False

    async def disable_2fa(
        self,
        user_id: str,
        password: str,
        totp_code: str = None,
        backup_code: str = None,
    ) -> Dict[str, Any]:
        """Deshabilitar 2FA"""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")

            if not self._verify_password(password, user.password_hash):
                raise ValueError("Invalid password")

            if not user.has_2fa:
                raise ValueError("2FA is not enabled")

            # Verificar código 2FA o código de respaldo
            verified = False

            if totp_code:
                verified = self._verify_totp_code(user.totp_secret, totp_code)
            elif backup_code and user.backup_codes:
                verified = any(
                    self._verify_password(backup_code, hashed)
                    for hashed in user.backup_codes
                )

            if not verified:
                raise ValueError("Invalid 2FA or backup code")

            # Deshabilitar 2FA
            update_data = {
                "has_2fa": False,
                "totp_secret": None,
                "backup_codes": None,
                "updated_at": self._get_current_timestamp().isoformat(),
            }

            result = (
                self.client.table("users")
                .update(update_data)
                .eq("id", user_id)
                .execute()
            )

            if not result.data:
                raise Exception("Failed to disable 2FA")

            # Log del evento
            await self._log_auth_event(
                user_id=user_id, action="2fa_disable", success=True
            )

            return {"success": True, "message": "2FA disabled successfully"}

        except Exception as e:
            logger.error(f"Disable 2FA error: {e}")
            raise

    # ===================== GESTIÓN DE USUARIOS =====================

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Obtener usuario por ID"""
        try:
            result = self.client.table("users").select("*").eq("id", user_id).execute()

            if result.data:
                return User(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Get user by ID error: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtener usuario por email"""
        try:
            result = self.client.table("users").select("*").eq("email", email).execute()

            if result.data:
                return User(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Get user by email error: {e}")
            return None

    def _user_to_profile(self, user: User) -> UserProfile:
        """Convertir User a UserProfile"""
        return UserProfile(
            user_id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            company=user.company,
            phone=user.phone,
            role=user.role,
            is_active=user.is_active,
            email_confirmed=user.email_confirmed,
            has_2fa=user.has_2fa,
            created_at=user.created_at,
            last_login=user.last_login,
        )

    # ===================== MÉTODOS AUXILIARES =====================

    async def _create_user_session(
        self,
        user: User,
        remember_me: bool,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Tuple[str, str]:
        """Crear sesión de usuario y tokens"""
        try:
            # Crear tokens
            access_token = self._create_access_token(
                str(user.id), user.email, user.role.value
            )
            refresh_token = self._create_refresh_token(str(user.id))

            # Calcular expiración basada en remember_me
            expires_delta = timedelta(
                days=self.refresh_token_expire_days if remember_me else 1
            )
            expires_at = self._get_current_timestamp() + expires_delta

            # Crear registro de sesión
            session_data = {
                "id": str(uuid4()),
                "user_id": str(user.id),
                "session_token": self._generate_secure_token(),
                "refresh_token": refresh_token,
                "device_info": user_agent,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": self._get_current_timestamp().isoformat(),
                "last_activity": self._get_current_timestamp().isoformat(),
                "expires_at": expires_at.isoformat(),
                "is_active": True,
                "revoked": False,
            }

            result = self.client.table("user_sessions").insert(session_data).execute()

            if not result.data:
                raise Exception("Failed to create session")

            return access_token, refresh_token

        except Exception as e:
            logger.error(f"Create session error: {e}")
            raise

    async def _log_auth_event(
        self,
        user_id: str = None,
        email: str = None,
        action: str = "",
        success: bool = True,
        ip_address: str = None,
        user_agent: str = None,
        error_message: str = None,
        details: Dict[str, Any] = None,
    ):
        """Registrar evento de autenticación"""
        try:
            log_data = {
                "id": str(uuid4()),
                "user_id": user_id,
                "email": email,
                "action": action,
                "success": success,
                "error_message": error_message,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "details": details or {},
                "timestamp": self._get_current_timestamp().isoformat(),
            }

            self.client.table("auth_audit_logs").insert(log_data).execute()

        except Exception as e:
            logger.error(f"Auth logging error: {e}")

    async def _update_last_login(self, user_id: str):
        """Actualizar último login del usuario"""
        try:
            update_data = {
                "last_login": self._get_current_timestamp().isoformat(),
                "last_activity": self._get_current_timestamp().isoformat(),
            }

            self.client.table("users").update(update_data).eq(
                "id", str(user_id)
            ).execute()

        except Exception as e:
            logger.error(f"Update last login error: {e}")

    # ===================== MÉTODOS REDIS INTEGRADOS =====================

    def _get_redis_client(self):
        """Obtener cliente Redis lazy-loading"""
        if not hasattr(self, "_redis_client"):
            try:
                from app.auth.redis_client import redis_auth_client

                self._redis_client = redis_auth_client
            except ImportError:
                logger.warning("Redis client not available, using fallback")
                self._redis_client = None
        return self._redis_client

    async def _store_2fa_temp_session(
        self, user_id: UUID, temp_token: str, ip_address: str, user_agent: str
    ):
        """Almacenar sesión temporal para 2FA"""
        redis_client = self._get_redis_client()
        if redis_client:
            return await redis_client.store_2fa_temp_session(
                str(user_id), temp_token, ip_address, user_agent
            )
        return False

    async def _get_2fa_temp_session(self, temp_token: str) -> Optional[Dict[str, Any]]:
        """Obtener sesión temporal 2FA"""
        redis_client = self._get_redis_client()
        if redis_client:
            return await redis_client.get_2fa_temp_session(temp_token)
        return None

    async def _cleanup_2fa_temp_session(self, temp_token: str):
        """Limpiar sesión temporal 2FA"""
        redis_client = self._get_redis_client()
        if redis_client:
            return await redis_client.cleanup_2fa_temp_session(temp_token)
        return False

    async def _store_pending_2fa(
        self, user_id: str, secret: str, backup_codes: List[str]
    ):
        """Almacenar datos pendientes de 2FA"""
        redis_client = self._get_redis_client()
        if redis_client:
            return await redis_client.store_pending_2fa(user_id, secret, backup_codes)
        return False

    async def _get_pending_2fa(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtener datos pendientes de 2FA"""
        redis_client = self._get_redis_client()
        if redis_client:
            return await redis_client.get_pending_2fa(user_id)
        return None

    async def _cleanup_pending_2fa(self, user_id: str):
        """Limpiar datos pendientes de 2FA"""
        redis_client = self._get_redis_client()
        if redis_client:
            return await redis_client.cleanup_pending_2fa(user_id)
        return False

    async def _get_session_by_refresh_token(
        self, refresh_token: str
    ) -> Optional[UserSession]:
        """Obtener sesión por refresh token"""
        try:
            result = (
                self.client.table("user_sessions")
                .select("*")
                .eq("refresh_token", refresh_token)
                .execute()
            )

            if result.data:
                return UserSession(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Get session error: {e}")
            return None

    async def _update_session_activity(self, session_id: UUID):
        """Actualizar actividad de sesión"""
        try:
            update_data = {"last_activity": self._get_current_timestamp().isoformat()}

            self.client.table("user_sessions").update(update_data).eq(
                "id", str(session_id)
            ).execute()

        except Exception as e:
            logger.error(f"Update session activity error: {e}")
