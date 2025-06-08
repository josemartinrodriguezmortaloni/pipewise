import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class WhatsAppClient:
    """Cliente para interactuar con WhatsApp Business API"""

    def __init__(self, access_token: str = None, phone_number_id: str = None):
        self.access_token = access_token or os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.phone_number_id = phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.base_url = "https://graph.facebook.com/v18.0"

        if self.access_token and self.phone_number_id:
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            self.enabled = True
            logger.info("WhatsApp client initialized with API credentials")
        else:
            self.headers = {}
            self.enabled = False
            logger.warning(
                "WhatsApp client initialized without credentials - using demo mode"
            )

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Realizar solicitud HTTP a la API de WhatsApp"""
        if not self.enabled:
            return {
                "success": True,
                "message_id": f"demo_msg_{datetime.now().timestamp()}",
            }

        url = f"{self.base_url}/{self.phone_number_id}/{endpoint}"

        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "GET":
                response = requests.get(url, headers=self.headers, params=data)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error en solicitud WhatsApp {method} {endpoint}: {e}")
            raise Exception(f"Error de API WhatsApp: {str(e)}")

    def send_text_message(self, to: str, message: str) -> Dict:
        """Enviar mensaje de texto simple"""
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message},
        }

        if not self.enabled:
            logger.info(f"[DEMO] WhatsApp message to {to}: {message}")
            return {
                "success": True,
                "message_id": f"demo_msg_{datetime.now().timestamp()}",
                "to": to,
                "message": message,
                "sent_at": datetime.now().isoformat(),
            }

        result = self._make_request("POST", "messages", data)
        return {
            "success": True,
            "message_id": result.get("messages", [{}])[0].get("id"),
            "to": to,
            "message": message,
            "sent_at": datetime.now().isoformat(),
        }

def send_template_message(
     self, to: str, template_name: str, parameters: List[str] = None
 ) -> Dict:
     """Enviar mensaje usando template aprobado"""
    # Validate template name
    if not template_name or not template_name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Invalid template name format")
    
    # Validate parameters
    if parameters:
        for param in parameters:
            if len(param) > 1024:  # WhatsApp parameter limit
                raise ValueError(f"Parameter too long: {param[:50]}...")

     data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "es"},
                "components": [],
            },
        }

        if parameters:
            data["template"]["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": param} for param in parameters
                    ],
                }
            ]

        if not self.enabled:
            logger.info(
                f"[DEMO] WhatsApp template {template_name} to {to} with params: {parameters}"
            )
            return {
                "success": True,
                "message_id": f"demo_template_{datetime.now().timestamp()}",
                "to": to,
                "template": template_name,
                "sent_at": datetime.now().isoformat(),
            }

        result = self._make_request("POST", "messages", data)
        return {
            "success": True,
            "message_id": result.get("messages", [{}])[0].get("id"),
            "to": to,
            "template": template_name,
            "sent_at": datetime.now().isoformat(),
        }

    def send_interactive_message(
        self, to: str, body_text: str, buttons: List[Dict]
    ) -> Dict:
        """Enviar mensaje con botones interactivos"""
        interactive_buttons = []
        for i, button in enumerate(buttons[:3]):  # WhatsApp permite máximo 3 botones
            interactive_buttons.append(
                {
                    "type": "reply",
                    "reply": {
                        "id": f"btn_{i}",
                        "title": button["title"][:20],  # Máximo 20 caracteres
                    },
                }
            )

        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {"buttons": interactive_buttons},
            },
        }

        if not self.enabled:
            logger.info(f"[DEMO] WhatsApp interactive message to {to}: {body_text}")
            return {
                "success": True,
                "message_id": f"demo_interactive_{datetime.now().timestamp()}",
                "to": to,
                "message": body_text,
                "buttons": buttons,
                "sent_at": datetime.now().isoformat(),
            }

        result = self._make_request("POST", "messages", data)
        return {
            "success": True,
            "message_id": result.get("messages", [{}])[0].get("id"),
            "to": to,
            "message": body_text,
            "buttons": buttons,
            "sent_at": datetime.now().isoformat(),
        }

    def get_phone_info(self, phone_number: str) -> Dict:
        """Obtener información de un número de teléfono"""
        if not self.enabled:
            return {
                "valid": True,
                "formatted": phone_number,
                "country_code": "+1",
                "platform": "whatsapp",
            }

        # En modo real, aquí verificarías el número con la API
        return {"valid": True, "formatted": phone_number, "platform": "whatsapp"}

def process_webhook_message(self, webhook_data: Dict) -> Dict:
     """Procesar mensaje recibido via webhook"""
     try:
        entries = webhook_data.get("entry", [])
        if not entries:
            logger.warning("No entries found in webhook data")
            return None
        
        entry = entries[0]
        changes = entry.get("changes", [])
        if not changes:
            logger.warning("No changes found in webhook entry")
            return None
        
        value = changes[0].get("value", {})

         if "messages" in value:
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])
            
            if not messages or not contacts:
                logger.warning("Missing messages or contacts in webhook value")
                return None
            
            message = messages[0]
            contact = contacts[0]

                return {
                    "message_id": message.get("id"),
                    "from": message.get("from"),
                    "contact_name": contact.get("profile", {}).get("name", "Unknown"),
                    "message_type": message.get("type"),
                    "text": message.get("text", {}).get("body")
                    if message.get("type") == "text"
                    else None,
                    "timestamp": datetime.fromtimestamp(
                        int(message.get("timestamp", 0))
                    ).isoformat(),
                    "platform": "whatsapp",
                }

            return None

        except Exception as e:
            logger.error(f"Error processing WhatsApp webhook: {e}")
            return None

    def health_check(self) -> Dict:
        """Verificar estado de la conexión"""
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "message": "WhatsApp API not configured",
                    "demo_mode": True,
                }

            # Verificar credenciales con una consulta simple
            url = f"{self.base_url}/{self.phone_number_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            return {
                "status": "healthy",
                "phone_number_id": self.phone_number_id,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


def get_whatsapp_client() -> WhatsAppClient:
    """Obtener instancia del cliente de WhatsApp"""
    return WhatsAppClient()
