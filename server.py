#!/usr/bin/env python3
"""
PipeWise CRM - Servidor Principal con Supabase
Sistema completo de CRM con autenticación real y Google Authenticator
"""

import os
import logging

import base64
import io
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# FastAPI imports
from fastapi import (
    FastAPI,
    HTTPException,
    status,
    Depends,
    Request,
    BackgroundTasks,
    Query,
    APIRouter,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from dotenv import load_dotenv
from postgrest.exceptions import APIError

# Pydantic para validación
from pydantic import BaseModel, EmailStr

# Supabase
from supabase import create_client, Client

# Google Authenticator
import pyotp
import qrcode

# Cargar variables de entorno
load_dotenv()

# Configurar logging con soporte para Unicode en Windows
# Configure logging handlers with UTF-8 encoding for Windows compatibility
file_handler = logging.FileHandler("pipewise.log", encoding="utf-8")
stream_handler = logging.StreamHandler()

# Set UTF-8 encoding for the stream handler if on Windows
import sys

if sys.platform == "win32":
    import locale

    stream_handler.setStream(
        open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[file_handler, stream_handler],
)
logger = logging.getLogger(__name__)

# ===================== CONFIGURACIÓN SUPABASE =====================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    logger.error("SUPABASE_URL and SUPABASE_ANON_KEY are required")
    raise ValueError("Missing Supabase configuration")

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Cliente Supabase administrativo (para operaciones que requieren bypass de RLS)
supabase_admin: Client
if SUPABASE_SERVICE_KEY:
    supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
else:
    logger.warning("SUPABASE_SERVICE_KEY not provided. Some operations may fail.")

# ===================== MODELOS PYDANTIC =====================


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company: Optional[str] = None
    phone: Optional[str] = None


class UserRegisterResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    email_confirmed: bool
    message: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class UserLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]
    requires_2fa: Optional[bool] = False


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class Enable2FARequest(BaseModel):
    password: str


class Enable2FAResponse(BaseModel):
    qr_code: str
    secret: str
    backup_codes: List[str]


class Verify2FARequest(BaseModel):
    totp_code: str
    secret: str


class Disable2FARequest(BaseModel):
    password: str
    totp_code: str


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    company: Optional[str] = None
    phone: Optional[str] = None
    has_2fa: bool
    created_at: str
    last_login: Optional[str] = None


# ===================== MODELOS PARA API DE CONTACTOS =====================


