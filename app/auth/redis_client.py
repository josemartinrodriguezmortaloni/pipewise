# app/auth/redis_client.py
import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import timedelta
import redis
from redis.exceptions import ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class RedisAuthClient:
    """Cliente Redis para manejo de sesiones temporales y cache de autenticación"""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.enabled = True

        # Configuración de TTL por defecto
        self.default_ttl = {
            "2fa_temp_session": 300,  # 5 minutos
            "pending_2fa": 1800,  # 30 minutos
            "password_reset": 3600,  # 1 hora
            "email_confirmation": 86400,  # 24 horas
            "rate_limit": 3600,  # 1 hora
            "session_cache": 1800,  # 30 minutos
        }

        try:
            # Inicializar cliente Redis
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test de conexión
            self.client.ping()
            logger.info("Redis client initialized successfully")

        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                f"Redis connection failed: {e}. Falling back to in-memory storage"
            )
            self.enabled = False
            self._memory_store = {}  # Fallback a memoria

    def _get_key(self, prefix: str, identifier: str) -> str:
        """Generar clave Redis con prefijo"""
        return f"auth:{prefix}:{identifier}"

    def _serialize_data(self, data: Any) -> str:
        """Serializar datos para Redis"""
        return json.dumps(data, default=str)

    def _deserialize_data(self, data: str) -> Any:
        """Deserializar datos de Redis"""
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
            key = self._get_key("2fa_temp", temp_token)
            data = {
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": self._get_current_timestamp(),
            }

            if self.enabled:
                result = self.client.setex(
                    key,
                    self.default_ttl["2fa_temp_session"],
                    self._serialize_data(data),
                )
                return bool(result)
            else:
                # Fallback a memoria
                self._memory_store[key] = {
                    "data": data,
                    "expires_at": self._get_current_timestamp()
                    + self.default_ttl["2fa_temp_session"],
                }
                return True

        except Exception as e:
            logger.error(f"Error storing 2FA temp session: {e}")
            return False

    async def get_2fa_temp_session(self, temp_token: str) -> Optional[Dict[str, Any]]:
        """Obtener sesión temporal 2FA"""
        try:
            key = self._get_key("2fa_temp", temp_token)

            if self.enabled:
                data = self.client.get(key)
                if data:
                    return self._deserialize_data(data)
            else:
                # Fallback a memoria
                stored = self._memory_store.get(key)
                if stored and stored["expires_at"] > self._get_current_timestamp():
                    return stored["data"]
                elif stored:
                    del self._memory_store[key]  # Limpiar expirado

            return None

        except Exception as e:
            logger.error(f"Error getting 2FA temp session: {e}")
            return None

    async def cleanup_2fa_temp_session(self, temp_token: str) -> bool:
        """Limpiar sesión temporal 2FA"""
        try:
            key = self._get_key("2fa_temp", temp_token)

            if self.enabled:
                result = self.client.delete(key)
                return bool(result)
            else:
                # Fallback a memoria
                if key in self._memory_store:
                    del self._memory_store[key]
                    return True

            return False

        except Exception as e:
            logger.error(f"Error cleaning up 2FA temp session: {e}")
            return False

    # ===================== CONFIGURACIÓN 2FA PENDIENTE =====================

    async def store_pending_2fa(
        self, user_id: str, secret: str, backup_codes: List[str]
    ) -> bool:
        """Almacenar configuración pendiente de 2FA"""
        try:
            key = self._get_key("pending_2fa", user_id)
            data = {
                "secret": secret,
                "backup_codes": backup_codes,
                "created_at": self._get_current_timestamp(),
            }

            if self.enabled:
                result = self.client.setex(
                    key, self.default_ttl["pending_2fa"], self._serialize_data(data)
                )
                return bool(result)
            else:
                # Fallback a memoria
                self._memory_store[key] = {
                    "data": data,
                    "expires_at": self._get_current_timestamp()
                    + self.default_ttl["pending_2fa"],
                }
                return True

        except Exception as e:
            logger.error(f"Error storing pending 2FA: {e}")
            return False

    async def get_pending_2fa(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtener configuración pendiente de 2FA"""
        try:
            key = self._get_key("pending_2fa", user_id)

            if self.enabled:
                data = self.client.get(key)
                if data:
                    return self._deserialize_data(data)
            else:
                # Fallback a memoria
                stored = self._memory_store.get(key)
                if stored and stored["expires_at"] > self._get_current_timestamp():
                    return stored["data"]
                elif stored:
                    del self._memory_store[key]

            return None

        except Exception as e:
            logger.error(f"Error getting pending 2FA: {e}")
            return None

    async def cleanup_pending_2fa(self, user_id: str) -> bool:
        """Limpiar configuración pendiente de 2FA"""
        try:
            key = self._get_key("pending_2fa", user_id)

            if self.enabled:
                result = self.client.delete(key)
                return bool(result)
            else:
                # Fallback a memoria
                if key in self._memory_store:
                    del self._memory_store[key]
                    return True

            return False

        except Exception as e:
            logger.error(f"Error cleaning up pending 2FA: {e}")
            return False

    # ===================== RATE LIMITING =====================

    async def check_rate_limit(
        self, identifier: str, limit: int, window: int = 3600
    ) -> Dict[str, Any]:
        """Verificar y actualizar rate limit"""
        try:
            key = self._get_key("rate_limit", identifier)

            if self.enabled:
                # Usar sliding window con Redis
                current_time = self._get_current_timestamp()
                pipe = self.client.pipeline()

                # Limpiar requests antiguos
                pipe.zremrangebyscore(key, 0, current_time - window)

                # Contar requests actuales
                pipe.zcard(key)

                # Agregar request actual
                pipe.zadd(key, {str(current_time): current_time})

                # Establecer expiración
                pipe.expire(key, window)

                results = pipe.execute()
                current_count = results[1]

                return {
                    "allowed": current_count < limit,
                    "count": current_count,
                    "limit": limit,
                    "reset_time": current_time + window,
                }
            else:
                # Fallback básico a memoria
                current_time = self._get_current_timestamp()

                if key not in self._memory_store:
                    self._memory_store[key] = {
                        "requests": [],
                        "reset_time": current_time + window,
                    }

                rate_data = self._memory_store[key]

                # Limpiar requests antiguos
                rate_data["requests"] = [
                    req for req in rate_data["requests"] if req > current_time - window
                ]

                # Agregar request actual
                rate_data["requests"].append(current_time)

                return {
                    "allowed": len(rate_data["requests"]) <= limit,
                    "count": len(rate_data["requests"]),
                    "limit": limit,
                    "reset_time": rate_data["reset_time"],
                }

        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return {"allowed": True, "count": 0, "limit": limit, "reset_time": 0}

    # ===================== CACHE DE SESIONES =====================

    async def cache_user_session(
        self, session_id: str, user_data: Dict[str, Any]
    ) -> bool:
        """Cachear datos de sesión de usuario"""
        try:
            key = self._get_key("session_cache", session_id)

            if self.enabled:
                result = self.client.setex(
                    key,
                    self.default_ttl["session_cache"],
                    self._serialize_data(user_data),
                )
                return bool(result)
            else:
                # Fallback a memoria
                self._memory_store[key] = {
                    "data": user_data,
                    "expires_at": self._get_current_timestamp()
                    + self.default_ttl["session_cache"],
                }
                return True

        except Exception as e:
            logger.error(f"Error caching user session: {e}")
            return False

    async def get_cached_user_session(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtener datos de sesión cacheados"""
        try:
            key = self._get_key("session_cache", session_id)

            if self.enabled:
                data = self.client.get(key)
                if data:
                    return self._deserialize_data(data)
            else:
                # Fallback a memoria
                stored = self._memory_store.get(key)
                if stored and stored["expires_at"] > self._get_current_timestamp():
                    return stored["data"]
                elif stored:
                    del self._memory_store[key]

            return None

        except Exception as e:
            logger.error(f"Error getting cached user session: {e}")
            return None

    async def invalidate_user_session_cache(self, session_id: str) -> bool:
        """Invalidar cache de sesión"""
        try:
            key = self._get_key("session_cache", session_id)

            if self.enabled:
                result = self.client.delete(key)
                return bool(result)
            else:
                # Fallback a memoria
                if key in self._memory_store:
                    del self._memory_store[key]
                    return True

            return False

        except Exception as e:
            logger.error(f"Error invalidating session cache: {e}")
            return False

    # ===================== TOKENS DE RECUPERACIÓN =====================

    async def store_password_reset_token(
        self, user_id: str, token: str, expires_in: int = None
    ) -> bool:
        """Almacenar token de reset de contraseña"""
        try:
            key = self._get_key("password_reset", token)
            data = {"user_id": user_id, "created_at": self._get_current_timestamp()}

            ttl = expires_in or self.default_ttl["password_reset"]

            if self.enabled:
                result = self.client.setex(key, ttl, self._serialize_data(data))
                return bool(result)
            else:
                # Fallback a memoria
                self._memory_store[key] = {
                    "data": data,
                    "expires_at": self._get_current_timestamp() + ttl,
                }
                return True

        except Exception as e:
            logger.error(f"Error storing password reset token: {e}")
            return False

    async def get_password_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Obtener datos del token de reset"""
        try:
            key = self._get_key("password_reset", token)

            if self.enabled:
                data = self.client.get(key)
                if data:
                    return self._deserialize_data(data)
            else:
                # Fallback a memoria
                stored = self._memory_store.get(key)
                if stored and stored["expires_at"] > self._get_current_timestamp():
                    return stored["data"]
                elif stored:
                    del self._memory_store[key]

            return None

        except Exception as e:
            logger.error(f"Error getting password reset token: {e}")
            return None

    async def invalidate_password_reset_token(self, token: str) -> bool:
        """Invalidar token de reset usado"""
        try:
            key = self._get_key("password_reset", token)

            if self.enabled:
                result = self.client.delete(key)
                return bool(result)
            else:
                # Fallback a memoria
                if key in self._memory_store:
                    del self._memory_store[key]
                    return True

            return False

        except Exception as e:
            logger.error(f"Error invalidating password reset token: {e}")
            return False

    # ===================== BLOQUEO DE USUARIOS =====================

    async def block_user_temporarily(self, user_id: str, duration: int = 900) -> bool:
        """Bloquear usuario temporalmente (15 min por defecto)"""
        try:
            key = self._get_key("blocked_user", user_id)
            data = {
                "blocked_at": self._get_current_timestamp(),
                "reason": "temporary_block",
            }

            if self.enabled:
                result = self.client.setex(key, duration, self._serialize_data(data))
                return bool(result)
            else:
                # Fallback a memoria
                self._memory_store[key] = {
                    "data": data,
                    "expires_at": self._get_current_timestamp() + duration,
                }
                return True

        except Exception as e:
            logger.error(f"Error blocking user temporarily: {e}")
            return False

    async def is_user_blocked(self, user_id: str) -> bool:
        """Verificar si un usuario está bloqueado"""
        try:
            key = self._get_key("blocked_user", user_id)

            if self.enabled:
                return bool(self.client.exists(key))
            else:
                # Fallback a memoria
                stored = self._memory_store.get(key)
                if stored and stored["expires_at"] > self._get_current_timestamp():
                    return True
                elif stored:
                    del self._memory_store[key]
                    return False

            return False

        except Exception as e:
            logger.error(f"Error checking if user is blocked: {e}")
            return False

    async def unblock_user(self, user_id: str) -> bool:
        """Desbloquear usuario"""
        try:
            key = self._get_key("blocked_user", user_id)

            if self.enabled:
                result = self.client.delete(key)
                return bool(result)
            else:
                # Fallback a memoria
                if key in self._memory_store:
                    del self._memory_store[key]
                    return True

            return False

        except Exception as e:
            logger.error(f"Error unblocking user: {e}")
            return False

    # ===================== ESTADÍSTICAS Y MONITOREO =====================

    async def get_auth_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de autenticación de Redis"""
        try:
            stats = {
                "redis_enabled": self.enabled,
                "active_2fa_sessions": 0,
                "pending_2fa_configs": 0,
                "active_sessions": 0,
                "blocked_users": 0,
                "active_rate_limits": 0,
            }

            if self.enabled:
                # Contar claves por tipo
                patterns = {
                    "active_2fa_sessions": "auth:2fa_temp:*",
                    "pending_2fa_configs": "auth:pending_2fa:*",
                    "active_sessions": "auth:session_cache:*",
                    "blocked_users": "auth:blocked_user:*",
                    "active_rate_limits": "auth:rate_limit:*",
                }

                for stat_name, pattern in patterns.items():
                    try:
                        keys = self.client.keys(pattern)
                        stats[stat_name] = len(keys)
                    except Exception as e:
                        logger.warning(f"Error counting {stat_name}: {e}")
            else:
                # Contar en memoria
                for key in self._memory_store:
                    if "2fa_temp" in key:
                        stats["active_2fa_sessions"] += 1
                    elif "pending_2fa" in key:
                        stats["pending_2fa_configs"] += 1
                    elif "session_cache" in key:
                        stats["active_sessions"] += 1
                    elif "blocked_user" in key:
                        stats["blocked_users"] += 1
                    elif "rate_limit" in key:
                        stats["active_rate_limits"] += 1

            return stats

        except Exception as e:
            logger.error(f"Error getting auth stats: {e}")
            return {"error": str(e)}

    # ===================== LIMPIEZA Y MANTENIMIENTO =====================

    async def cleanup_expired_keys(self) -> int:
        """Limpiar claves expiradas (solo para modo memoria)"""
        if self.enabled:
            return 0  # Redis maneja expiración automáticamente

        try:
            current_time = self._get_current_timestamp()
            expired_keys = []

            for key, value in self._memory_store.items():
                if isinstance(value, dict) and "expires_at" in value:
                    if value["expires_at"] <= current_time:
                        expired_keys.append(key)

            for key in expired_keys:
                del self._memory_store[key]

            logger.info(f"Cleaned up {len(expired_keys)} expired keys from memory")
            return len(expired_keys)

        except Exception as e:
            logger.error(f"Error cleaning up expired keys: {e}")
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """Verificar salud del cliente Redis"""
        try:
            if self.enabled:
                # Test de ping
                self.client.ping()

                # Obtener info del servidor
                info = self.client.info()

                return {
                    "status": "healthy",
                    "enabled": True,
                    "redis_version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "uptime_in_seconds": info.get("uptime_in_seconds"),
                }
            else:
                return {
                    "status": "fallback",
                    "enabled": False,
                    "mode": "in_memory",
                    "stored_keys": len(self._memory_store),
                }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": str(e), "enabled": self.enabled}

    # ===================== UTILIDADES =====================

    def _get_current_timestamp(self) -> int:
        """Obtener timestamp actual en segundos"""
        from datetime import datetime, timezone

        return int(datetime.now(timezone.utc).timestamp())

    async def close(self):
        """Cerrar conexión Redis"""
        try:
            if self.enabled and hasattr(self, "client"):
                self.client.close()
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# ===================== INSTANCIA GLOBAL =====================

# Crear instancia global del cliente Redis
redis_auth_client = RedisAuthClient()


# ===================== FUNCIONES DE CONVENIENCIA =====================


async def get_redis_client() -> RedisAuthClient:
    """Obtener cliente Redis para dependency injection"""
    return redis_auth_client


async def cleanup_redis_keys():
    """Función para limpiar claves expiradas (usar en tareas programadas)"""
    return await redis_auth_client.cleanup_expired_keys()


async def redis_health_check():
    """Health check de Redis"""
    return await redis_auth_client.health_check()
