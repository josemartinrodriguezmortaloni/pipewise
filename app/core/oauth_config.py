"""
OAuth Configuration for PipeWise Integrations

Centralized configuration for OAuth 2.0 flows with external services.
All client credentials are stored as environment variables for security.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import base64
import hashlib
import secrets
import re

logger = logging.getLogger(__name__)


class OAuthConfig(BaseModel):
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    redirect_uri_path: str  # e.g., /api/integrations/google_calendar/oauth/callback
    scope: str
    extra_params: Optional[Dict[str, Any]] = None


# Using Postman's public callback URL for local development.
# IMPORTANT: You must add this exact URL to the "Authorized redirect URIs"
# in your Google Cloud and Twitter Developer App settings.


def get_base_redirect_url() -> str:
    """Gets the base URL for OAuth redirects from environment variables."""
    # Esta URL debe ser pública (usando ngrok o localtunnel) para desarrollo
    base_url = os.getenv("OAUTH_BASE_URL", "http://localhost:8001")
    logger.info(f"🔗 OAuth redirect base URL: {base_url}")
    return base_url


def build_redirect_uri(service: str) -> str:
    """Builds the full, absolute redirect URI for a service."""
    logger.info(f"🔧 Building redirect URI for service: {service}")

    config = OAUTH_CONFIGS.get(service)
    if not config:
        logger.error(f"❌ OAuth configuration not found for service: {service}")
        raise ValueError(f"OAuth configuration not found for service: {service}")

    base_url = get_base_redirect_url().rstrip("/")
    redirect_uri = f"{base_url}{config.redirect_uri_path}"

    logger.info(f"✅ Built redirect URI for {service}: {redirect_uri}")
    return redirect_uri


# Log environment variables for debugging (only log existence, not values)
logger.info("🔧 Checking OAuth environment variables...")
logger.info(f"📋 GOOGLE_CLIENT_ID set: {'GOOGLE_CLIENT_ID' in os.environ}")
logger.info(f"📋 GOOGLE_CLIENT_SECRET set: {'GOOGLE_CLIENT_SECRET' in os.environ}")
logger.info(f"📋 CALENDLY_CLIENT_ID set: {'CALENDLY_CLIENT_ID' in os.environ}")
logger.info(f"📋 CALENDLY_CLIENT_SECRET set: {'CALENDLY_CLIENT_SECRET' in os.environ}")
logger.info(f"📋 TWITTER_CLIENT_ID set: {'TWITTER_CLIENT_ID' in os.environ}")
logger.info(f"📋 TWITTER_CLIENT_SECRET set: {'TWITTER_CLIENT_SECRET' in os.environ}")
logger.info(
    f"📋 OAUTH_REDIRECT_BASE_URL set: {'OAUTH_REDIRECT_BASE_URL' in os.environ}"
)

OAUTH_CONFIGS: Dict[str, OAuthConfig] = {
    "google_calendar": OAuthConfig(
        client_id=os.getenv("GOOGLE_CLIENT_ID", "your-google-client-id"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your-google-client-secret"),
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        redirect_uri_path="/api/integrations/google_calendar/oauth/callback",
        scope="https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/userinfo.email",
        extra_params={"access_type": "offline", "prompt": "consent"},
    ),
    "gmail": OAuthConfig(
        client_id=os.getenv("GOOGLE_CLIENT_ID", "your-google-client-id"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your-google-client-secret"),
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        redirect_uri_path="/api/integrations/gmail/oauth/callback",
        scope="https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/userinfo.email",
        extra_params={"access_type": "offline", "prompt": "consent"},
    ),
    "calendly": OAuthConfig(
        client_id=os.getenv("CALENDLY_CLIENT_ID", "your-calendly-client-id"),
        client_secret=os.getenv(
            "CALENDLY_CLIENT_SECRET", "your-calendly-client-secret"
        ),
        authorize_url="https://auth.calendly.com/oauth/authorize",
        token_url="https://auth.calendly.com/oauth/token",
        redirect_uri_path="/api/integrations/calendly/oauth/callback",
        scope="",
    ),
    "twitter_account": OAuthConfig(
        client_id=os.getenv("TWITTER_CLIENT_ID", "your-twitter-client-id"),
        client_secret=os.getenv("TWITTER_CLIENT_SECRET", "your-twitter-client-secret"),
        authorize_url="https://twitter.com/i/oauth2/authorize",
        token_url="https://api.twitter.com/2/oauth2/token",
        redirect_uri_path="/api/integrations/twitter_account/oauth/callback",
        scope="tweet.read tweet.write users.read offline.access",
    ),
    "pipedrive": OAuthConfig(
        client_id=os.getenv("PIPEDRIVE_CLIENT_ID", ""),
        client_secret=os.getenv(
            "PIPEDRIVE_CLIENT_SECRET", "your-pipedrive-client-secret"
        ),
        authorize_url="https://oauth.pipedrive.com/oauth/authorize",
        token_url="https://oauth.pipedrive.com/oauth/token",
        redirect_uri_path="/api/integrations/pipedrive/oauth/callback",
        scope="activities:full deals:full users:read contacts:full",
        extra_params={"response_type": "code"},
    ),
    "zoho_crm": OAuthConfig(
        client_id=os.getenv("ZOHO_CRM_CLIENT_ID", "your-zoho-crm-client-id"),
        client_secret=os.getenv(
            "ZOHO_CRM_CLIENT_SECRET", "your-zoho-crm-client-secret"
        ),
        authorize_url="https://accounts.zoho.com/oauth/v2/auth",
        token_url="https://accounts.zoho.com/oauth/v2/token",
        redirect_uri_path="/api/integrations/zoho_crm/oauth/callback",
        scope="ZohoCRM.modules.ALL ZohoCRM.settings.ALL",
        extra_params={
            "access_type": "offline",
            "prompt": "consent",
            "response_type": "code",
        },
    ),
    # Add other services here...
}


def get_oauth_config(service: str) -> Optional[OAuthConfig]:
    """Gets the OAuth configuration for a specific service."""
    logger.info(f"🔍 Getting OAuth config for service: {service}")

    config = OAUTH_CONFIGS.get(service)
    if config:
        logger.info(f"✅ OAuth config found for {service}")
        logger.debug(f"📋 Client ID: {config.client_id[:10]}...")
        expected_placeholder = f"your-{service.replace('_', '-')}-client-secret"
        has_real_secret = config.client_secret != expected_placeholder
        logger.debug(f"📋 Has client secret: {has_real_secret}")
        logger.debug(f"📋 Authorize URL: {config.authorize_url}")
        logger.debug(f"📋 Token URL: {config.token_url}")
    else:
        logger.error(f"❌ OAuth config not found for service: {service}")

    return config


def validate_oauth_env_vars():
    """
    Valida que todas las variables de entorno críticas para OAuth estén correctamente configuradas.
    En desarrollo, solo emite warnings en lugar de errores para permitir el funcionamiento del servidor.
    """
    required_vars = [
        ("GOOGLE_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID")),
        ("GOOGLE_CLIENT_SECRET", os.getenv("GOOGLE_CLIENT_SECRET")),
        ("CALENDLY_CLIENT_ID", os.getenv("CALENDLY_CLIENT_ID")),
        ("CALENDLY_CLIENT_SECRET", os.getenv("CALENDLY_CLIENT_SECRET")),
        ("TWITTER_CLIENT_ID", os.getenv("TWITTER_CLIENT_ID")),
        ("TWITTER_CLIENT_SECRET", os.getenv("TWITTER_CLIENT_SECRET")),
        ("PIPEDRIVE_CLIENT_ID", os.getenv("PIPEDRIVE_CLIENT_ID")),
        ("PIPEDRIVE_CLIENT_SECRET", os.getenv("PIPEDRIVE_CLIENT_SECRET")),
        ("ZOHO_CRM_CLIENT_ID", os.getenv("ZOHO_CRM_CLIENT_ID")),
        ("ZOHO_CRM_CLIENT_SECRET", os.getenv("ZOHO_CRM_CLIENT_SECRET")),
    ]

    # En desarrollo, solo emitir warnings para permitir el funcionamiento del servidor
    is_development = os.getenv("ENV", "development") == "development"

    for var, value in required_vars:
        if not value or value.strip() == "" or value.startswith("your-"):
            message = (
                f"❌ Variable de entorno crítica para OAuth no configurada correctamente: {var}. "
                f"Por favor, revisa tu archivo .env y asegúrate de que no tenga valores de ejemplo."
            )
            if is_development:
                logger.warning(message)
            else:
                raise RuntimeError(message)

    logger.info("✅ OAuth environment variables validation completed")


# Ejecutar validación al importar el módulo
# validate_oauth_env_vars()  # Comentado para desarrollo - permitir que el servidor inicie sin todas las variables OAuth


def generate_pkce_pair() -> Dict[str, str]:
    """
    Generate PKCE code_verifier and code_challenge pair for OAuth 2.0.
    Required for Twitter OAuth 2.0.

    Returns:
        Dict containing code_verifier and code_challenge
    """
    # Generate code_verifier (43-128 characters, URL-safe)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8")
    code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)

    # Generate code_challenge (SHA256 hash of code_verifier, base64 encoded)
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
    code_challenge = code_challenge.replace("=", "")

    return {
        "code_verifier": code_verifier,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }


def get_services_requiring_pkce() -> List[str]:
    """
    Return list of services that require PKCE.
    """
    return ["twitter_account", "instagram_account"]
