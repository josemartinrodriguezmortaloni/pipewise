import os
import json
import logging
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.lead_schema import LeadUpdate

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
        return "Eres un agente experto en calificar leads para un CRM SaaS."
    except Exception as e:
        print(f"Error loading prompt file {file_path}: {e}")
        return "Error loading prompt."


class LeadAgent:
    def __init__(self):
        self.model = "gpt-4.1"
        self.client = OpenAI()
        self.db_client = SupabaseCRMClient()

        # Cargar instrucciones
        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "leadQualifierPrompt.md"
        )
        self.instructions = load_prompt_from_file(prompt_path)

    def _get_supabase_tools(self) -> List[Dict]:
        """Definir herramientas de Supabase para el agente"""
        return [
            {
                "type": "function",
                "name": "get_lead_by_email",
                "description": "Buscar un lead específico por email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email del lead a buscar",
                        },
                    },
                    "required": ["email"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "get_lead_by_id",
                "description": "Buscar un lead específico por ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {
                            "type": "string",
                            "description": "ID del lead a buscar",
                        },
                    },
                    "required": ["lead_id"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "update_lead_qualification",
                "description": "Actualizar el estado de calificación de un lead",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {
                            "type": "string",
                            "description": "ID del lead a actualizar",
                        },
                        "qualified": {
                            "type": "boolean",
                            "description": "Si el lead está calificado o no",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Razón de la calificación",
                        },
                    },
                    "required": ["lead_id", "qualified"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "mark_lead_as_qualified",
                "description": "Marcar directamente un lead como calificado",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {
                            "type": "string",
                            "description": "ID del lead a marcar como calificado",
                        },
                    },
                    "required": ["lead_id"],
                    "additionalProperties": False,
                },
            },
        ]

    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Ejecutar función de Supabase - VERSIÓN CORREGIDA CON SERIALIZACIÓN UUID"""
        try:
            if function_name == "get_lead_by_email":
                result = self.db_client.get_lead_by_email(arguments["email"])
                # CORREGIDO: Serializar UUID correctamente
                return json.dumps(serialize_for_json(result) if result else None)

            elif function_name == "get_lead_by_id":
                result = self.db_client.get_lead(arguments["lead_id"])
                # CORREGIDO: Serializar UUID correctamente
                return json.dumps(serialize_for_json(result) if result else None)

            elif function_name == "update_lead_qualification":
                qualified = arguments["qualified"]
                reason = arguments.get("reason", "")

                # Preparar metadata con la razón
                metadata = {
                    "qualification_reason": reason,
                    "qualified_by": "lead_agent",
                }
                status = "qualified" if qualified else "unqualified"

                updates = LeadUpdate(
                    qualified=qualified, status=status, metadata=metadata
                )

                result = self.db_client.update_lead(arguments["lead_id"], updates)
                # CORREGIDO: Serializar UUID correctamente
                return json.dumps(serialize_for_json(result))

            elif function_name == "mark_lead_as_qualified":
                result = self.db_client.mark_lead_as_qualified(arguments["lead_id"])
                # CORREGIDO: Serializar UUID correctamente
                return json.dumps(serialize_for_json(result))

            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})

        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}")
            return json.dumps({"error": str(e)})

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar el agente calificador con function calling"""
        try:
            # Preparar mensajes de entrada
            input_messages = [
                {"role": "system", "content": self.instructions},
                {
                    "role": "user",
                    "content": f"Califica este lead y actualiza su estado en la base de datos: {json.dumps(input_data)}",
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
            qualification_result = {
                "qualified": False,
                "reason": "No qualification performed",
            }

            while iteration < max_iterations:
                function_calls = [
                    item for item in response.output if item.type == "function_call"
                ]

                if not function_calls:
                    break

                # Ejecutar todas las function calls
                for tool_call in function_calls:
                    args = json.loads(tool_call.arguments)
                    result = self._execute_function(tool_call.name, args)

                    # Si fue una actualización de calificación, capturar el resultado
                    if tool_call.name in [
                        "update_lead_qualification",
                        "mark_lead_as_qualified",
                    ]:
                        try:
                            result_data = json.loads(result)
                            if "qualified" in result_data:
                                qualification_result["qualified"] = result_data[
                                    "qualified"
                                ]
                                qualification_result["reason"] = (
                                    "Lead updated successfully"
                                )
                        except:
                            pass

                    # Agregar function call y resultado a los mensajes
                    input_messages.append(tool_call)
                    input_messages.append(
                        {
                            "type": "function_call_output",
                            "call_id": tool_call.call_id,
                            "output": result,
                        }
                    )

                # Nueva llamada al modelo con los resultados
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

            # Intentar parsear como JSON
            try:
                result = json.loads(output_text)
                if "qualified" in result:
                    return result
            except json.JSONDecodeError:
                pass

            # Si no se pudo parsear, usar el resultado de las function calls
            if qualification_result["qualified"]:
                return qualification_result

            # Fallback: extraer qualified del texto
            qualified = (
                'qualified": true' in output_text.lower()
                or '"qualified": true' in output_text
                or "calificado" in output_text.lower()
            )

            return {"qualified": qualified, "reason": "Extracted from agent response"}

        except Exception as e:
            logger.error(f"Error en LeadAgent: {e}")
            return {"qualified": False, "error": str(e)}
