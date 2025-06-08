import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class TwitterClient:
    """Cliente para interactuar con Twitter API v2 (Direct Messages)"""

    def __init__(
        self,
        bearer_token: str = None,
        api_key: str = None,
        api_secret: str = None,
        access_token: str = None,
        access_token_secret: str = None,
    ):
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        self.api_key = api_key or os.getenv("TWITTER_API_KEY")
        self.api_secret = api_secret or os.getenv("TWITTER_API_SECRET")
        self.access_token = access_token or os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = access_token_secret or os.getenv(
            "TWITTER_ACCESS_TOKEN_SECRET"
        )

        self.base_url = "https://api.twitter.com/2"

        if all(
            [self.api_key, self.api_secret, self.access_token, self.access_token_secret]
        ):
            self.headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
            }
            self.enabled = True
            logger.info("Twitter client initialized with API credentials")
        else:
            self.headers = {}
            self.enabled = False
            logger.warning(
                "Twitter client initialized without credentials - using demo mode"
            )

    def _make_request(
        self, method: str, endpoint: str, data: Dict = None, params: Dict = None
    ) -> Dict:
        """Realizar solicitud HTTP a la API de Twitter"""
        if not self.enabled:
            return {
                "success": True,
                "message_id": f"demo_twitter_{datetime.now().timestamp()}",
            }

        url = f"{self.base_url}/{endpoint}"

        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "GET":
                response = requests.get(url, headers=self.headers, params=params)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")

            response.raise_for_status()
            if response.status_code == 204:
                return {"success": True}
            try:
                return response.json()
            except ValueError:
                return {"success": True, "raw": response.text}

        except requests.exceptions.RequestException as e:
            logger.error(f"Error en solicitud Twitter {method} {endpoint}: {e}")
            raise Exception(f"Error de API Twitter: {str(e)}")

    def send_direct_message(self, recipient_id: str, message: str) -> Dict:
        """Enviar mensaje directo a un usuario"""
        data = {
            "dm_conversation_id": f"{recipient_id}-dm",
            "text": message,
            "attachments": [],
        }

        if not self.enabled:
            logger.info(f"[DEMO] Twitter DM to {recipient_id}: {message}")
            return {
                "success": True,
                "message_id": f"demo_twitter_{datetime.now().timestamp()}",
                "to": recipient_id,
                "message": message,
                "sent_at": datetime.now().isoformat(),
                "platform": "twitter",
            }

        # Usar endpoint v1.1 para DMs (v2 aún no está completamente disponible)
        v1_url = "https://api.twitter.com/1.1/direct_messages/events/new.json"
        v1_data = {
            "event": {
                "type": "message_create",
                "message_create": {
                    "target": {"recipient_id": recipient_id},
                    "message_data": {"text": message},
                },
            }
        }

        try:
            response = requests.post(v1_url, headers=self.headers, json=v1_data)
            response.raise_for_status()
            result = response.json()

            return {
                "success": True,
                "message_id": result.get("event", {}).get("id"),
                "to": recipient_id,
                "message": message,
                "sent_at": datetime.now().isoformat(),
                "platform": "twitter",
            }
        except Exception as e:
            logger.error(f"Error sending Twitter DM: {e}")
            return {"success": False, "error": str(e), "platform": "twitter"}

    def get_user_by_username(self, username: str) -> Dict:
        """Obtener información de usuario por username"""
        if not self.enabled:
            return {
                "id": f"demo_user_{username}",
                "username": username,
                "name": f"Demo {username}",
                "public_metrics": {
                    "followers_count": 100,
                    "following_count": 50,
                    "tweet_count": 200,
                },
                "platform": "twitter",
            }

        endpoint = f"users/by/username/{username}"
        params = {
            "user.fields": "id,username,name,public_metrics,description,profile_image_url"
        }

        result = self._make_request("GET", endpoint, params=params)

        user_data = result.get("data", {})
        return {
            "id": user_data.get("id"),
            "username": user_data.get("username"),
            "name": user_data.get("name"),
            "description": user_data.get("description"),
            "public_metrics": user_data.get("public_metrics", {}),
            "profile_image_url": user_data.get("profile_image_url"),
            "platform": "twitter",
        }

    def get_user_by_id(self, user_id: str) -> Dict:
        """Obtener información de usuario por ID"""
        if not self.enabled:
            return {
                "id": user_id,
                "username": f"demo_user_{user_id[-4:]}",
                "name": "Demo User",
                "public_metrics": {
                    "followers_count": 100,
                    "following_count": 50,
                    "tweet_count": 200,
                },
                "platform": "twitter",
            }

        endpoint = f"users/{user_id}"
        params = {
            "user.fields": "id,username,name,public_metrics,description,profile_image_url"
        }

        result = self._make_request("GET", endpoint, params=params)

        user_data = result.get("data", {})
        return {
            "id": user_data.get("id"),
            "username": user_data.get("username"),
            "name": user_data.get("name"),
            "description": user_data.get("description"),
            "public_metrics": user_data.get("public_metrics", {}),
            "profile_image_url": user_data.get("profile_image_url"),
            "platform": "twitter",
        }

    def search_users(self, query: str, max_results: int = 10) -> Dict:
        """Buscar usuarios por nombre o username"""
        if not self.enabled:
            return {
                "users": [
                    {
                        "id": f"demo_user_{i}",
                        "username": f"{query.lower()}_{i}",
                        "name": f"{query} Demo {i}",
                        "public_metrics": {
                            "followers_count": 100 + i * 10,
                            "following_count": 50 + i * 5,
                        },
                    }
                    for i in range(min(max_results, 5))
                ],
                "query": query,
                "platform": "twitter",
            }

        # Twitter API v2 no tiene búsqueda directa de usuarios
        # Usamos una aproximación buscando por username
        try:
            user_result = self.get_user_by_username(query)
            if user_result.get("id"):
                return {"users": [user_result], "query": query, "platform": "twitter"}
        except:
            pass

        return {
            "users": [],
            "query": query,
            "platform": "twitter",
            "note": "Twitter API v2 tiene limitaciones en búsqueda de usuarios",
        }

    def get_mentions(self, user_id: str = None, max_results: int = 10) -> Dict:
        """Obtener menciones recientes"""
        if not self.enabled:
            return {
                "mentions": [
                    {
                        "id": f"demo_mention_{i}",
                        "text": f"Demo mention {i} @username",
                        "author_id": f"user_{i}",
                        "created_at": datetime.now().isoformat(),
                        "public_metrics": {
                            "reply_count": i,
                            "retweet_count": i * 2,
                            "like_count": i * 5,
                        },
                    }
                    for i in range(max_results)
                ],
                "platform": "twitter",
            }

        if not user_id:
            # Obtener ID del usuario autenticado
            me_result = self._make_request("GET", "users/me")
            user_id = me_result.get("data", {}).get("id")

        endpoint = f"users/{user_id}/mentions"
        params = {
            "tweet.fields": "id,text,author_id,created_at,public_metrics",
            "max_results": min(max_results, 100),
        }

        result = self._make_request("GET", endpoint, params=params)

        return {"mentions": result.get("data", []), "platform": "twitter"}

    def reply_to_tweet(self, tweet_id: str, message: str) -> Dict:
        """Responder a un tweet"""
        data = {"text": message, "reply": {"in_reply_to_tweet_id": tweet_id}}

        if not self.enabled:
            logger.info(f"[DEMO] Twitter reply to {tweet_id}: {message}")
            return {
                "success": True,
                "tweet_id": f"demo_reply_{datetime.now().timestamp()}",
                "in_reply_to": tweet_id,
                "message": message,
                "sent_at": datetime.now().isoformat(),
                "platform": "twitter",
            }

        result = self._make_request("POST", "tweets", data)

        return {
            "success": True,
            "tweet_id": result.get("data", {}).get("id"),
            "in_reply_to": tweet_id,
            "message": message,
            "sent_at": datetime.now().isoformat(),
            "platform": "twitter",
        }

    def get_my_user_info(self) -> Dict:
        """Obtener información del usuario autenticado"""
        if not self.enabled:
            return {
                "id": "demo_me",
                "username": "demo_bot",
                "name": "Demo Bot",
                "public_metrics": {
                    "followers_count": 1000,
                    "following_count": 100,
                    "tweet_count": 500,
                },
                "platform": "twitter",
            }

        endpoint = "users/me"
        params = {
            "user.fields": "id,username,name,public_metrics,description,profile_image_url"
        }

        result = self._make_request("GET", endpoint, params=params)

        user_data = result.get("data", {})
        return {
            "id": user_data.get("id"),
            "username": user_data.get("username"),
            "name": user_data.get("name"),
            "description": user_data.get("description"),
            "public_metrics": user_data.get("public_metrics", {}),
            "profile_image_url": user_data.get("profile_image_url"),
            "platform": "twitter",
        }

    def health_check(self) -> Dict:
        """Verificar estado de la conexión"""
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "message": "Twitter API not configured",
                    "demo_mode": True,
                }

            # Verificar credenciales obteniendo info del usuario
            user_info = self.get_my_user_info()

            return {
                "status": "healthy",
                "user_id": user_info.get("id"),
                "username": user_info.get("username"),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


def get_twitter_client() -> TwitterClient:
    """Obtener instancia del cliente de Twitter"""
    return TwitterClient()