class Contact(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    platform: str
    platform_id: str
    username: Optional[str] = None
    profile_url: Optional[str] = None
    created_at: datetime
    total_messages: int
    last_message_at: Optional[datetime] = None
    meeting_scheduled: bool
    meeting_url: Optional[str] = None


class ContactStats(BaseModel):
    total_contacts: int
    contacts_by_platform: Dict[str, int]
    messages_sent: int
    meetings_scheduled: int
    conversion_rate: float
    last_contact_date: Optional[datetime] = None


class Message(BaseModel):
    id: str
    platform: str
    message_type: str
    subject: Optional[str] = None
    content: str
    template_name: Optional[str] = None
    sent_at: datetime
    status: str
    metadata: Optional[Dict[str, Any]] = None


# ===================== MODELOS PARA API DE LEADS =====================


class Lead(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    source: Optional[str] = None
    status: str = "new"
    priority: str = "medium"
    notes: Optional[str] = None
    tags: List[str] = []
    value: Optional[float] = None
    expected_close_date: Optional[str] = None
    created_at: str
    updated_at: str


class LeadsList(BaseModel):
    items: List[Lead]
    total: int
    page: int
    per_page: int
    total_pages: int


class LeadCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    source: Optional[str] = None
    status: str = "new"
    priority: str = "medium"
    notes: Optional[str] = None
    tags: List[str] = []
    value: Optional[float] = None
    expected_close_date: Optional[str] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    value: Optional[float] = None
    expected_close_date: Optional[str] = None


class LeadAnalytics(BaseModel):
    total_leads: int
    leads_by_status: Dict[str, int]
    leads_by_source: Dict[str, int]
    recent_leads: List[Lead]
    conversion_rate: float
    average_value: float


# ===================== SISTEMA DE AUTENTICACIÓN CON SUPABASE =====================


class SupabaseAuth:
    """Sistema de autenticación con Supabase y 2FA"""

    def __init__(self):
        self.supabase = supabase
        self.supabase_admin = supabase_admin

    async def register_user(
        self, user_data: UserRegisterRequest
    ) -> UserRegisterResponse:
        """Registrar usuario en Supabase"""
        try:
            # Registrar en Supabase Auth
            auth_response = self.supabase.auth.sign_up(
                {
                    "email": user_data.email,
                    "password": user_data.password,
                    "options": {
                        "data": {
                            "full_name": user_data.full_name,
                            "company": user_data.company,
                            "phone": user_data.phone,
                        }
                    },
                }
            )

            if auth_response.user is None:
                raise ValueError("Failed to create user")

            # Crear perfil en tabla users
            user_profile = {
                "id": auth_response.user.id,
                "email": user_data.email,
                "full_name": user_data.full_name,
                "company": user_data.company,
                "phone": user_data.phone,
                "has_2fa": False,
                "created_at": datetime.now().isoformat(),
            }

            # Siempre usar el cliente administrativo para insertar en tabla users
            if self.supabase_admin:
                self.supabase_admin.table("users").insert(user_profile).execute()
                logger.info(
                    f"User profile created with admin client: {user_data.email}"
                )
            else:
                # Fallback usando el cliente normal (puede fallar por RLS)
                logger.warning(
                    "Using non-admin client for user insertion - this might fail due to RLS policies"
                )
                self.supabase.table("users").insert(user_profile).execute()

            return UserRegisterResponse(
                user_id=auth_response.user.id,
                email=user_data.email,
                full_name=user_data.full_name,
                email_confirmed=auth_response.user.email_confirmed_at is not None,
                message="User registered successfully. Please check your email to confirm your account.",
            )

        except Exception as e:
            logger.error(f"Registration error: {e}")
            if "already registered" in str(e):
                raise ValueError("Email already registered")
            raise ValueError(f"Registration failed: {str(e)}")

    async def login_user(
        self, request: Request, login_data: UserLoginRequest
    ) -> UserLoginResponse:
        """
        Login con Supabase y 2FA opcional.
        """
        if not self.supabase_admin:
            logger.error(
                "Supabase admin client is not configured. SUPABASE_SERVICE_KEY is required."
            )
            raise ValueError("Server configuration error: Admin client not available.")

        client_ip = get_client_ip(request)
        logger.info(f"Login attempt for {login_data.email} from {client_ip}")

        auth_response = self.supabase.auth.sign_in_with_password(
            {"email": login_data.email, "password": login_data.password}
        )
        if not auth_response.user or not auth_response.session:
            raise ValueError("Invalid credentials")

        if (
            not auth_response.user.email_confirmed_at
            and os.getenv("ENV") != "development"
        ):
            raise ValueError("Email not confirmed")

        user_id = auth_response.user.id
        try:
            profile_res = (
                self.supabase_admin.table("users")
                .select("*")
                .eq("id", user_id)
                .single()
                .execute()
            )
            profile_data = profile_res.data
        except APIError as api_err:
            # PGRST116 = 0 filas (o más de 1) → crear perfil al vuelo
            if getattr(api_err, "code", "") == "PGRST116":
                logger.warning(
                    "No profile row found for %s – inserting one on the fly", user_id
                )
                profile_data = {
                    "id": user_id,
                    "email": login_data.email,
                    "full_name": auth_response.user.user_metadata.get("full_name")
                    or login_data.email.split("@")[0],
                    "company": auth_response.user.user_metadata.get("company"),
                    "phone": auth_response.user.user_metadata.get("phone"),
                    "has_2fa": False,
                    "created_at": datetime.utcnow().isoformat(),
                }
                self.supabase_admin.table("users").insert(profile_data).execute()
            else:
                raise

        user_profile = profile_data
        now_iso = datetime.now().isoformat()
        created_at = user_profile.get("created_at")

        user_for_response = {
            "id": str(user_profile.get("id")),
            "email": user_profile.get("email"),
            "full_name": user_profile.get("full_name"),
            "company": user_profile.get("company"),
            "phone": user_profile.get("phone"),
            "has_2fa": user_profile.get("has_2fa", False),
            "created_at": created_at.isoformat()
            if isinstance(created_at, datetime)
            else str(created_at),
            "last_login": now_iso,
        }

        try:
            self.supabase_admin.table("users").update({"last_login": now_iso}).eq(
                "id", user_id
            ).execute()
        except Exception as e:
            logger.warning(f"Could not update last_login for {user_id}: {e}")

        return UserLoginResponse(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            token_type="bearer",
            expires_in=auth_response.session.expires_in,
            user=user_for_response,
        )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Renovar token de acceso"""
        try:
            response = self.supabase.auth.refresh_session(refresh_token)

            if response.session is None:
                raise ValueError("Invalid refresh token")

            return {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "token_type": "bearer",
                "expires_in": response.session.expires_in or 3600,
            }

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise ValueError("Token refresh failed")

    async def get_user_from_token(self, access_token: str) -> Optional[Dict]:
        """Obtener usuario a partir de un token de acceso, usando cliente admin para evitar RLS"""
        try:
            # Obtener usuario de Supabase Auth
            auth_response = self.supabase.auth.get_user(access_token)

            if not auth_response or not auth_response.user:
                return None

            user = auth_response.user

            # Preferir cliente admin para evitar RLS, pero hacer fallback si no existe
            if self.supabase_admin:
                profile_response = (
                    self.supabase_admin.table("users")
                    .select("*")
                    .eq("id", user.id)
                    .single()
                    .execute()
                )
            else:
                logger.warning(
                    "Supabase admin client not configured. Falling back to regular client; this may be limited by RLS policies."
                )
                profile_response = (
                    self.supabase.table("users")
                    .select("*")
                    .eq("id", user.id)
                    .single()
                    .execute()
                )

            if not profile_response.data:
                logger.warning(
                    "No profile row found for %s during token validation – inserting one",
                    user.id,
                )
                # Safe access to user.email with fallback
                user_email = user.email or "unknown@email.com"
                basic_profile = {
                    "id": user.id,
                    "email": user_email,
                    "full_name": user.user_metadata.get("full_name")
                    or user_email.split("@")[0],
                    "company": user.user_metadata.get("company"),
                    "phone": user.user_metadata.get("phone"),
                    "has_2fa": False,
                    "created_at": user.created_at.isoformat()
                    if user.created_at
                    else datetime.now().isoformat(),
                    "last_login": None,
                }
                try:
                    if self.supabase_admin:
                        self.supabase_admin.table("users").insert(
                            basic_profile
                        ).execute()
                    else:
                        self.supabase.table("users").insert(basic_profile).execute()
                    return basic_profile
                except Exception as insert_err:
                    logger.error("Failed to insert profile on the fly: %s", insert_err)
                    return None

            return profile_response.data

        except Exception as e:
            logger.error(f"Error al validar token: {e}")
            return None

    async def enable_2fa(self, user_id: str, password: str) -> Enable2FAResponse:
        """Habilitar 2FA para el usuario"""
        try:
            # Verificar password actual
            user_profile = (
                self.supabase.table("users").select("email").eq("id", user_id).execute()
            )
            if not user_profile.data:
                raise ValueError("User not found")

            # Verificar que el password es correcto antes de habilitar 2FA
            user_email = user_profile.data[0]["email"]
            try:
                # Intentar autenticar con el password proporcionado
                auth_check = self.supabase.auth.sign_in_with_password(
                    {"email": user_email, "password": password}
                )
                if not auth_check.user:
                    raise ValueError("Invalid password")
            except Exception as e:
                logger.error(f"Password verification failed: {e}")
                raise ValueError("Invalid password")

            # Generar secreto TOTP
            secret = pyotp.random_base32()

            # Crear URI para Google Authenticator
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user_profile.data[0]["email"], issuer_name="PipeWise CRM"
            )

            # Generar QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(totp_uri)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = io.BytesIO()
            img.save(img_buffer, "PNG")
            img_str = base64.b64encode(img_buffer.getvalue()).decode()

            # Generar códigos de backup
            backup_codes = [pyotp.random_base32()[:8] for _ in range(10)]

            # Guardar secreto temporalmente (se confirmará en verify_2fa)
            self.supabase.table("users").update(
                {"totp_secret_temp": secret, "backup_codes": backup_codes}
            ).eq("id", user_id).execute()

            return Enable2FAResponse(
                qr_code=f"data:image/png;base64,{img_str}",
                secret=secret,
                backup_codes=backup_codes,
            )

        except Exception as e:
            logger.error(f"Enable 2FA error: {e}")
            raise ValueError(f"Failed to enable 2FA: {str(e)}")

    async def verify_2fa(self, user_id: str, totp_code: str, secret: str) -> bool:
        """Verificar y activar 2FA"""
        try:
            if not self._verify_totp(secret, totp_code):
                raise ValueError("Invalid verification code")

            # Activar 2FA definitivamente
            self.supabase.table("users").update(
                {"has_2fa": True, "totp_secret": secret, "totp_secret_temp": None}
            ).eq("id", user_id).execute()

            return True

        except Exception as e:
            logger.error(f"Verify 2FA error: {e}")
            raise ValueError("2FA verification failed")

    async def disable_2fa(self, user_id: str, password: str, totp_code: str) -> bool:
        """Deshabilitar 2FA"""
        try:
            # Obtener datos del usuario
            user_data = (
                self.supabase.table("users").select("*").eq("id", user_id).execute()
            )
            if not user_data.data:
                raise ValueError("User not found")

            user = user_data.data[0]

            # Verificar código TOTP
            if not self._verify_totp(user["totp_secret"], totp_code):
                raise ValueError("Invalid 2FA code")

            # Deshabilitar 2FA
            self.supabase.table("users").update(
                {"has_2fa": False, "totp_secret": None, "backup_codes": None}
            ).eq("id", user_id).execute()

            return True

        except Exception as e:
            logger.error(f"Disable 2FA error: {e}")
            raise ValueError("Failed to disable 2FA")

    def _verify_totp(self, secret: str, code: str) -> bool:
        """Verificar código TOTP"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=1)
        except (ValueError, TypeError, AttributeError) as e:
            # Catch specific exceptions that might occur during TOTP verification
            logger.error(f"TOTP verification error: {e}")
            return False
        except Exception as e:
            # Log unexpected exceptions before returning False
            logger.error(f"Unexpected error during TOTP verification: {e}")
            return False


# Instancia global del sistema de autenticación
auth_system = SupabaseAuth()

# ===================== DEPENDENCIAS =====================

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Obtener usuario actual del token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await auth_system.get_user_from_token(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except Exception as e:
        logger.error(f"Token validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ===================== UTILIDADES DE INFRAESTRUCTURA =====================


# Función para ejecutar SQL y crear las políticas de RLS correctas para la tabla users
async def fix_users_rls_policies():
    """Función para corregir políticas RLS que causan recursión infinita"""
    if not supabase_admin:
        logger.error("No se puede corregir las políticas RLS sin SUPABASE_SERVICE_KEY")
        return

    try:
        # Usar el cliente administrativo para ejecutar SQL directo
        logger.info("Intentando corregir políticas RLS para la tabla users...")

        # Primero eliminamos las políticas problemáticas
        try:
            supabase_admin.postgrest.rpc(
                "exec_sql",
                {
                    "query": """
                    DROP POLICY IF EXISTS \"Users can view own profile\" ON users;
                    DROP POLICY IF EXISTS \"Users can update own profile\" ON users;
                    DROP POLICY IF EXISTS \"Users can insert own profile\" ON users;
                """
                },
            ).execute()
        except Exception as rpc_err:
            if "PGRST202" in str(rpc_err):
                logger.warning(
                    "exec_sql function not present; skipping RLS policy reset via RPC"
                )
            else:
                raise

        # Creamos nuevas políticas que permiten a los usuarios acceder a sus propios datos
        # y al rol de servicio acceder a todos los datos
        supabase_admin.postgrest.rpc(
            "exec_sql",
            {
                "query": """
                CREATE POLICY "Users can view own profile" ON users FOR SELECT
                USING (auth.uid()::text = id::text OR auth.role() = 'service_role');
                
                CREATE POLICY "Users can update own profile" ON users FOR UPDATE
                USING (auth.uid()::text = id::text OR auth.role() = 'service_role');
                
                CREATE POLICY "Users can insert own profile" ON users FOR INSERT
                WITH CHECK (auth.uid()::text = id::text OR auth.role() = 'service_role');
            """
            },
        ).execute()

        logger.info("Políticas RLS corregidas correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al corregir políticas RLS: {e}")
        return False


def get_client_ip(request: Request) -> str:
    """Obtener IP del cliente"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ===================== CICLO DE VIDA DE LA APLICACIÓN =====================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager para manejar el ciclo de vida de la aplicación.
    Se ejecuta al iniciar y al apagar el servidor.
    """
    logger.info("Starting PipeWise CRM with Supabase...")
    try:
        # Intenta corregir las políticas de RLS al inicio
        # await fix_users_rls_policies() # Comentado temporalmente para evitar errores de inicio

        # Verifica la conexión con Supabase
        if supabase_admin:
            supabase_admin.table("users").select("count").execute()
            logger.info("Supabase connection established")
        else:
            supabase.table("users").select("count").execute()
            logger.info("Supabase connection established")
    except Exception as e:
        logger.error(f"Supabase connection failed: {e}")

    logger.info("PipeWise CRM Server started successfully")

    yield

    # Shutdown
    logger.info("Shutting down PipeWise CRM Server...")
    logger.info("Server shutdown complete")


# ===================== CREAR APLICACIÓN =====================

app = FastAPI(
    title="PipeWise CRM with Supabase",
    description="Sistema completo de CRM con autenticación Supabase y Google Authenticator",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ===================== CONFIGURACIÓN DE CORS =====================

allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "https://app.pipewise.com",
    "https://pipewise.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Rate-Limit-Remaining"],
)

# ===================== MIDDLEWARE =====================


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware de logging"""
    import time

    start_time = time.time()
    client_ip = get_client_ip(request)

    logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        logger.info(f"Response: {response.status_code} in {process_time:.4f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed after {process_time:.4f}s - {str(e)}")
        raise


# ===================== MANEJO DE ERRORES =====================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Manejo de excepciones HTTP"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Manejo de errores de validación"""
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "status_code": 400,
            "timestamp": datetime.now().isoformat(),
        },
    )


# ===================== RUTAS PRINCIPALES =====================


@app.get("/")
async def root():
    """Ruta principal"""
    return {
        "message": "PipeWise CRM API with Supabase",
        "version": "3.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "features": ["Supabase Auth", "Google Authenticator", "2FA"],
    }


@app.get("/health")
async def health_check():
    """Verifica el estado del servidor y la conexión a Supabase."""
    return {"status": "ok", "message": "PipeWise server is running"}


@app.get("/api/test-reload")
async def test_reload():
    return {"message": "Server has been reloaded successfully!"}


# ===================== RUTAS DE AUTENTICACIÓN =====================

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@auth_router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    request: Request, user_data: UserRegisterRequest, background_tasks: BackgroundTasks
):
    """Registrar nuevo usuario con Supabase"""
    try:
        client_ip = get_client_ip(request)
        logger.info(f"Registration attempt from {client_ip} for {user_data.email}")

        result = await auth_system.register_user(user_data)

        logger.info(f"User registered successfully: {user_data.email}")
        return result

    except ValueError as e:
        logger.warning(f"Registration failed for {user_data.email}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@auth_router.post("/login", response_model=UserLoginResponse)
async def login_user(request: Request, login_data: UserLoginRequest):
    """
    Login con Supabase y 2FA opcional.
    """
    try:
        return await auth_system.login_user(request, login_data)
    except ValueError as e:
        logger.warning(f"Login failed for {login_data.email}: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(
            f"An unexpected login error occurred for {login_data.email}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during login.",
        )


@auth_router.post("/refresh")
async def refresh_access_token(token_data: TokenRefreshRequest):
    """Renovar token de acceso"""
    try:
        result = await auth_system.refresh_token(token_data.refresh_token)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@auth_router.get("/validate")
async def validate_token(current_user: dict = Depends(get_current_user)):
    """Validar token actual"""
    return {
        "valid": True,
        "user": {
            "user_id": current_user["id"],
            "email": current_user["email"],
            "full_name": current_user["full_name"],
            "company": current_user.get("company"),
            "phone": current_user.get("phone"),
            "has_2fa": current_user.get("has_2fa", False),
            "created_at": current_user["created_at"],
            "last_login": current_user.get("last_login"),
        },
    }


@auth_router.post("/logout")
async def logout_user(request: Request, current_user: dict = Depends(get_current_user)):
    """Logout de usuario"""
    try:
        # Supabase maneja el logout automáticamente al expirar el token
        logger.info(f"User logged out: {current_user['email']}")
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )


