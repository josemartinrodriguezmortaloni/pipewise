import os
import json
import logging
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.conversations_schema import ConversationCreate, ConversationUpdate

load_dotenv()
logger = logging.getLogger(__name__)


def serialize_for_json(obj: Any) -> Any:
    """Serializar objeto para JSON, convirtiendo UUIDs y datetime a strings"""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, "model_dump"):
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
        return (
            "Eres un agente especializado en agendar reuniones con leads calificados."
        )
    except Exception as e:
        print(f"Error loading prompt file {file_path}: {e}")
        return "Error loading prompt."


class MeetingSchedulerAgent:
    def __init__(self):
        self.model = "gpt-4.1"
        self.client = OpenAI()
        self.db_client = SupabaseCRMClient()
        self.calendly_token = os.getenv("CALENDLY_ACCESS_TOKEN")

        # Cargar instrucciones
        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "meetingSchedulerPrompt.md"
        )
        self.instructions = load_prompt_from_file(prompt_path)

    def _get_tools(self) -> List[Dict]:
        """Definir herramientas disponibles para el agente - CORREGIDO"""
        tools = [
            {
                "type": "function",
                "name": "get_lead_by_id",
                "description": "Obtener información completa del lead para personalizar la reunión",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {
                            "type": "string",
                            "description": "ID del lead a obtener",
                        }
                    },
                    "required": ["lead_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "create_conversation_for_lead",
                "description": "Crear nueva conversación para el lead",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {"type": "string", "description": "ID del lead"},
                        "channel": {
                            "type": "string",
                            "description": "Canal de comunicación",
                            "default": "meeting_scheduler",
                        },
                    },
                    "required": ["lead_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "schedule_meeting_for_lead",
                "description": "Marcar lead con reunión agendada y guardar URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {"type": "string", "description": "ID del lead"},
                        "meeting_url": {
                            "type": "string",
                            "description": "URL de la reunión generada",
                        },
                        "meeting_type": {
                            "type": "string",
                            "description": "Tipo de reunión",
                            "default": "Sales Call",
                        },
                    },
                    "required": ["lead_id", "meeting_url"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "generate_meeting_url",
                "description": "Generar URL de reunión personalizada",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {"type": "string", "description": "ID del lead"},
                        "event_type": {
                            "type": "string",
                            "description": "Tipo de evento",
                            "default": "Sales Call",
                        },
                    },
                    "required": ["lead_id"],
                    "additionalProperties": False,
                },
            },
        ]

        return tools

    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Ejecutar función de Supabase o Calendly - VERSIÓN CORREGIDA CON SERIALIZACIÓN UUID"""
        try:
            if function_name == "get_lead_by_id":
                result = self.db_client.get_lead(arguments["lead_id"])
                # CORREGIDO: Serializar UUID correctamente
                return json.dumps(serialize_for_json(result) if result else None)

            elif function_name == "create_conversation_for_lead":
                # CORREGIDO: agent_id debe ser None, no string
                lead_id = arguments["lead_id"]
                channel = arguments.get("channel", "meeting_scheduler")

                conv_data = ConversationCreate(
                    lead_id=lead_id,
                    agent_id=None,  # CORREGIDO: None en lugar de string
                    channel=channel,
                    status="meeting_scheduling",
                )

                result = self.db_client.create_conversation(conv_data)
                # CORREGIDO: Serializar UUID correctamente
                return json.dumps(serialize_for_json(result))

            elif function_name == "schedule_meeting_for_lead":
                lead_id = arguments["lead_id"]
                meeting_url = arguments["meeting_url"]
                meeting_type = arguments.get("meeting_type", "Sales Call")

                result = self.db_client.schedule_meeting_for_lead(
                    lead_id, meeting_url, meeting_type
                )
                # CORREGIDO: Serializar UUID correctamente
                return json.dumps(serialize_for_json(result))

            elif function_name == "generate_meeting_url":
                lead_id = arguments["lead_id"]
                event_type = arguments.get("event_type", "Sales Call")

                # Generar URL única basada en el lead
                import hashlib

                unique_hash = hashlib.md5(
                    f"{lead_id}-{event_type}".encode()
                ).hexdigest()[:8]

                if self.calendly_token:
                    meeting_url = f"https://calendly.com/your-company/{event_type.lower().replace(' ', '-')}-{unique_hash}"
                else:
                    meeting_url = f"https://calendly.com/sales-demo/{unique_hash}"

                return json.dumps(
                    {
                        "meeting_url": meeting_url,
                        "event_type": event_type,
                        "unique_id": unique_hash,
                        "success": True,
                    }
                )

            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})

        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}")
            return json.dumps({"error": str(e)})

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar el agente de agendamiento con function calling"""
        try:
            # Preparar mensajes de entrada
            input_messages = [
                {"role": "system", "content": self.instructions},
                {
                    "role": "user",
                    "content": f"Agenda una reunión para este lead y MARCA como meeting_scheduled: {json.dumps(input_data)}",
                },
            ]

            # Llamada inicial al modelo
            response = self.client.responses.create(
                model=self.model,
                input=input_messages,
                tools=self._get_tools(),
                tool_choice="auto",
                parallel_tool_calls=True,
            )

            # Procesar function calls iterativamente
            max_iterations = 5
            iteration = 0
            meeting_result = {
                "success": False,
                "meeting_url": "https://calendly.com/contact-support",
                "event_type": "Sales Call",
                "lead_status": "meeting_scheduling_error",
                "conversation_id": None,
            }

            while iteration < max_iterations:
                function_calls = [
                    item for item in response.output if item.type == "function_call"
                ]

                if not function_calls:
                    break

                # Ejecutar function calls
                for tool_call in function_calls:
                    args = json.loads(tool_call.arguments)
                    result = self._execute_function(tool_call.name, args)

                    # Capturar resultados importantes
                    if tool_call.name == "schedule_meeting_for_lead":
                        try:
                            result_data = json.loads(result)
                            if (
                                "meeting_scheduled" in result_data
                                and result_data["meeting_scheduled"]
                            ):
                                meeting_result["success"] = True
                                meeting_result["lead_status"] = "meeting_scheduled"
                                if "metadata" in result_data and isinstance(
                                    result_data["metadata"], dict
                                ):
                                    meeting_url = result_data["metadata"].get(
                                        "meeting_url"
                                    )
                                    meeting_type = result_data["metadata"].get(
                                        "meeting_type"
                                    )
                                    if meeting_url:
                                        meeting_result["meeting_url"] = meeting_url
                                    if meeting_type:
                                        meeting_result["event_type"] = meeting_type
                        except:
                            pass

                    elif tool_call.name == "generate_meeting_url":
                        try:
                            result_data = json.loads(result)
                            if "meeting_url" in result_data:
                                meeting_result["meeting_url"] = result_data[
                                    "meeting_url"
                                ]
                                meeting_result["event_type"] = result_data.get(
                                    "event_type", "Sales Call"
                                )
                        except:
                            pass

                    elif tool_call.name == "create_conversation_for_lead":
                        try:
                            result_data = json.loads(result)
                            if "id" in result_data:
                                meeting_result["conversation_id"] = result_data["id"]
                        except:
                            pass

                    input_messages.append(tool_call)
                    input_messages.append(
                        {
                            "type": "function_call_output",
                            "call_id": tool_call.call_id,
                            "output": result,
                        }
                    )

                # Nueva llamada al modelo
                response = self.client.responses.create(
                    model=self.model,
                    input=input_messages,
                    tools=self._get_tools(),
                    tool_choice="auto",
                    parallel_tool_calls=True,
                )

                iteration += 1

            # Extraer respuesta final
            output_text = response.output_text

            try:
                result = json.loads(output_text)
                # Combinar con meeting_result para asegurar campos requeridos
                final_result = {**meeting_result, **result}
                return final_result
            except json.JSONDecodeError:
                # Usar meeting_result como base y agregar texto de respuesta
                meeting_result["message"] = (
                    output_text if output_text else "Meeting scheduling completed"
                )
                return meeting_result

        except Exception as e:
            logger.error(f"Error en MeetingSchedulerAgent: {e}")
            return {
                "success": False,
                "error": str(e),
                "meeting_url": "https://calendly.com/contact-support",
                "event_type": "Error - Agent Failed",
                "lead_status": "meeting_scheduled_error",
                "conversation_id": None,
                "metadata": {
                    "scheduled_at": None,
                    "event_duration": None,
                    "personalization_applied": False,
                    "availability_checked": False,
                    "error": str(e),
                },
            }
