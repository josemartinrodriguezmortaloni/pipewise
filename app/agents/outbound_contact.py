import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI

from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.messsage_schema import MessageCreate

load_dotenv()
logger = logging.getLogger(__name__)


def load_prompt_from_file(file_path: str) -> str:
    """Loads content from a specified file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {file_path}")
        return "Eres un agente experto en contactar leads de manera personalizada."
    except Exception as e:
        print(f"Error loading prompt file {file_path}: {e}")
        return "Error loading prompt."


class OutboundAgent:
    def __init__(self):
        self.model = "gpt-4.1"
        self.client = OpenAI()
        self.db_client = SupabaseCRMClient()

        # Cargar instrucciones
        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "outboundPrompt.md"
        )
        self.instructions = load_prompt_from_file(prompt_path)

    def _get_supabase_tools(self) -> List[Dict]:
        """Definir herramientas de Supabase para el agente"""
        return [
            [
                {
                    "type": "function",
                    "name": "get_lead",
                    "description": "Obtener información completa del lead antes de contactar",
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
                    "name": "get_conversation",
                    "description": "Obtener conversación activa del lead",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "conversation_id": {
                                "type": "string",
                                "description": "ID de la conversación",
                            }
                        },
                        "required": ["conversation_id"],
                        "additionalProperties": False,
                    },
                },
                {
                    "type": "function",
                    "name": "create_message",
                    "description": "Registrar mensaje enviado en la conversación",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "conversation_id": {"type": "string"},
                            "sender": {"type": "string"},
                            "content": {"type": "string"},
                            "message_type": {"type": ["string", "null"]},
                            "metadata": {"type": ["object", "null"]},
                        },
                        "required": [
                            "conversation_id",
                            "sender",
                            "content",
                            "message_type",
                            "metadata",
                        ],
                        "additionalProperties": False,
                    },
                },
                {
                    "type": "function",
                    "name": "get_messages",
                    "description": "Obtener historial de mensajes de una conversación",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "conversation_id": {"type": "string"},
                            "limit": {"type": ["integer", "null"]},
                        },
                        "required": ["conversation_id", "limit"],
                        "additionalProperties": False,
                    },
                },
            ]
        ]

    async def _execute_function(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> str:
        """Ejecutar función de Supabase"""
        try:
            if function_name == "get_lead":
                result = await self.db_client.get_lead(arguments["lead_id"])
                return json.dumps(result.model_dump() if result else None)

            elif function_name == "get_conversation":
                result = await self.db_client.get_conversation(
                    arguments["conversation_id"]
                )
                return json.dumps(result.model_dump() if result else None)

            elif function_name == "create_message":
                # Filtrar valores None
                msg_data_dict = {k: v for k, v in arguments.items() if v is not None}
                msg_data = MessageCreate(**msg_data_dict)
                result = await self.db_client.create_message(msg_data)
                return json.dumps(result.model_dump())

            elif function_name == "get_messages":
                filter_args = {k: v for k, v in arguments.items() if v is not None}
                result = await self.db_client.get_messages(**filter_args)
                return json.dumps([msg.model_dump() for msg in result])

            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})

        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}")
            return json.dumps({"error": str(e)})

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar el agente de outbound con function calling"""
        try:
            # Preparar mensajes de entrada
            input_messages = [
                {"role": "system", "content": self.instructions},
                {
                    "role": "user",
                    "content": f"Procesa este contacto outbound: {json.dumps(input_data)}",
                },
            ]

            # Llamada inicial al modelo
            response = self.client.responses.create(
                model=self.model, input=input_messages, tools=self._get_supabase_tools()
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
                    model=self.model,
                    input=input_messages,
                    tools=self._get_supabase_tools(),
                )

                iteration += 1

            # Extraer respuesta final
            output_text = response.output_text

            try:
                result = json.loads(output_text)
                return result
            except json.JSONDecodeError:
                return {
                    "message": output_text,
                    "success": True,
                    "contact_method": "automated",
                }

        except Exception as e:
            logger.error(f"Error en OutboundAgent: {e}")
            return {"success": False, "error": str(e), "message": "Error en contacto"}
