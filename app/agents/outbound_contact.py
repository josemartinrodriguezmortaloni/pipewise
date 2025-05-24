import os
import json
import logging
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.messsage_schema import MessageCreate

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
        """Definir herramientas de Supabase para el agente - CORREGIDO"""
        return [
            {
                "type": "function",
                "name": "get_lead_by_id",
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
                "name": "mark_lead_as_contacted",
                "description": "Marcar un lead como contactado",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {"type": "string", "description": "ID del lead"},
                        "contact_method": {
                            "type": "string",
                            "description": "Método de contacto utilizado",
                            "default": "outbound_automated",
                        },
                    },
                    "required": ["lead_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "create_contact_message",
                "description": "Crear registro del mensaje de contacto enviado",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {"type": "string", "description": "ID del lead"},
                        "message_content": {
                            "type": "string",
                            "description": "Contenido del mensaje enviado",
                        },
                        "contact_method": {
                            "type": "string",
                            "description": "Método de contacto",
                        },
                    },
                    "required": ["lead_id", "message_content"],
                    "additionalProperties": False,
                },
            },
        ]

    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Ejecutar función de Supabase - VERSIÓN CORREGIDA CON SERIALIZACIÓN UUID"""
        try:
            if function_name == "get_lead_by_id":
                result = self.db_client.get_lead(arguments["lead_id"])
                # CORREGIDO: Serializar UUID correctamente
                return json.dumps(serialize_for_json(result) if result else None)

            elif function_name == "mark_lead_as_contacted":
                lead_id = arguments["lead_id"]
                contact_method = arguments.get("contact_method", "outbound_automated")

                result = self.db_client.mark_lead_as_contacted(lead_id, contact_method)
                # CORREGIDO: Serializar UUID correctamente
                return json.dumps(serialize_for_json(result))

            elif function_name == "create_contact_message":
                lead_id = arguments["lead_id"]
                message_content = arguments["message_content"]
                contact_method = arguments.get("contact_method", "outbound_automated")

                # Por ahora, solo actualizar metadata del lead con el mensaje
                from app.schemas.lead_schema import LeadUpdate

                metadata = {
                    "last_message": message_content,
                    "last_contact_method": contact_method,
                    "message_sent_at": self.db_client._get_current_timestamp(),
                }

                updates = LeadUpdate(metadata=metadata)
                result = self.db_client.update_lead(lead_id, updates)
                # CORREGIDO: Serializar UUID correctamente
                return json.dumps(
                    {
                        "message_saved": True,
                        "lead_updated": serialize_for_json(result) if result else None,
                    }
                )

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
                    "content": f"Procesa este contacto outbound y MARCA el lead como contactado: {json.dumps(input_data)}",
                },
            ]

            # Llamada inicial al modelo
            response = self.client.responses.create(
                model=self.model,
                input=input_messages,
                tools=self._get_supabase_tools(),
                tool_choice="auto",
                parallel_tool_calls=True,
            )

            # Procesar function calls iterativamente
            max_iterations = 5
            iteration = 0
            contact_result = {
                "success": False,
                "message": "No contact performed",
                "contact_method": "automated",
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

                    # Si fue marcar como contactado, capturar resultado
                    if tool_call.name == "mark_lead_as_contacted":
                        try:
                            result_data = json.loads(result)
                            if "contacted" in result_data and result_data["contacted"]:
                                contact_result["success"] = True
                                contact_result["message"] = (
                                    "Lead marked as contacted successfully"
                                )
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
                    tools=self._get_supabase_tools(),
                    tool_choice="auto",
                    parallel_tool_calls=True,
                )

                iteration += 1

            # Extraer respuesta final
            output_text = response.output_text

            try:
                result = json.loads(output_text)
                # Asegurar que tenemos campos requeridos
                if "message" not in result:
                    result["message"] = "Contacto automatizado realizado"
                if "success" not in result:
                    result["success"] = contact_result["success"]
                if "contact_method" not in result:
                    result["contact_method"] = "outbound_automated"
                return result
            except json.JSONDecodeError:
                return {
                    "message": output_text
                    if output_text
                    else "Contacto automatizado completado",
                    "success": contact_result["success"],
                    "contact_method": "outbound_automated",
                }

        except Exception as e:
            logger.error(f"Error en OutboundAgent: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error en contacto automatizado",
                "contact_method": "failed",
            }
