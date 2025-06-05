from __future__ import annotations

"""
Servicio de autenticación con Supabase (email/password y Google OAuth).
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from urllib.parse import urlencode
import httpx

from app.core.config import settings
from app.supabase.auth_client import SupabaseAuthClient
from app.models.user import User
from app.schemas.auth import GoogleAuthInit, UserAuth, Token
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)


class AuthService:
    """Servicio para manejar autenticación (Google OAuth + email/password)."""

    def __init__(self) -> None:
        self.auth_client = SupabaseAuthClient()
        self.google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.google_token_url = "https://oauth2.googleapis.com/token"

    # ---------------------------------------------------------------------
    # Google OAuth flows
    # ---------------------------------------------------------------------
    def get_google_auth_url(self, state: str) -> str:
        """Generar URL de autenticación de Google."""
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.google_auth_url}?{urlencode(params)}"

    async def handle_google_callback(self, code: str, state: str) -> Optional[UserAuth]:
        """Procesar callback de Google OAuth."""
        try:
            # Intercambiar código por tokens de Google
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.google_token_url,
                    data={
                        "code": code,
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "redirect_uri": settings.google_redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                response.raise_for_status()
                tokens = response.json()
        except httpx.HTTPError as err:
            logger.error(f"Error obteniendo tokens de Google: {err}")
            return None

        # Autenticar contra Supabase con los tokens de Google
        auth_response = await self.auth_client.sign_in_with_oauth_token(
            provider="google",
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
        )
        if not auth_response:
            return None

        # Crear/actualizar usuario local (solo mantenemos en memoria)
        user = await self._create_or_update_user(auth_response["user"])

        return UserAuth(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            provider=user.provider,
            access_token=auth_response["access_token"],
            refresh_token=auth_response.get("refresh_token"),
        )

    # ---------------------------------------------------------------------
    # Email / Password flows
    # ---------------------------------------------------------------------
    async def sign_up_email(self, email: str, password: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Token]:
        """Registrar usuario con email/password en Supabase y devolver tokens."""
        resp = await self.auth_client.sign_up_with_email(email, password, metadata)
        if not resp:
            return None
        return Token(
            access_token=resp.get("access_token"),
            refresh_token=resp.get("refresh_token"),
            expires_in=resp.get("expires_in"),
        )

    async def login_email(self, email: str, password: str) -> Optional[Token]:
        """Iniciar sesión con email/password."""
        resp = await self.auth_client.sign_in_with_email(email, password)
        if not resp:
            return None
        return Token(
            access_token=resp.get("access_token"),
            refresh_token=resp.get("refresh_token"),
            expires_in=resp.get("expires_in"),
        )

    # ---------------------------------------------------------------------
    # Misc helpers
    # ---------------------------------------------------------------------
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        return await self.auth_client.refresh_access_token(refresh_token)

    async def sign_out(self, access_token: str) -> bool:
        return await self.auth_client.sign_out(access_token)

    async def _create_or_update_user(self, supabase_user: Dict[str, Any]) -> User:
        """Crear o actualizar modelo User local desde datos de Supabase."""
        user_metadata = supabase_user.get("user_metadata", {})
        return User(
            id=UUID(supabase_user["id"]),
            email=supabase_user["email"],
            full_name=user_metadata.get("full_name") or user_metadata.get("name"),
            avatar_url=user_metadata.get("avatar_url") or user_metadata.get("picture"),
            provider="google",  # Para email/password podría ser "email"
            created_at=supabase_user["created_at"],
            updated_at=supabase_user.get("updated_at"),
            last_sign_in_at=supabase_user.get("last_sign_in_at"),
            raw_user_meta_data=user_metadata,
        )