"""Utilidades de autenticación"""

import os
import secrets
import hashlib
from typing import Optional
from fastapi import Request
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Obtener IP del cliente considerando proxies"""
    # Verificar headers de proxy
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Tomar la primera IP (cliente original)
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fallback a IP directa
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Obtener User-Agent del request"""
    return request.headers.get("user-agent", "unknown")


def generate_secure_token(length: int = 32) -> str:
    """Generar token seguro"""
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    """Hash de token para almacenamiento seguro"""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    """Verificar hash de token"""
    return hash_token(token) == token_hash


def is_development() -> bool:
    """Verificar si estamos en modo desarrollo"""
    return os.getenv("ENVIRONMENT", "development").lower() == "development"


def get_frontend_url() -> str:
    """Obtener URL del frontend"""
    return os.getenv("FRONTEND_URL", "http://localhost:3000")


def get_api_url() -> str:
    """Obtener URL de la API"""
    return os.getenv("API_URL", "http://localhost:8000")


def sanitize_email(email: str) -> str:
    """Sanitizar email"""
    return email.lower().strip()


def is_valid_email_domain(email: str, allowed_domains: Optional[list] = None) -> bool:
    """Verificar si el dominio del email está permitido"""
    if not allowed_domains:
        return True

    domain = email.split("@")[-1].lower()
    return domain in [d.lower() for d in allowed_domains]


def get_rate_limit_key(request: Request, identifier: str) -> str:
    """Generar clave para rate limiting"""
    if identifier:
        return f"rate_limit:{identifier}"

    client_ip = get_client_ip(request)
    return f"rate_limit:ip:{client_ip}"


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Enmascarar datos sensibles"""
    if len(data) <= visible_chars:
        return "*" * len(data)

    return data[:visible_chars] + "*" * (len(data) - visible_chars)


def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
):
    """Log de eventos de seguridad"""
    log_data = {
        "event_type": event_type,
        "user_id": user_id,
        "ip_address": ip_address,
        "details": details or {},
    }

    logger.warning(f"Security Event: {log_data}")


# Constantes de configuración
DEFAULT_TOKEN_EXPIRY_MINUTES = 30
DEFAULT_REFRESH_TOKEN_EXPIRY_DAYS = 7
DEFAULT_2FA_CODE_EXPIRY_MINUTES = 5
DEFAULT_PASSWORD_RESET_EXPIRY_HOURS = 1
DEFAULT_EMAIL_CONFIRMATION_EXPIRY_HOURS = 24

# Rate limiting defaults
DEFAULT_RATE_LIMIT_REQUESTS = 100
DEFAULT_RATE_LIMIT_WINDOW_MINUTES = 15
DEFAULT_LOGIN_RATE_LIMIT_REQUESTS = 5
DEFAULT_LOGIN_RATE_LIMIT_WINDOW_MINUTES = 15
