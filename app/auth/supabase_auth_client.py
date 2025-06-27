"""
Supabase-based authentication client
Replaces Redis functionality with Supabase database tables
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.supabase.supabase_client import SupabaseCRMClient

logger = logging.getLogger(__name__)


class SupabaseAuthClient:
    """Cliente Supabase para manejo de sesiones temporales y cache de autenticación"""

    def __init__(self):
        self.client = SupabaseCRMClient().client  # Use the supabase client directly
        self.enabled = True

        # Configuración de TTL por defecto (en segundos)
        self.default_ttl = {
            "2fa_temp_session": 300,  # 5 minutos
            "pending_2fa": 1800,  # 30 minutos
            "password_reset": 3600,  # 1 hora
            "email_confirmation": 86400,  # 24 horas
            "rate_limit": 3600,  # 1 hora
            "session_cache": 1800,  # 30 minutos
        }

    def _get_expiration_time(self, ttl_key: str) -> datetime:
        """Calculate expiration time based on TTL"""
        ttl_seconds = self.default_ttl.get(ttl_key, 3600)
        return datetime.utcnow() + timedelta(seconds=ttl_seconds)

    def _serialize_data(self, data: Any) -> str:
        """Serializar datos para Supabase"""
        return json.dumps(data, default=str)

    def _deserialize_data(self, data: str) -> Any:
        """Deserializar datos de Supabase"""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data

    # ===================== SESIONES TEMPORALES 2FA =====================

    async def store_2fa_temp_session(
        self,
        user_id: str,
        temp_token: str,
        ip_address: str,
        user_agent: str,
    ) -> bool:
        """Almacenar sesión temporal para 2FA"""
        try:
            data = {
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.utcnow().isoformat(),
            }

            expires_at = self._get_expiration_time("2fa_temp_session")

            result = (
                self.client.table("auth_temp_sessions")
                .upsert(
                    {
                        "token": temp_token,
                        "session_type": "2fa_temp",
                        "user_id": user_id,
                        "data": self._serialize_data(data),
                        "expires_at": expires_at.isoformat(),
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error storing 2FA temp session: {e}")
            return False

    async def get_2fa_temp_session(self, temp_token: str) -> Optional[Dict[str, Any]]:
        """Obtener sesión temporal 2FA"""
        try:
            # Clean up expired sessions first
            await self._cleanup_expired_sessions("2fa_temp")

            result = (
                self.client.table("auth_temp_sessions")
                .select("*")
                .eq("token", temp_token)
                .eq("session_type", "2fa_temp")
                .gte("expires_at", datetime.utcnow().isoformat())
                .execute()
            )

            if result.data:
                session_data = result.data[0]
                return self._deserialize_data(session_data["data"])

            return None

        except Exception as e:
            logger.error(f"Error getting 2FA temp session: {e}")
            return None

    async def cleanup_2fa_temp_session(self, temp_token: str) -> bool:
        """Limpiar sesión temporal 2FA"""
        try:
            result = (
                self.client.table("auth_temp_sessions")
                .delete()
                .eq("token", temp_token)
                .eq("session_type", "2fa_temp")
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error cleaning up 2FA temp session: {e}")
            return False

    # ===================== CONFIGURACIÓN 2FA PENDIENTE =====================

    async def store_pending_2fa(
        self, user_id: str, secret: str, backup_codes: List[str]
    ) -> bool:
        """Almacenar configuración pendiente de 2FA"""
        try:
            data = {
                "secret": secret,
                "backup_codes": backup_codes,
                "created_at": datetime.utcnow().isoformat(),
            }

            expires_at = self._get_expiration_time("pending_2fa")

            result = (
                self.client.table("auth_temp_sessions")
                .upsert(
                    {
                        "token": f"pending_2fa_{user_id}",
                        "session_type": "pending_2fa",
                        "user_id": user_id,
                        "data": self._serialize_data(data),
                        "expires_at": expires_at.isoformat(),
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error storing pending 2FA: {e}")
            return False

    async def get_pending_2fa(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtener configuración pendiente de 2FA"""
        try:
            # Clean up expired sessions first
            await self._cleanup_expired_sessions("pending_2fa")

            result = (
                self.client.table("auth_temp_sessions")
                .select("*")
                .eq("user_id", user_id)
                .eq("session_type", "pending_2fa")
                .gte("expires_at", datetime.utcnow().isoformat())
                .execute()
            )

            if result.data:
                session_data = result.data[0]
                return self._deserialize_data(session_data["data"])

            return None

        except Exception as e:
            logger.error(f"Error getting pending 2FA: {e}")
            return None

    async def cleanup_pending_2fa(self, user_id: str) -> bool:
        """Limpiar configuración pendiente de 2FA"""
        try:
            result = (
                self.client.table("auth_temp_sessions")
                .delete()
                .eq("user_id", user_id)
                .eq("session_type", "pending_2fa")
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error cleaning up pending 2FA: {e}")
            return False

    # ===================== RATE LIMITING =====================

    async def check_rate_limit(
        self, identifier: str, limit: int, window: int = 3600
    ) -> Dict[str, Any]:
        """Verificar rate limiting usando Supabase"""
        try:
            # Clean up expired rate limit entries first
            await self._cleanup_expired_rate_limits()

            window_start = datetime.utcnow() - timedelta(seconds=window)

            # Count requests in the current window
            result = (
                self.client.table("rate_limits")
                .select("*")
                .eq("identifier", identifier)
                .gte("created_at", window_start.isoformat())
                .execute()
            )

            current_count = len(result.data)

            # Add current request
            self.client.table("rate_limits").insert(
                {
                    "identifier": identifier,
                    "created_at": datetime.utcnow().isoformat(),
                    "expires_at": (
                        datetime.utcnow() + timedelta(seconds=window)
                    ).isoformat(),
                }
            ).execute()

            new_count = current_count + 1

            return {
                "allowed": new_count <= limit,
                "count": new_count,
                "limit": limit,
                "window": window,
                "reset_time": int(
                    (datetime.utcnow() + timedelta(seconds=window)).timestamp()
                ),
            }

        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Allow request if rate limiting fails
            return {
                "allowed": True,
                "count": 0,
                "limit": limit,
                "window": window,
                "reset_time": int(
                    (datetime.utcnow() + timedelta(seconds=window)).timestamp()
                ),
            }

    # ===================== CACHE DE SESIONES =====================

    async def cache_user_session(
        self, session_id: str, user_data: Dict[str, Any]
    ) -> bool:
        """Cachear datos de sesión de usuario"""
        try:
            expires_at = self._get_expiration_time("session_cache")

            result = (
                self.client.table("auth_temp_sessions")
                .upsert(
                    {
                        "token": session_id,
                        "session_type": "user_session",
                        "user_id": user_data.get("user_id", "unknown"),
                        "data": self._serialize_data(user_data),
                        "expires_at": expires_at.isoformat(),
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error caching user session: {e}")
            return False

    async def get_cached_user_session(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtener datos de sesión cacheados"""
        try:
            # Clean up expired sessions first
            await self._cleanup_expired_sessions("user_session")

            result = (
                self.client.table("auth_temp_sessions")
                .select("*")
                .eq("token", session_id)
                .eq("session_type", "user_session")
                .gte("expires_at", datetime.utcnow().isoformat())
                .execute()
            )

            if result.data:
                session_data = result.data[0]
                return self._deserialize_data(session_data["data"])

            return None

        except Exception as e:
            logger.error(f"Error getting cached user session: {e}")
            return None

    async def invalidate_user_session_cache(self, session_id: str) -> bool:
        """Invalidar cache de sesión de usuario"""
        try:
            result = (
                self.client.table("auth_temp_sessions")
                .delete()
                .eq("token", session_id)
                .eq("session_type", "user_session")
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error invalidating user session cache: {e}")
            return False

    # ===================== TOKENS DE RESET DE CONTRASEÑA =====================

    async def store_password_reset_token(
        self, user_id: str, token: str, expires_in: Optional[int] = None
    ) -> bool:
        """Almacenar token de reset de contraseña"""
        try:
            ttl = (
                expires_in
                if expires_in is not None
                else self.default_ttl["password_reset"]
            )
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)

            data = {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
            }

            result = (
                self.client.table("auth_temp_sessions")
                .upsert(
                    {
                        "token": token,
                        "session_type": "password_reset",
                        "user_id": user_id,
                        "data": self._serialize_data(data),
                        "expires_at": expires_at.isoformat(),
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error storing password reset token: {e}")
            return False

    async def get_password_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Obtener token de reset de contraseña"""
        try:
            # Clean up expired tokens first
            await self._cleanup_expired_sessions("password_reset")

            result = (
                self.client.table("auth_temp_sessions")
                .select("*")
                .eq("token", token)
                .eq("session_type", "password_reset")
                .gte("expires_at", datetime.utcnow().isoformat())
                .execute()
            )

            if result.data:
                session_data = result.data[0]
                return self._deserialize_data(session_data["data"])

            return None

        except Exception as e:
            logger.error(f"Error getting password reset token: {e}")
            return None

    async def invalidate_password_reset_token(self, token: str) -> bool:
        """Invalidar token de reset de contraseña"""
        try:
            result = (
                self.client.table("auth_temp_sessions")
                .delete()
                .eq("token", token)
                .eq("session_type", "password_reset")
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error invalidating password reset token: {e}")
            return False

    # ===================== BLOQUEO TEMPORAL DE USUARIOS =====================

    async def block_user_temporarily(self, user_id: str, duration: int = 900) -> bool:
        """Bloquear usuario temporalmente"""
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=duration)

            data = {
                "reason": "temporary_block",
                "duration": duration,
                "created_at": datetime.utcnow().isoformat(),
            }

            result = (
                self.client.table("auth_temp_sessions")
                .upsert(
                    {
                        "token": f"block_{user_id}",
                        "session_type": "user_block",
                        "user_id": user_id,
                        "data": self._serialize_data(data),
                        "expires_at": expires_at.isoformat(),
                        "created_at": datetime.utcnow().isoformat(),
                    }
                )
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error blocking user temporarily: {e}")
            return False

    async def is_user_blocked(self, user_id: str) -> bool:
        """Verificar si el usuario está bloqueado"""
        try:
            # Clean up expired blocks first
            await self._cleanup_expired_sessions("user_block")

            result = (
                self.client.table("auth_temp_sessions")
                .select("*")
                .eq("user_id", user_id)
                .eq("session_type", "user_block")
                .gte("expires_at", datetime.utcnow().isoformat())
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error checking if user is blocked: {e}")
            return False

    async def unblock_user(self, user_id: str) -> bool:
        """Desbloquear usuario"""
        try:
            result = (
                self.client.table("auth_temp_sessions")
                .delete()
                .eq("user_id", user_id)
                .eq("session_type", "user_block")
                .execute()
            )

            return len(result.data) > 0

        except Exception as e:
            logger.error(f"Error unblocking user: {e}")
            return False

    # ===================== ESTADÍSTICAS Y UTILIDADES =====================

    async def get_auth_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de autenticación"""
        try:
            # Get count by session type
            stats = {}

            for session_type in [
                "2fa_temp",
                "pending_2fa",
                "user_session",
                "password_reset",
                "user_block",
            ]:
                result = (
                    self.client.table("auth_temp_sessions")
                    .select("*")
                    .eq("session_type", session_type)
                    .gte("expires_at", datetime.utcnow().isoformat())
                    .execute()
                )

                stats[f"active_{session_type}_sessions"] = len(result.data)

            # Get rate limit stats
            rate_limit_result = (
                self.client.table("rate_limits")
                .select("*")
                .gte("expires_at", datetime.utcnow().isoformat())
                .execute()
            )

            stats["active_rate_limits"] = len(rate_limit_result.data)

            return {
                "status": "healthy",
                "stats": stats,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting auth stats: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def cleanup_expired_keys(self) -> int:
        """Limpiar claves expiradas"""
        try:
            total_cleaned = 0

            # Clean up expired auth sessions
            sessions_result = (
                self.client.table("auth_temp_sessions")
                .delete()
                .lt("expires_at", datetime.utcnow().isoformat())
                .execute()
            )

            total_cleaned += len(sessions_result.data)

            # Clean up expired rate limits
            rate_limits_result = (
                self.client.table("rate_limits")
                .delete()
                .lt("expires_at", datetime.utcnow().isoformat())
                .execute()
            )

            total_cleaned += len(rate_limits_result.data)

            logger.info(f"Cleaned up {total_cleaned} expired keys")
            return total_cleaned

        except Exception as e:
            logger.error(f"Error cleaning up expired keys: {e}")
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """Verificar salud del sistema de autenticación"""
        try:
            # Test connection by running a simple query
            result = (
                self.client.table("auth_temp_sessions").select("*").limit(1).execute()
            )

            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "connection": "active",
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "connection": "failed",
            }

    # ===================== MÉTODOS PRIVADOS =====================

    async def _cleanup_expired_sessions(self, session_type: str) -> int:
        """Limpiar sesiones expiradas de un tipo específico"""
        try:
            result = (
                self.client.table("auth_temp_sessions")
                .delete()
                .eq("session_type", session_type)
                .lt("expires_at", datetime.utcnow().isoformat())
                .execute()
            )

            return len(result.data)

        except Exception as e:
            logger.error(f"Error cleaning up expired {session_type} sessions: {e}")
            return 0

    async def _cleanup_expired_rate_limits(self) -> int:
        """Limpiar rate limits expirados"""
        try:
            result = (
                self.client.table("rate_limits")
                .delete()
                .lt("expires_at", datetime.utcnow().isoformat())
                .execute()
            )

            return len(result.data)

        except Exception as e:
            logger.error(f"Error cleaning up expired rate limits: {e}")
            return 0

    async def close(self):
        """Cerrar conexión (no necesario para Supabase, pero mantenemos compatibilidad)"""
        logger.info("Supabase auth client closed")


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

_supabase_auth_client = None


async def get_supabase_auth_client() -> SupabaseAuthClient:
    """Get or create Supabase auth client singleton"""
    global _supabase_auth_client
    if _supabase_auth_client is None:
        _supabase_auth_client = SupabaseAuthClient()
    return _supabase_auth_client


async def cleanup_supabase_auth_keys():
    """Clean up expired keys using Supabase auth client"""
    client = await get_supabase_auth_client()
    return await client.cleanup_expired_keys()


async def supabase_auth_health_check():
    """Health check for Supabase auth system"""
    client = await get_supabase_auth_client()
    return await client.health_check()
