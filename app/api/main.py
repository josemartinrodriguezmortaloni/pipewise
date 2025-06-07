## main.py - Configuración principal de FastAPI con autenticación
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

# Importaciones del sistema de autenticación
from app.api.auth import router as auth_router
from app.auth.redis_client import redis_auth_client, cleanup_redis_keys
from app.auth.utils import get_client_ip, get_user_agent
from app.services.email_service import email_service

# Importaciones existentes del CRM
# from app.api.api import app as crm_app  # Comentado para tests
from app.agents.agent import Agent

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    # Startup
    logger.info("🚀 Starting PipeWise CRM with Authentication...")

    # Verificar servicios críticos
    await startup_checks()

    # Inicializar tareas de limpieza
    await schedule_cleanup_tasks()

    logger.info("✅ Application started successfully")

    yield

    # Shutdown
    logger.info("🛑 Shutting down application...")
    await cleanup_resources()
    logger.info("✅ Application shutdown complete")


async def startup_checks():
    """Verificaciones de inicio"""
    try:
        # Verificar Redis
        redis_health = await redis_auth_client.health_check()
        logger.info(f"Redis Status: {redis_health['status']}")

        # Verificar Email Service
        email_health = await email_service.health_check()
        logger.info(f"Email Service Status: {email_health['status']}")

        # Verificar CRM Agents
        try:
            agent = Agent()
            logger.info("✅ CRM Agents initialized")
        except Exception as e:
            logger.warning(f"⚠️ CRM Agents initialization warning: {e}")

    except Exception as e:
        logger.error(f"❌ Startup check failed: {e}")


async def schedule_cleanup_tasks():
    """Programar tareas de limpieza"""
    try:
        # Limpiar claves expiradas de Redis
        cleaned = await cleanup_redis_keys()
        logger.info(f"Cleaned {cleaned} expired Redis keys")
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")


async def cleanup_resources():
    """Limpiar recursos al cerrar"""
    try:
        await redis_auth_client.close()
    except Exception as e:
        logger.error(f"Error closing resources: {e}")


# Crear aplicación FastAPI
app = FastAPI(
    title="PipeWise CRM with Authentication",
    description="Complete CRM system with advanced authentication and 2FA",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ===================== CONFIGURACIÓN DE CORS =====================

# Configurar CORS
allowed_origins = [
    "http://localhost:3000",  # React development
    "http://localhost:3001",  # Alternative React port
    "http://127.0.0.1:3000",
    "https://app.pipewise.com",  # Production frontend
    "https://pipewise.vercel.app",  # Vercel deployment
]

# Agregar origins adicionales desde variables de entorno
additional_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
allowed_origins.extend(
    [origin.strip() for origin in additional_origins if origin.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Rate-Limit-Remaining", "X-Rate-Limit-Reset"],
)

# ===================== MIDDLEWARE DE SEGURIDAD =====================

# Hosts confiables
trusted_hosts = ["localhost", "127.0.0.1", "*.pipewise.com"]
additional_hosts = os.getenv("TRUSTED_HOSTS", "").split(",")
trusted_hosts.extend([host.strip() for host in additional_hosts if host.strip()])

app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)


# ===================== MIDDLEWARE PERSONALIZADO =====================


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Agregar headers de seguridad"""
    response = await call_next(request)

    # Headers de seguridad
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # CSP básico
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self'"
    )

    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware de logging para requests"""
    import time

    start_time = time.time()
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Log del request
    logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")

    try:
        response = await call_next(request)

        # Calcular tiempo de procesamiento
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # Log de la respuesta
        logger.info(
            f"Response: {response.status_code} for {request.method} {request.url.path} in {process_time:.4f}s"
        )

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} after {process_time:.4f}s - {str(e)}"
        )
        raise


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """Middleware básico de rate limiting"""
    try:
        # Aplicar rate limiting solo a ciertas rutas
        sensitive_paths = ["/auth/login", "/auth/register", "/auth/forgot-password"]

        if any(request.url.path.startswith(path) for path in sensitive_paths):
            client_ip = get_client_ip(request)

            # Verificar rate limit
            rate_check = await redis_auth_client.check_rate_limit(
                identifier=f"ip:{client_ip}",
                limit=10,  # 10 requests por hora
                window=3600,
            )

            if not rate_check["allowed"]:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Too many requests",
                        "detail": "Rate limit exceeded. Please try again later.",
                        "retry_after": rate_check.get("reset_time", 3600),
                    },
                    headers={
                        "X-Rate-Limit-Limit": str(rate_check["limit"]),
                        "X-Rate-Limit-Remaining": str(
                            max(0, rate_check["limit"] - rate_check["count"])
                        ),
                        "X-Rate-Limit-Reset": str(rate_check.get("reset_time", 0)),
                        "Retry-After": str(3600),
                    },
                )

        return await call_next(request)

    except Exception as e:
        logger.error(f"Rate limiting middleware error: {e}")
        return await call_next(request)


