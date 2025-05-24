import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI

from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.conversations_schema import ConversationCreate, ConversationUpdate

load_dotenv()
logger = logging.getLogger(__name__)


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
        """Definir herramientas disponibles para el agente"""
        tools = [
            {
                "type": "function",
                "name": "get_lead",
                "description": "Obtener información completa del lead para personalizar la reunión",
                "parameters": {
                    "type": "object",
                    "properties": {"lead_id": {"type": "string"}},
                    "required": ["lead_id"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "list_conversations",
                "description": "Buscar conversaciones existentes del lead",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {"type": ["string", "null"]},
                        "status": {"type": ["string", "null"]},
                    },
                    "required": ["lead_id", "status"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "create_conversation",
                "description": "Crear nueva conversación si no existe una activa",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {"type": "string"},
                        "agent_id": {"type": ["string", "null"]},
                        "channel": {"type": ["string", "null"]},
                        "status": {"type": ["string", "null"]},
                    },
                    "required": ["lead_id", "agent_id", "channel", "status"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "update_conversation",
                "description": "Actualizar estado de conversación después de agendar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "conversation_id": {"type": "string"},
                        "updates": {
                            "type": "object",
                            "properties": {
                                "status": {"type": ["string", "null"]},
                                "summary": {"type": ["string", "null"]},
                            },
                            "required": ["status", "summary"],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["conversation_id", "updates"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "schedule_meeting_for_lead",
                "description": "Marcar lead con reunión agendada y guardar URL de Calendly",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {"type": "string"},
                        "meeting_url": {"type": "string"},
                        "meeting_type": {"type": ["string", "null"]},
                    },
                    "required": ["lead_id", "meeting_url", "meeting_type"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        ]

        # Agregar herramientas de Calendly MCP si está configurado
        if self.calendly_token:
            tools.extend(
                [
                    {
                        "type": "function",
                        "name": "create_calendly_scheduling_link",
                        "description": "Crear link único de Calendly para el lead usando MCP",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "event_type_name": {"type": ["string", "null"]},
                                "max_uses": {"type": ["integer", "null"]},
                            },
                            "required": ["event_type_name", "max_uses"],
                            "additionalProperties": False,
                        },
                        "strict": True,
                    }
                ]
            )

        return tools

    async def _execute_function(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> str:
        """Ejecutar función de Supabase o Calendly"""
        try:
            # Funciones de Supabase
            if function_name == "get_lead":
                result = await self.db_client.get_lead(arguments["lead_id"])
                return json.dumps(result.model_dump() if result else None)

            elif function_name == "list_conversations":
                filter_args = {k: v for k, v in arguments.items() if v is not None}
                result = await self.db_client.list_conversations(**filter_args)
                return json.dumps([conv.model_dump() for conv in result])

            elif function_name == "create_conversation":
                # Filtrar valores None
                conv_data_dict = {k: v for k, v in arguments.items() if v is not None}
                conv_data = ConversationCreate(**conv_data_dict)
                result = await self.db_client.create_conversation(conv_data)
                return json.dumps(result.model_dump())

            elif function_name == "update_conversation":
                updates_dict = {
                    k: v for k, v in arguments["updates"].items() if v is not None
                }
                updates = ConversationUpdate(**updates_dict)
                result = await self.db_client.update_conversation(
                    arguments["conversation_id"], updates
                )
                return json.dumps(result.model_dump())

            elif function_name == "schedule_meeting_for_lead":
                result = await self.db_client.schedule_meeting_for_lead(
                    arguments["lead_id"],
                    arguments["meeting_url"],
                    arguments.get("meeting_type"),
                )
                return json.dumps(result.model_dump())

            # Funciones de Calendly (simuladas - en producción usarías el MCP real)
            elif function_name == "create_calendly_scheduling_link":
                event_type = arguments.get("event_type_name", "Sales Call")
                max_uses = arguments.get("max_uses", 1)

                # Simular creación de link único
                unique_id = f"link-{abs(hash(str(arguments)))}"
                meeting_url = f"https://calendly.com/your-company/{event_type.lower().replace(' ', '-')}-{unique_id}"

                return json.dumps(
                    {
                        "booking_url": meeting_url,
                        "event_type": event_type,
                        "max_uses": max_uses,
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
                    "content": f"Agenda una reunión para este lead: {json.dumps(input_data)}",
                },
            ]

            # Llamada inicial al modelo
            response = self.client.responses.create(
                model=self.model, input=input_messages, tools=self._get_tools()
            )

            # Procesar function calls iterativamente
            max_iterations = 5
            iteration = 0

            while iteration < max_iterations:
                function_calls = [
                    item for item in response.output if item.type == "function_call"
                ]

                if not function_calls:
                    break

                # Ejecutar function calls
                for tool_call in function_calls:
                    args = json.loads(tool_call.arguments)
                    result = await self._execute_function(tool_call.name, args)

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
                    model=self.model, input=input_messages, tools=self._get_tools()
                )

                iteration += 1

            # Extraer respuesta final
            output_text = response.output_text

            try:
                result = json.loads(output_text)
                # Asegurar que siempre hay un meeting_url
                if "meeting_url" not in result:
                    result["meeting_url"] = "https://calendly.com/contact-support"
                return result
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "meeting_url": "https://calendly.com/default-meeting",
                    "event_type": "Sales Call",
                    "message": output_text,
                }

        except Exception as e:
            logger.error(f"Error en MeetingSchedulerAgent: {e}")
            return {
                "success": False,
                "error": str(e),
                "meeting_url": "https://calendly.com/contact-support",
            }