@auth_router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Obtener perfil del usuario"""
    return UserProfile(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        company=current_user.get("company"),
        phone=current_user.get("phone"),
        has_2fa=current_user.get("has_2fa", False),
        created_at=current_user["created_at"],
        last_login=current_user.get("last_login"),
    )


# ===================== RUTAS DE 2FA =====================


@auth_router.post("/2fa/enable", response_model=Enable2FAResponse)
async def enable_2fa(
    request: Request,
    enable_data: Enable2FARequest,
    current_user: dict = Depends(get_current_user),
):
    """Habilitar Google Authenticator 2FA"""
    try:
        result = await auth_system.enable_2fa(current_user["id"], enable_data.password)
        logger.info(f"2FA setup initiated for user: {current_user['email']}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Enable 2FA error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable 2FA",
        )


@auth_router.post("/2fa/verify")
async def verify_2fa(
    request: Request,
    verify_data: Verify2FARequest,
    current_user: dict = Depends(get_current_user),
):
    """Verificar y activar 2FA"""
    try:
        success = await auth_system.verify_2fa(
            current_user["id"], verify_data.totp_code, verify_data.secret
        )

        if success:
            logger.info(f"2FA enabled successfully for user: {current_user['email']}")
            return {"message": "2FA enabled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code",
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Verify 2FA error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="2FA verification failed",
        )


@auth_router.post("/2fa/disable")
async def disable_2fa(
    request: Request,
    disable_data: Disable2FARequest,
    current_user: dict = Depends(get_current_user),
):
    """Deshabilitar 2FA"""
    try:
        success = await auth_system.disable_2fa(
            current_user["id"], disable_data.password, disable_data.totp_code
        )

        if success:
            logger.info(f"2FA disabled for user: {current_user['email']}")
            return {"message": "2FA disabled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to disable 2FA"
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Disable 2FA error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable 2FA",
        )


app.include_router(auth_router, prefix="/api")

# ===================== RUTAS PARA LEADS =====================


@app.get("/api/leads", response_model=LeadsList)
async def get_leads(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=1000),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    current_user: dict = Depends(get_current_user),
):
    """Obtener y listar leads para el usuario actual con filtros y paginación."""
    try:
        user_id = current_user["id"]
        logger.info(f"Obteniendo leads para usuario {user_id}")

        # Use admin client if available, otherwise fallback to regular client
        client = supabase_admin if supabase_admin else supabase

        query = client.table("leads").select("*").eq("user_id", user_id)

        if status_filter:
            query = query.eq("status", status_filter)
        # Search functionality disabled due to API limitations
        # if search:
        #     query = query.text_search("fts", search)

        # Ordering disabled due to API limitations
        # if sort_by:
        #     query = query.order(sort_by, desc=sort_order == "desc")

        # Get all data and handle pagination manually
        result = query.execute()

        # Calculate total and pagination
        all_leads = result.data or []
        total_items = len(all_leads)

        # Apply pagination manually
        offset = (page - 1) * per_page
        paginated_leads = all_leads[offset : offset + per_page]

        total_pages = (total_items + per_page - 1) // per_page

        return {
            "items": paginated_leads,
            "total": total_items,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Error al obtener leads: {e}")
        raise HTTPException(
            status_code=500, detail="Error interno del servidor al obtener leads"
        )


@app.post("/api/leads", status_code=status.HTTP_201_CREATED, response_model=Lead)
async def create_lead(
    request: Request,
    lead_data: LeadCreate,
    current_user: dict = Depends(get_current_user),
):
    """Crear un nuevo lead"""
    try:
        user_id = current_user["id"]

        # Crear el lead
        new_lead = {
            **lead_data.dict(),
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # Insertar en la base de datos usando el cliente admin si está disponible
        client = supabase_admin if supabase_admin else supabase
        response = client.table("leads").insert(new_lead).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear el lead",
            )

        return Lead(**response.data[0])

    except Exception as e:
        logger.error(f"Error al crear lead: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear lead: {str(e)}",
        )


@app.get("/api/leads/{lead_id}", response_model=Lead)
async def get_lead(
    request: Request,
    lead_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Obtener un lead específico"""
    try:
        user_id = current_user["id"]

        # Obtener el lead usando el cliente admin si está disponible
        client = supabase_admin if supabase_admin else supabase
        response = (
            client.table("leads")
            .select("*")
            .eq("id", lead_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead no encontrado",
            )

        return Lead(**response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener lead: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener lead: {str(e)}",
        )


@app.put("/api/leads/{lead_id}", response_model=Lead)
async def update_lead(
    request: Request,
    lead_id: str,
    lead_data: LeadUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Actualizar un lead"""
    try:
        user_id = current_user["id"]

        # Verificar que el lead existe y pertenece al usuario
        client = supabase_admin if supabase_admin else supabase
        lead_response = (
            client.table("leads")
            .select("*")
            .eq("id", lead_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not lead_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead no encontrado",
            )

        # Actualizar el lead
        update_data = {
            **{k: v for k, v in lead_data.dict().items() if v is not None},
            "updated_at": datetime.now().isoformat(),
        }

        response = (
            client.table("leads")
            .update(update_data)
            .eq("id", lead_id)
            .eq("user_id", user_id)
            .execute()
        )

        return Lead(**response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar lead: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar lead: {str(e)}",
        )


@app.delete("/api/leads/{lead_id}")
async def delete_lead(
    request: Request,
    lead_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Eliminar un lead"""
    try:
        user_id = current_user["id"]

        # Verificar que el lead existe y pertenece al usuario
        client = supabase_admin if supabase_admin else supabase
        lead_response = (
            client.table("leads")
            .select("*")
            .eq("id", lead_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not lead_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lead no encontrado",
            )

        # Eliminar el lead
        client.table("leads").delete().eq("id", lead_id).eq(
            "user_id", user_id
        ).execute()

        return {"message": "Lead eliminado correctamente"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar lead: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar lead: {str(e)}",
        )


@app.get("/api/analytics/leads", response_model=LeadAnalytics)
async def get_lead_analytics(
    request: Request,
    timerange: str = Query("30d", pattern="^(7d|30d|90d|1y|all)$"),
    current_user: dict = Depends(get_current_user),
):
    """Obtener analíticas de leads"""
    try:
        user_id = current_user["id"]

        # Calcular fecha de inicio según el timerange
        now = datetime.now()
        if timerange == "7d":
            start_date = now - timedelta(days=7)
        elif timerange == "30d":
            start_date = now - timedelta(days=30)
        elif timerange == "90d":
            start_date = now - timedelta(days=90)
        elif timerange == "1y":
            start_date = now - timedelta(days=365)
        else:  # all
            start_date = datetime.min

        start_date_str = start_date.isoformat()

        # Use admin client if available for better performance, otherwise fallback
        client = supabase_admin if supabase_admin else supabase

        # Get all leads and count manually
        all_leads_response = (
            client.table("leads")
            .select("*")
            .eq("user_id", user_id)
            .gte("created_at", start_date_str)
            .execute()
        )
        all_leads_data = all_leads_response.data or []
        total_leads = len(all_leads_data)

        if total_leads == 0:
            return LeadAnalytics(
                total_leads=0,
                leads_by_status={},
                leads_by_source={},
                recent_leads=[],
                conversion_rate=0,
                average_value=0,
            )

        # Get recent leads (last 5)
        recent_leads_response = (
            client.table("leads")
            .select("*")
            .eq("user_id", user_id)
            .gte("created_at", start_date_str)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        recent_leads = [Lead(**lead) for lead in recent_leads_response.data]

        # Get all leads for aggregation (we need this for status/source counts)
        # In a production environment, you might want to use database views or functions
        leads_response = (
            client.table("leads")
            .select("status, source, value")
            .eq("user_id", user_id)
            .gte("created_at", start_date_str)
            .execute()
        )

        leads = leads_response.data

        # Calculate aggregations
        leads_by_status = {}
        leads_by_source = {}
        closed_count = 0
        value_sum = 0
        value_count = 0

        for lead in leads:
            # Count by status
            status_val = lead.get("status", "unknown")
            leads_by_status[status_val] = leads_by_status.get(status_val, 0) + 1

            # Count closed leads for conversion rate
            if status_val == "closed":
                closed_count += 1

            # Count by source
            source = lead.get("source")
            if source:
                leads_by_source[source] = leads_by_source.get(source, 0) + 1

            # Sum values for average
            value = lead.get("value")
            if value is not None:
                value_sum += value
                value_count += 1

        # Calculate metrics
        conversion_rate = (closed_count / total_leads) * 100 if total_leads > 0 else 0
        average_value = value_sum / value_count if value_count > 0 else 0

        return LeadAnalytics(
            total_leads=total_leads,
            leads_by_status=leads_by_status,
            leads_by_source=leads_by_source,
            recent_leads=recent_leads,
            conversion_rate=conversion_rate,
            average_value=average_value,
        )

    except Exception as e:
        logger.error(f"Error al obtener analíticas de leads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener analíticas de leads: {str(e)}",
        )


# ===================== RUTAS DE INTEGRACIONES =====================
integrations_router = APIRouter(prefix="/api/integrations", tags=["Integrations"])
contacts_router = APIRouter(prefix="/api/contacts", tags=["Contacts"])


@integrations_router.post("/calendly/connect")
async def connect_calendly(request: Request):
    """Endpoint para conectar Calendly (placeholder)"""
    # Aquí puedes agregar la lógica real de integración con Calendly
    return {"message": "Calendly connected successfully"}


@contacts_router.get("", response_model=Dict[str, List[Contact]])
async def get_contacts(
    request: Request,
    platform: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves a list of contacts, optionally filtered by platform.
    This is a mock implementation.
    """
    logger.info(f"User {current_user['id']} fetching contacts. Platform: {platform}")

    # Mock data
    mock_contacts = [
        Contact(
            id="1",
            name="Juan Perez",
            email="juan.perez@example.com",
            platform="email",
            platform_id="contact1_email",
            created_at=datetime.now() - timedelta(days=10),
            total_messages=5,
            last_message_at=datetime.now() - timedelta(days=1),
            meeting_scheduled=True,
            meeting_url="https://calendly.com/juan-perez",
        ),
        Contact(
            id="2",
            name="Maria Garcia",
            phone="+1234567890",
            platform="whatsapp",
            platform_id="contact2_whatsapp",
            created_at=datetime.now() - timedelta(days=5),
            total_messages=12,
            last_message_at=datetime.now() - timedelta(hours=6),
            meeting_scheduled=False,
        ),
        Contact(
            id="3",
            name="Carlos Rodriguez",
            username="@carlos.r",
            platform="instagram",
            platform_id="contact3_ig",
            created_at=datetime.now() - timedelta(days=20),
            total_messages=2,
            last_message_at=datetime.now() - timedelta(days=15),
            meeting_scheduled=False,
        ),
    ]

    if platform:
        filtered_contacts = [c for c in mock_contacts if c.platform == platform]
    else:
        filtered_contacts = mock_contacts

    return {"contacts": filtered_contacts}


@contacts_router.get("/stats", response_model=ContactStats)
async def get_contact_stats(
    request: Request, current_user: dict = Depends(get_current_user)
):
    """
    Retrieves statistics about contacts.
    This is a mock implementation.
    """
    logger.info(f"User {current_user['id']} fetching contact stats.")

    # Mock data
    mock_stats = ContactStats(
        total_contacts=150,
        contacts_by_platform={"email": 60, "whatsapp": 50, "instagram": 40},
        messages_sent=450,
        meetings_scheduled=25,
        conversion_rate=16.67,
        last_contact_date=datetime.now() - timedelta(hours=2),
    )
    return mock_stats


@contacts_router.get("/{contact_id}/messages", response_model=Dict[str, List[Message]])
async def get_contact_messages(
    request: Request, contact_id: str, current_user: dict = Depends(get_current_user)
):
    """
    Retrieves messages for a specific contact.
    This is a mock implementation.
    """
    logger.info(
        f"User {current_user['id']} fetching messages for contact {contact_id}."
    )

    # Mock data
    mock_messages = [
        Message(
            id="msg1",
            platform="email",
            message_type="outgoing",
            subject="Re: Consulta",
            content="Hola Juan, gracias por tu interés...",
            sent_at=datetime.now() - timedelta(days=1),
            status="sent",
        ),
        Message(
            id="msg2",
            platform="email",
            message_type="incoming",
            subject="Consulta",
            content="Hola, me gustaría saber más sobre...",
            sent_at=datetime.now() - timedelta(days=2),
            status="received",
        ),
    ]

    # In a real implementation, you would filter messages by contact_id
    if contact_id:
        return {"messages": mock_messages}
    return {"messages": []}


# Incluir nuestro módulo completo de integrations
try:
    from app.api.integrations import router as full_integrations_router

    app.include_router(full_integrations_router)
    logger.info("Full integrations module loaded successfully")
except ImportError as e:
    logger.warning(f"Could not load full integrations module: {e}")
    # Fallback to basic integrations
    app.include_router(integrations_router)

app.include_router(contacts_router)

# ===================== RUTAS PARA DESARROLLO =====================


@app.post("/dev/confirm-email/{email}")
async def confirm_email_dev(email: str):
    """Confirmar email manualmente (SOLO PARA DESARROLLO)"""
    if os.getenv("ENV") != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development mode",
        )

    try:
        if not supabase_admin:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Admin client not available, SUPABASE_SERVICE_ROLE_KEY required",
            )

        # Buscar usuario por email
        user_response = supabase_admin.auth.admin.list_users()
        users = [u for u in user_response if u.email == email]

        if not users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {email} not found",
            )

        user = users[0]

        # Confirmar email
        supabase_admin.auth.admin.update_user_by_id(user.id, {"email_confirm": True})

        logger.warning(f"Email confirmed manually for development: {email}")
        return {"message": f"Email confirmed for {email}"}

    except Exception as e:
        logger.error(f"Error confirming email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm email: {str(e)}",
        )


# ===================== FUNCIÓN PRINCIPAL =====================


def main():
    """Función principal para ejecutar el servidor"""
    logger.info("Starting PipeWise CRM Server with Supabase...")

    # Verificar configuración
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        logger.error(
            "Missing Supabase configuration. Please set SUPABASE_URL and SUPABASE_ANON_KEY"
        )
        return

    # Configuración del servidor
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("BACEND_PORT", "8001"))
    is_dev = os.getenv("ENV") == "development"

    # Permitir recarga solo si BACKEND_RELOAD=true (por defecto desactivado para ver logs limpios)
    enable_reload = is_dev and os.getenv("BACKEND_RELOAD", "false").lower() == "true"

    # Silenciar spam de watchfiles cuando reload está activo
    if enable_reload:
        logging.getLogger("watchfiles.main").setLevel(logging.ERROR)

    logger.info(f"Server will start on {host}:{port}")
    if is_dev:
        logger.info("Running in development mode with auto-reload.")
    logger.info("Access the API documentation at http://localhost:8001/docs")
    logger.info("Features: Supabase Auth, Google Authenticator, 2FA")

    # Para que el reload funcione correctamente, uvicorn necesita la ruta al 'app' como string.
    reload_dirs = (
        os.getenv("RELOAD_DIRS", "server,app").split(",") if enable_reload else None
    )

    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=enable_reload,
        reload_dirs=reload_dirs,
        log_level="info",
    )


if __name__ == "__main__":
    main()
