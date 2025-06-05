from __future__ import annotations

"""Cliente específico para autenticación con Supabase."""

import logging
from typing import Optional, Dict, Any
from supabase import create_client, Client
from gotrue.errors import AuthError

from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseAuthClient:
    """Cliente para operaciones de autenticación con Supabase."""

    def __init__(self) -> None:
        self.client: Client = create_client(settings.supabase_url, settings.supabase_anon_key)

    # ------------------------------------------------------------------
    # Email / password flows
    # ------------------------------------------------------------------
    async def sign_up_with_email(
        self,
        email: str,
        password: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Registrar un usuario en Supabase con email y contraseña."""
        try:
            resp = self.client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": metadata or {}},
                }
            )
            return self._session_to_dict(resp)
        except AuthError as e:
            logger.error(f"Error en sign_up: {e}")
            return None
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error inesperado en sign_up: {e}")
            return None

    async def sign_in_with_email(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Login usuario con email y contraseña."""
        try:
            resp = self.client.auth.sign_in_with_password({"email": email, "password": password})
            return self._session_to_dict(resp)
        except AuthError as e:
            logger.error(f"Error en sign_in: {e}")
            return None
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error inesperado en sign_in: {e}")
            return None

    # ------------------------------------------------------------------
    # OAuth token flow (Google, etc.)
    # ------------------------------------------------------------------
    async def sign_in_with_oauth_token(
        self, *, provider: str, access_token: str, refresh_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.auth.sign_in_with_oauth(
                {
                    "provider": provider,
                    "options": {"access_token": access_token, "refresh_token": refresh_token},
                }
            )
            return self._session_to_dict(response)
        except AuthError as e:
            logger.error(f"Error en autenticación OAuth: {e}")
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def get_user_by_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        try:
            self.client.auth.set_session(access_token, "")
            resp = self.client.auth.get_user(access_token)
            return resp.user.dict() if resp and resp.user else None
        except AuthError as e:
            logger.error(f"Error obteniendo usuario: {e}")
            return None

    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        try:
            resp = self.client.auth.refresh_session(refresh_token)
            if resp and resp.session:
                return {
                    "access_token": resp.session.access_token,
                    "refresh_token": resp.session.refresh_token,
                    "expires_in": resp.session.expires_in,
                }
            return None
        except AuthError as e:
            logger.error(f"Error refrescando token: {e}")
            return None

    async def sign_out(self, access_token: str) -> bool:
        try:
            self.client.auth.set_session(access_token, "")
            self.client.auth.sign_out()
            return True
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error cerrando sesión: {e}")
            return False

    # ------------------------------------------------------------------
    def _session_to_dict(self, response) -> Dict[str, Any]:  # type: ignore[no-any-unbound]
        """Convert Supabase SDK response to a flat dict."""
        return {
            "user": response.user.dict() if response.user else None,
            "access_token": response.session.access_token if response.session else None,
            "refresh_token": response.session.refresh_token if response.session else None,
            "expires_in": response.session.expires_in if response.session else None,
        }