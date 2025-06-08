import asyncio
import os
import json
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.lead_schema import LeadCreate
from app.schemas.contacts_schema import ContactCreate, OutreachMessageCreate
from app.agents.tools.whatsapp import WhatsAppClient
from app.agents.lead_qualifier import LeadAgent
from app.agents.meeting_scheduler import MeetingSchedulerAgent

load_dotenv()
logger = logging.getLogger(__name__)


def serialize_for_json(obj: Any) -> Any:
    """Serializar objeto para JSON, convirtiendo UUIDs y datetime a strings"""
    if hasattr(obj, "model_dump"):
        return serialize_for_json(obj.model_dump())
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    else:
        return obj


def load_prompt_from_file(file_path: str) -> str:
    """Loads content from a specified file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {file_path}")
        return "Eres un agente experto en ventas por WhatsApp para PipeWise CRM."
    except Exception as e:
        print(f"Error loading prompt file {file_path}: {e}")
        return "Error loading prompt."


class WhatsAppAgent:
    """Agente especializado para gestionar conversaciones de WhatsApp"""

    def __init__(self, user_id: str = "demo_user"):
        self.model = "gpt-4o"
        self.client = OpenAI()
        self.db_client = SupabaseCRMClient()
        self.whatsapp_client = WhatsAppClient()
        self.user_id = user_id

        # Cargar prompt especializado
        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "whatsappAgentPrompt.md"
        )
        self.instructions = load_prompt_from_file(prompt_path)

    def _get_tools(self) -> List[Dict]:
        """Definir herramientas disponibles para el agente de WhatsApp"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "send_whatsapp_message",
                    "description": "Enviar mensaje de WhatsApp a un número",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": {
                                "type": "string",
                                "description": "Número de teléfono del destinatario",
                            },
                            "message": {
                                "type": "string",
                                "description": "Contenido del mensaje",
                            },
                            "message_type": {
                                "type": "string",
                                "description": "Tipo de mensaje (text, template, interactive)",
                                "default": "text",
                            },
                        },
                        "required": ["phone_number", "message"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_lead_from_contact",
                    "description": "Crear lead en la base de datos desde información de contacto",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Nombre del lead",
                            },
                            "phone": {
                                "type": "string",
                                "description": "Teléfono del lead",
                            },
                            "company": {
                                "type": "string",
                                "description": "Empresa del lead (opcional)",
                            },
                            "notes": {
                                "type": "string",
                                "description": "Notas sobre la conversación",
                            },
                        },
                        "required": ["name", "phone"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "save_contact_and_message",
                    "description": "Guardar contacto y mensaje en la base de datos",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contact_name": {
                                "type": "string",
                                "description": "Nombre del contacto",
                            },
                            "phone_number": {
                                "type": "string",
                                "description": "Número de teléfono",
                            },
                            "message_content": {
                                "type": "string",
                                "description": "Contenido del mensaje enviado",
                            },
                            "message_type": {
                                "type": "string",
                                "description": "Tipo de mensaje",
                                "default": "text",
                            },
                        },
                        "required": ["contact_name", "phone_number", "message_content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "trigger_lead_workflow",
                    "description": "Activar el workflow de calificación y agendamiento para un lead",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lead_id": {
                                "type": "string",
                                "description": "ID del lead a procesar",
                            }
                        },
                        "required": ["lead_id"],
                    },
                },
            },
        ]

    async def _execute_function(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> str:
        """Ejecutar función del agente de WhatsApp"""
        logger.info(
            f"🔧 WhatsApp Agent executing: {function_name} with args: {arguments}"
        )
        try:
            if function_name == "send_whatsapp_message":
                result = self.whatsapp_client.send_text_message(
                    arguments["phone_number"], arguments["message"]
                )
                return json.dumps(
                    {"success": result.get("success", False), "details": result}
                )

            elif function_name == "create_lead_from_contact":
                lead_data = LeadCreate(
                    name=arguments["name"],
                    phone=arguments["phone"],
                    company=arguments.get("company"),
                    source="whatsapp",
                    notes=arguments.get("notes"),
                    metadata={"contacted_via": "whatsapp", "user_id": self.user_id},
                )
                lead = self.db_client.create_lead(lead_data)
                return json.dumps({"success": True, "lead_id": str(lead.id)})

            elif function_name == "save_contact_and_message":
                contact = self.db_client.get_or_create_contact(
                    name=arguments["contact_name"],
                    phone=arguments["phone_number"],
                    platform="whatsapp",
                    user_id=self.user_id,
                )
                message_data = OutreachMessageCreate(
                    contact_id=contact.id,
                    platform="whatsapp",
                    message_type=arguments.get("message_type", "text"),
                    content=arguments["message_content"],
                )
                message = self.db_client.create_outreach_message(message_data)
                return json.dumps(
                    {
                        "success": True,
                        "contact_id": str(contact.id),
                        "message_id": str(message.id),
                    }
                )

            elif function_name == "trigger_lead_workflow":
                return await self.trigger_lead_workflow(arguments["lead_id"])

            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})
        except Exception as e:
            logger.error(f"❌ Error executing {function_name}: {e}")
            return json.dumps({"error": str(e)})

    async def process_incoming_message(self, webhook_data: Dict) -> Dict:
        """Procesar mensaje entrante desde webhook de WhatsApp"""
        try:
            message_data = self.whatsapp_client.process_webhook_message(webhook_data)
            if not message_data:
                return {"success": False, "error": "Invalid webhook data"}

            phone_number = message_data["from"]
            contact_name = message_data["contact_name"]
            message_text = message_data["text"]

            logger.info(
                f"📱 Processing WhatsApp message from {contact_name} ({phone_number}): {message_text}"
            )

            messages = [
                {"role": "system", "content": self.instructions},
                {
                    "role": "user",
                    "content": f'Mensaje recibido de {contact_name} ({phone_number}): "{message_text}"',
                },
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self._get_tools(),
                tool_choice="auto",
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                await asyncio.gather(
                    *(
                        self._execute_function(
                            tool.function.name, json.loads(tool.function.arguments)
                        )
                        for tool in tool_calls
                    )
                )

            return {
                "success": True,
                "agent_response": response_message.content or "Action taken.",
            }

        except Exception as e:
            logger.error(f"❌ Error processing WhatsApp message: {e}")
            return {"success": False, "error": str(e)}

    async def send_outreach_message(self, target_data: Dict) -> Dict:
        """Enviar mensaje de outreach a un contacto potencial"""
        try:
            phone_number = target_data.get("phone_number")
            name = target_data.get("name", "Cliente")
            if not phone_number:
                return {"success": False, "error": "Phone number required"}

            messages = [
                {"role": "system", "content": self.instructions},
                {
                    "role": "user",
                    "content": f"Crea un mensaje de outreach inicial para WhatsApp dirigido a {name} ({phone_number}). Luego envíalo y guarda el contacto y el mensaje.",
                },
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self._get_tools(),
                tool_choice="auto",
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            if tool_calls:
                await asyncio.gather(
                    *(
                        self._execute_function(
                            tool.function.name, json.loads(tool.function.arguments)
                        )
                        for tool in tool_calls
                    )
                )

            return {
                "success": True,
                "agent_message": response_message.content,
                "platform": "whatsapp",
            }

        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp outreach: {e}")
            return {"success": False, "error": str(e)}

    async def generate_templated_message(
        self, lead_id: str, template_body: str
    ) -> Dict:
        """Generar un mensaje personalizado basado en una plantilla y el contexto del lead"""
        try:
            lead = self.db_client.get_lead(lead_id)
            if not lead:
                return {"success": False, "error": "Lead not found"}

            prompt = f"Basado en la siguiente plantilla: ```{template_body}``` y el contexto del lead: {lead.name}, {lead.company}, genera un mensaje personalizado."

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un asistente de ventas experto en personalización de mensajes de WhatsApp.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=256,
                temperature=0.7,
            )
            generated_message = response.choices[0].message.content.strip()
            self.whatsapp_client.send_text_message(
                phone_number=lead.phone, message=generated_message
            )
            return {"success": True, "generated_content": generated_message}
        except Exception as e:
            logger.error(f"Error generating templated message for lead {lead_id}: {e}")
            return {"success": False, "error": str(e)}

    async def trigger_lead_workflow(self, lead_id: str) -> str:
        """Activar el workflow de calificación y agendamiento para un lead"""
        try:
            lead = self.db_client.get_lead(lead_id)
            if not lead:
                return json.dumps({"success": False, "error": "Lead not found"})

            qualifier = LeadAgent()
            qualification_result = await qualifier.run(
                {"lead": serialize_for_json(lead)}
            )

            if qualification_result.get("qualified"):
                scheduler = MeetingSchedulerAgent()
                meeting_result = await scheduler.run({"lead": serialize_for_json(lead)})
                return json.dumps(
                    {"success": True, "qualified": True, **meeting_result}
                )
            else:
                return json.dumps(
                    {
                        "success": True,
                        "qualified": False,
                        "reason": qualification_result.get("reason"),
                    }
                )
        except Exception as e:
            logger.error(f"❌ Error triggering lead workflow: {e}")
            return json.dumps({"success": False, "error": str(e)})

    async def send_meeting_link(self, contact_id: str, meeting_url: str) -> Dict:
        """Enviar link de reunión al contacto por WhatsApp"""
        try:
            UUID(contact_id)
            contact = self.db_client.get_contact_by_id(contact_id)
            if not contact:
                return {"success": False, "error": "Contact not found"}

            phone_number = contact.platform_id
            name = contact.name
            message = (
                f"¡Hola {name}! Tu reunión ha sido agendada. Únete aquí: {meeting_url}"
            )

            result = self.whatsapp_client.send_text_message(phone_number, message)
            if result.get("success"):
                message_data = OutreachMessageCreate(
                    contact_id=UUID(contact_id),
                    platform="whatsapp",
                    message_type="meeting_link",
                    content=message,
                    template_name="meeting_scheduled",
                )
                self.db_client.create_outreach_message(message_data)
            return {"success": result.get("success", False), "platform": "whatsapp"}
        except ValueError:
            return {"success": False, "error": "Invalid contact ID format"}
        except Exception as e:
            logger.error(f"❌ Error sending meeting link via WhatsApp: {e}")
            return {"success": False, "error": str(e)}


def get_whatsapp_agent(user_id: str = "demo_user") -> WhatsAppAgent:
    """Obtener instancia del agente de WhatsApp"""
    return WhatsAppAgent(user_id=user_id)