# ===================== MANEJADORES DE ERRORES =====================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Manejador personalizado de excepciones HTTP"""
    client_ip = get_client_ip(request)
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail} for {request.method} {request.url.path} from {client_ip}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Manejador de errores de validación"""
    from datetime import datetime

    logger.error(f"ValueError: {str(exc)} for {request.method} {request.url.path}")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation error",
            "detail": str(exc),
            "status_code": 400,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Manejador general de excepciones"""
    from datetime import datetime

    client_ip = get_client_ip(request)
    logger.error(
        f"Unhandled exception: {str(exc)} for {request.method} {request.url.path} from {client_ip}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ===================== RUTAS PRINCIPALES =====================

# Incluir router de autenticación
app.include_router(auth_router)

# Incluir router de CRM
from app.api.api import router as crm_router

app.include_router(crm_router)

# Incluir router de webhooks y notificaciones
from app.api.webhooks import router as webhooks_router

app.include_router(webhooks_router)

# Incluir router de búsqueda y exportación
from app.api.search import router as search_router

app.include_router(search_router)

# Incluir router de configuración
from app.api.config import router as config_router

app.include_router(config_router)


# ===================== RUTAS DE SALUD Y ESTADO =====================


@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "PipeWise CRM API with Authentication",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "Advanced Authentication",
            "Two-Factor Authentication",
            "CRM Lead Management",
            "AI Agents Integration",
            "Rate Limiting",
            "Email Notifications",
        ],
    }


@app.get("/health")
async def health_check():
    """Health check completo del sistema"""
    from datetime import datetime

    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {},
        }

        # Verificar Redis
        try:
            redis_health = await redis_auth_client.health_check()
            health_status["services"]["redis"] = redis_health
        except Exception as e:
            health_status["services"]["redis"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # Verificar Email Service
        try:
            email_health = await email_service.health_check()
            health_status["services"]["email"] = email_health
        except Exception as e:
            health_status["services"]["email"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # Verificar CRM Database (usando el cliente existente)
        try:
            from app.supabase.supabase_client import SupabaseCRMClient

            db_client = SupabaseCRMClient()
            db_health = db_client.health_check()
            health_status["services"]["database"] = db_health
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        # Determinar estado general
        all_healthy = all(
            service.get("status") in ["healthy", "disabled", "fallback"]
            for service in health_status["services"].values()
        )

        if not all_healthy:
            health_status["status"] = "degraded"

        return health_status

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@app.get("/metrics")
async def get_metrics():
    """Obtener métricas del sistema"""
    from datetime import datetime

    try:
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "auth": {},
            "redis": {},
            "database": {},
        }

        # Métricas de autenticación de Redis
        try:
            auth_stats = await redis_auth_client.get_auth_stats()
            metrics["auth"] = auth_stats
        except Exception as e:
            metrics["auth"] = {"error": str(e)}

        # Métricas de base de datos
        try:
            from app.supabase.supabase_client import SupabaseCRMClient

            db_client = SupabaseCRMClient()
            db_stats = db_client.get_stats()
            metrics["database"] = db_stats
        except Exception as e:
            metrics["database"] = {"error": str(e)}

        return metrics

    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics",
        )


# ===================== CONFIGURACIÓN DE DESARROLLO =====================

if __name__ == "__main__":
    import time
    from datetime import datetime

    # Configuración para desarrollo
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() == "true"

    logger.info(f"Starting server on {host}:{port} (debug={debug})")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        access_log=True,
        log_level="info" if not debug else "debug",
    )


# ===================== CONFIGURACIÓN DE PRODUCCIÓN =====================

# Para producción, usar:
# gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# O con uvicorn:
# uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4


# ===================== TAREAS PROGRAMADAS (OPCIONAL) =====================


# Para usar con APScheduler o similar
async def scheduled_cleanup():
    """Tarea programada de limpieza"""
    try:
        # Limpiar Redis
        cleaned_redis = await cleanup_redis_keys()
        logger.info(f"Scheduled cleanup: {cleaned_redis} Redis keys cleaned")

        # Limpiar base de datos (tokens expirados)
        # Implementar según necesidades

    except Exception as e:
        logger.error(f"Scheduled cleanup error: {e}")


# Configuración de tareas programadas (comentado por defecto)
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import atexit

scheduler = AsyncIOScheduler()
scheduler.add_job(
    func=scheduled_cleanup,
    trigger="interval",
    minutes=30,  # Cada 30 minutos
    id='cleanup_job'
)

# Iniciar scheduler
scheduler.start()

# Asegurar que se cierre al terminar la aplicación
atexit.register(lambda: scheduler.shutdown())
"""
