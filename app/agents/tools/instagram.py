import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class InstagramClient:
    """Cliente para interactuar con Instagram Graph API (Direct Messages)"""

    def __init__(self, access_token: str = None, instagram_business_id: str = None):
        self.access_token = access_token or os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.instagram_business_id = instagram_business_id or os.getenv(
            "INSTAGRAM_BUSINESS_ID"
        )
        self.base_url = "https://graph.facebook.com/v18.0"

        if self.access_token and self.instagram_business_id:
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            self.enabled = True
            logger.info("Instagram client initialized with API credentials")
        else:
            self.headers = {}
            self.enabled = False
            logger.warning(
                "Instagram client initialized without credentials - using demo mode"
            )

    def _make_request(
        self, method: str, endpoint: str, data: Dict = None, params: Dict = None
    ) -> Dict:
        """Realizar solicitud HTTP a la API de Instagram"""
        if not self.enabled:
            return {
                "success": True,
                "message_id": f"demo_ig_{datetime.now().timestamp()}",
            }

        url = f"{self.base_url}/{endpoint}"

        try:
            if method.upper() == "POST":
                response = requests.post(
                    url,
                    headers=self.headers,
                    json=data,
                    timeout=10,
                )
            elif method.upper() == "GET":
                response = requests.get(url, headers=self.headers, params=params)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error en solicitud Instagram {method} {endpoint}: {e}")
            raise Exception(f"Error de API Instagram: {str(e)}")

    def send_direct_message(self, recipient_id: str, message: str) -> Dict:
        """Enviar mensaje directo a un usuario"""
        data = {"recipient": {"id": recipient_id}, "message": {"text": message}}

        if not self.enabled:
            logger.info(f"[DEMO] Instagram DM to {recipient_id}: {message}")
            return {
                "success": True,
                "message_id": f"demo_ig_{datetime.now().timestamp()}",
                "to": recipient_id,
                "message": message,
                "sent_at": datetime.now().isoformat(),
                "platform": "instagram",
            }

        endpoint = f"{self.instagram_business_id}/messages"
        result = self._make_request("POST", endpoint, data)

        return {
            "success": True,
            "message_id": result.get("message_id"),
            "to": recipient_id,
            "message": message,
            "sent_at": datetime.now().isoformat(),
            "platform": "instagram",
        }

    def send_story_reply(self, story_id: str, message: str) -> Dict:
        """Responder a una historia de Instagram"""
        data = {"message": {"text": message}, "story_id": story_id}

        if not self.enabled:
            logger.info(f"[DEMO] Instagram story reply to {story_id}: {message}")
            return {
                "success": True,
                "message_id": f"demo_story_{datetime.now().timestamp()}",
                "story_id": story_id,
                "message": message,
                "sent_at": datetime.now().isoformat(),
                "platform": "instagram",
            }

        endpoint = f"{self.instagram_business_id}/messages"
        result = self._make_request("POST", endpoint, data)

        return {
            "success": True,
            "message_id": result.get("message_id"),
            "story_id": story_id,
            "message": message,
            "sent_at": datetime.now().isoformat(),
            "platform": "instagram",
        }

    def get_user_info(self, user_id: str) -> Dict:
        """Obtener información básica de un usuario"""
        if not self.enabled:
            return {
                "id": user_id,
                "username": f"demo_user_{user_id[-4:]}",
                "name": "Demo User",
                "profile_pic": None,
                "platform": "instagram",
            }

        params = {"fields": "id,username,name,profile_pic"}
        result = self._make_request("GET", user_id, params=params)

        return {
            "id": result.get("id"),
            "username": result.get("username"),
            "name": result.get("name"),
            "profile_pic": result.get("profile_pic"),
            "platform": "instagram",
        }

    def get_conversations(self) -> Dict:
        """Obtener lista de conversaciones activas"""
        if not self.enabled:
            return {
                "conversations": [
                    {
                        "id": f"demo_conv_{i}",
                        "participant": f"demo_user_{i}",
                        "updated_time": datetime.now().isoformat(),
                        "unread_count": 0,
                    }
                    for i in range(3)
                ],
                "platform": "instagram",
            }

        endpoint = f"{self.instagram_business_id}/conversations"
        params = {"fields": "id,participants,updated_time,unread_count"}
        result = self._make_request("GET", endpoint, params=params)

        conversations = []
        for conv in result.get("data", []):
            conversations.append(
                {
                    "id": conv.get("id"),
                    "participants": conv.get("participants", {}).get("data", []),
                    "updated_time": conv.get("updated_time"),
                    "unread_count": conv.get("unread_count", 0),
                }
            )

        return {"conversations": conversations, "platform": "instagram"}

    def get_conversation_messages(self, conversation_id: str) -> Dict:
        """Obtener mensajes de una conversación específica"""
        if not self.enabled:
            return {
                "messages": [
                    {
                        "id": f"demo_msg_{i}",
                        "message": f"Demo message {i}",
                        "created_time": datetime.now().isoformat(),
                        "from": "user" if i % 2 == 0 else "page",
                    }
                    for i in range(5)
                ],
                "conversation_id": conversation_id,
                "platform": "instagram",
            }

        endpoint = f"{conversation_id}/messages"
        params = {"fields": "id,message,created_time,from"}
        result = self._make_request("GET", endpoint, params=params)

        return {
            "messages": result.get("data", []),
            "conversation_id": conversation_id,
            "platform": "instagram",
        }

    def process_webhook_message(self, webhook_data: Dict) -> Dict:
        """Procesar mensaje recibido via webhook"""
        try:
            entry = webhook_data.get("entry", [{}])[0]
            messaging = entry.get("messaging", [{}])[0]

            if "message" in messaging:
                return {
                    "message_id": messaging["message"].get("mid"),
                    "from": messaging["sender"]["id"],
                    "to": messaging["recipient"]["id"],
                    "text": messaging["message"].get("text"),
                    "timestamp": datetime.fromtimestamp(
                        int(messaging.get("timestamp", 0)) / 1000
                    ).isoformat(),
                    "platform": "instagram",
                }

            return None

        except Exception as e:
            logger.error(f"Error processing Instagram webhook: {e}")
            return None

    def search_users(self, query: str) -> Dict:
        """Buscar usuarios por nombre o username"""
        if not self.enabled:
            return {
                "users": [
                    {
                        "id": f"demo_user_{i}",
                        "username": f"user_{query.lower()}_{i}",
                        "name": f"{query} Demo {i}",
                        "profile_pic": None,
                    }
                    for i in range(3)
                ],
                "query": query,
                "platform": "instagram",
            }

        # En Instagram Graph API la búsqueda de usuarios es limitada
        # Solo puedes buscar usuarios que ya han interactuado contigo
        endpoint = f"{self.instagram_business_id}/conversations"
        params = {"fields": "participants"}
        result = self._make_request("GET", endpoint, params=params)

        # Filtrar conversaciones que contengan el query
        matching_users = []
        for conv in result.get("data", []):
            for participant in conv.get("participants", {}).get("data", []):
                user_info = self.get_user_info(participant["id"])
                if (
                    query.lower() in user_info.get("username", "").lower()
                    or query.lower() in user_info.get("name", "").lower()
                ):
                    matching_users.append(user_info)

        return {"users": matching_users, "query": query, "platform": "instagram"}

    def health_check(self) -> Dict:
        """Verificar estado de la conexión"""
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "message": "Instagram API not configured",
                    "demo_mode": True,
                }

            # Verificar credenciales
            params = {"fields": "id,name"}
            result = self._make_request(
                "GET", self.instagram_business_id, params=params
            )

            return {
                "status": "healthy",
                "business_id": self.instagram_business_id,
                "business_name": result.get("name"),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


def get_instagram_client() -> InstagramClient:
    """Obtener instancia del cliente de Instagram"""
    return InstagramClient()
