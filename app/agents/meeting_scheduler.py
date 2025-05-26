import os
import json
import logging
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI

from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.conversations_schema import ConversationCreate
from app.schemas.lead_schema import LeadUpdate

# Importar el cliente de Calendly separado
try:
    from app.clients.calendly_client import CalendlyClient
except ImportError:
    # Fallback si no encuentra el archivo
    from app.agents.tools.calendly import CalendlyClient

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

        # Inicializar cliente de Calendly (maneja automáticamente token/fallback)
        self.calendly_client = CalendlyClient()

        # Cargar instrucciones
        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "meetingSchedulerPrompt.md"
        )
        self.instructions = load_prompt_from_file(prompt_path)

    def _get_tools(self) -> List[Dict]:
        """Definir herramientas disponibles para el agente"""
        tools = [
            # Herramientas de Supabase/CRM
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
            # Herramientas de Calendly
            {
                "type": "function",
                "name": "get_calendly_user",
                "description": "Obtener información del usuario actual de Calendly",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "get_calendly_event_types",
                "description": "Obtener tipos de eventos disponibles para agendar en Calendly",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "get_calendly_available_times",
                "description": "Obtener horarios disponibles para un tipo de evento específico",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_type_uri": {
                            "type": "string",
                            "description": "URI del tipo de evento",
                        },
                        "days_ahead": {
                            "type": "integer",
                            "description": "Número de días hacia adelante para consultar (default: 7)",
                            "default": 7,
                        },
                    },
                    "required": ["event_type_uri"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "create_calendly_scheduling_link",
                "description": "Crear un link único de Calendly para que un lead pueda agendar una reunión",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {
                            "type": "string",
                            "description": "ID del lead para quien se crea el link",
                        },
                        "event_type_name": {
                            "type": "string",
                            "description": "Nombre del tipo de evento (ej: 'Sales Call', 'Demo')",
                        },
                        "event_type_uri": {
                            "type": "string",
                            "description": "URI del tipo de evento (opcional si se proporciona event_type_name)",
                        },
                        "max_uses": {
                            "type": "integer",
                            "description": "Máximo número de usos del link (default: 1)",
                            "default": 1,
                        },
                    },
                    "required": ["lead_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "find_best_calendly_meeting_slot",
                "description": "Encontrar el mejor horario disponible para agendar una reunión en Calendly",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_type_name": {
                            "type": "string",
                            "description": "Tipo de reunión (ej: 'Sales Call', 'Demo')",
                        },
                        "preferred_time": {
                            "type": "string",
                            "description": "Hora preferida (ej: 'morning', 'afternoon', 'evening')",
                        },
                        "days_ahead": {
                            "type": "integer",
                            "description": "Buscar en los próximos X días (default: 7)",
                            "default": 7,
                        },
                    },
                    "required": ["event_type_name"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "get_calendly_scheduled_events",
                "description": "Obtener reuniones programadas en Calendly en un rango de fechas",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Días hacia adelante para consultar (default: 30)",
                            "default": 30,
                        },
                        "include_past": {
                            "type": "boolean",
                            "description": "Incluir eventos pasados (default: false)",
                            "default": False,
                        },
                    },
                    "required": [],
                    "additionalProperties": False,
                },
            },
        ]

        return tools

    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Ejecutar función de Supabase o Calendly"""
        logger.info(f"🔧 EXECUTING FUNCTION: {function_name} with args: {arguments}")
        try:
            # Funciones de Supabase/CRM
            if function_name == "get_lead_by_id":
                result = self.db_client.get_lead(arguments["lead_id"])
                return json.dumps(serialize_for_json(result) if result else None)

            elif function_name == "create_conversation_for_lead":
                lead_id = arguments["lead_id"]
                channel = arguments.get("channel", "meeting_scheduler")

                conv_data = ConversationCreate(
                    lead_id=lead_id,
                    agent_id=None,
                    channel=channel,
                    status="meeting_scheduling",
                )

                result = self.db_client.create_conversation(conv_data)
                return json.dumps(serialize_for_json(result))

            elif function_name == "schedule_meeting_for_lead":
                lead_id = arguments["lead_id"]
                meeting_url = arguments["meeting_url"]
                meeting_type = arguments.get("meeting_type", "Sales Call")

                result = self.db_client.schedule_meeting_for_lead(
                    lead_id, meeting_url, meeting_type
                )
                return json.dumps(serialize_for_json(result))

            # Funciones de Calendly usando el cliente separado
            elif function_name == "get_calendly_user":
                result = self.calendly_client.get_current_user()
                user_info = {
                    "name": result["resource"]["name"],
                    "email": result["resource"]["email"],
                    "timezone": result["resource"]["timezone"],
                    "uri": result["resource"]["uri"],
                }
                return json.dumps(user_info)

            elif function_name == "get_calendly_event_types":
                user_data = self.calendly_client.get_current_user()
                user_uri = user_data["resource"]["uri"]

                result = self.calendly_client.get_event_types(user_uri)
                event_types = []

                for event_type in result["collection"]:
                    event_types.append(
                        {
                            "name": event_type["name"],
                            "duration": event_type["duration"],
                            "uri": event_type["uri"],
                            "description": event_type.get("description_plain", ""),
                            "active": event_type["active"],
                        }
                    )

                return json.dumps(event_types)

            elif function_name == "get_calendly_available_times":
                event_type_uri = arguments["event_type_uri"]
                days_ahead = arguments.get("days_ahead", 7)

                start_time = datetime.now().isoformat()
                end_time = (datetime.now() + timedelta(days=days_ahead)).isoformat()

                result = self.calendly_client.get_available_times(
                    event_type_uri, start_time, end_time
                )

                available_slots = []
                for slot in result["collection"]:
                    start_dt = datetime.fromisoformat(
                        slot["start_time"].replace("Z", "+00:00")
                    )
                    available_slots.append(
                        {
                            "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
                            "day_of_week": start_dt.strftime("%A"),
                            "iso_time": slot["start_time"],
                        }
                    )

                return json.dumps(available_slots)

            elif function_name == "create_calendly_scheduling_link":
                lead_id = arguments.get("lead_id", "unknown")
                event_type_name = arguments.get("event_type_name", "Sales Call")
                max_uses = arguments.get("max_uses", 1)

                # Usar el método mejorado del cliente
                result = self.calendly_client.create_personalized_link(
                    lead_id, event_type_name, max_uses
                )

                return json.dumps(
                    {
                        "booking_url": result["booking_url"],
                        "max_event_count": result["max_uses"],
                        "owner_type": "EventType",
                        "event_type": result["event_type"],
                        "fallback": result.get("fallback", False),
                        "success": True,  # Marcar como exitoso para lógica posterior
                        "lead_id": lead_id,  # Incluir lead_id para referencia
                    }
                )

            elif function_name == "find_best_calendly_meeting_slot":
                event_type_name = arguments["event_type_name"]
                preferred_time = arguments.get("preferred_time", "")
                days_ahead = arguments.get("days_ahead", 7)

                # Usar el método mejorado del cliente
                result = self.calendly_client.find_best_meeting_slot(
                    event_type_name, preferred_time, days_ahead
                )

                return json.dumps(result)

            elif function_name == "get_calendly_scheduled_events":
                days_ahead = arguments.get("days_ahead", 30)
                include_past = arguments.get("include_past", False)

                user_data = self.calendly_client.get_current_user()
                user_uri = user_data["resource"]["uri"]

                if include_past:
                    start_time = (datetime.now() - timedelta(days=30)).isoformat()
                else:
                    start_time = datetime.now().isoformat()

                end_time = (datetime.now() + timedelta(days=days_ahead)).isoformat()

                result = self.calendly_client.get_scheduled_events(
                    user_uri, start_time, end_time
                )

                events = []
                for event in result["collection"]:
                    start_dt = datetime.fromisoformat(
                        event["start_time"].replace("Z", "+00:00")
                    )
                    events.append(
                        {
                            "name": event["name"],
                            "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
                            "status": event["status"],
                            "uuid": event["uri"].split("/")[-1],
                            "location": event.get("location", {}).get("type", "N/A"),
                        }
                    )
                logger.info(f"✅ FUNCTION RESULT: {function_name} -> {result[:100]}...")
                return json.dumps(events)

            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})

        except Exception as e:
            logger.error(f"❌ FUNCTION ERROR: {function_name} -> {str(e)}")
            return json.dumps({"error": str(e)})

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar el agente de agendamiento con function calling"""
        try:
            # Preparar mensajes de entrada
            lead_id = input_data.get("lead", {}).get("id", "unknown")
            input_messages = [
                {"role": "system", "content": self.instructions},
                {
                    "role": "user",
                    "content": f"""Agenda una reunión para este lead siguiendo estos pasos OBLIGATORIOS:

1. Obtener información del lead (get_lead_by_id)
2. Crear link de Calendly (create_calendly_scheduling_link) - INCLUYE lead_id: {lead_id}
3. Marcar lead como meeting_scheduled (schedule_meeting_for_lead)

Datos del lead: {json.dumps(input_data)}

IMPORTANTE: Una vez creado el link de Calendly, el lead debe quedar marcado como meeting_scheduled=true en la base de datos.""",
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

                    elif tool_call.name == "create_calendly_scheduling_link":
                        try:
                            result_data = json.loads(result)
                            if "booking_url" in result_data and result_data.get(
                                "success", False
                            ):
                                meeting_result["meeting_url"] = result_data[
                                    "booking_url"
                                ]
                                meeting_result["event_type"] = result_data.get(
                                    "event_type", "Sales Call"
                                )
                                meeting_result["success"] = True
                                meeting_result["lead_status"] = "meeting_scheduled"

                                # Auto-call schedule_meeting_for_lead si tenemos lead_id
                                if (
                                    "lead_id" in result_data
                                    and result_data["lead_id"] != "unknown"
                                ):
                                    logger.info(
                                        f"📅 Auto-scheduling meeting for lead {result_data['lead_id']}"
                                    )
                                    schedule_args = {
                                        "lead_id": result_data["lead_id"],
                                        "meeting_url": result_data["booking_url"],
                                        "meeting_type": result_data.get(
                                            "event_type", "Sales Call"
                                        ),
                                    }
                                    schedule_result = self._execute_function(
                                        "schedule_meeting_for_lead", schedule_args
                                    )
                                    logger.info(
                                        f"📅 Auto-schedule result: {schedule_result}"
                                    )
                                    # ─── NUEVO: Actualizar el lead con el link de la reunión ───
                                    update_data = LeadUpdate(
                                        metadata={
                                            "meeting_url": result_data["booking_url"]
                                        }
                                    )
                                    self.db_client.update_lead(
                                        result_data["lead_id"], update_data
                                    )
                        except Exception as e:
                            logger.error(f"Error processing calendly link result: {e}")

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
