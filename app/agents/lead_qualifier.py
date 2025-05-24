import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI

from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.lead_schema import LeadUpdate

load_dotenv()
logger = logging.getLogger(__name__)


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
                "name": "get_lead",
                "description": "Obtener un lead por ID o email para verificar si ya existe",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {
                            "type": ["string", "null"],
                            "description": "ID del lead a buscar",
                        },
                        "email": {
                            "type": ["string", "null"],
                            "description": "Email del lead a buscar",
                        },
                    },
                    "required": ["lead_id", "email"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "update_lead",
                "description": "Actualizar la información de un lead, incluyendo su estado de calificación",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lead_id": {
                            "type": "string",
                            "description": "ID del lead a actualizar",
                        },
                        "updates": {
                            "type": "object",
                            "properties": {
                                "qualified": {"type": ["boolean", "null"]},
                                "status": {"type": ["string", "null"]},
                                "metadata": {"type": ["object", "null"]},
                            },
                            "required": ["qualified", "status", "metadata"],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["lead_id", "updates"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "list_leads",
                "description": "Buscar leads existentes con filtros",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email": {"type": ["string", "null"]},
                        "status": {"type": ["string", "null"]},
                        "qualified": {"type": ["boolean", "null"]},
                        "limit": {"type": ["integer", "null"]},
                    },
                    "required": ["email", "status", "qualified", "limit"],
                    "additionalProperties": False,
                },
            },
        ]

    async def _execute_function(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> str:
        """Ejecutar función de Supabase"""
        try:
            if function_name == "get_lead":
                if arguments.get("email"):
                    result = await self.db_client.get_lead_by_email(arguments["email"])
                elif arguments.get("lead_id"):
                    result = await self.db_client.get_lead(arguments["lead_id"])
                else:
                    return json.dumps({"error": "Need either email or lead_id"})
                return json.dumps(result.model_dump() if result else None)

            elif function_name == "update_lead":
                updates = LeadUpdate(
                    **{k: v for k, v in arguments["updates"].items() if v is not None}
                )
                result = await self.db_client.update_lead(arguments["lead_id"], updates)
                return json.dumps(result.model_dump())

            elif function_name == "list_leads":
                # Filtrar argumentos None
                filter_args = {k: v for k, v in arguments.items() if v is not None}
                result = await self.db_client.list_leads(**filter_args)
                return json.dumps([lead.model_dump() for lead in result])

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
                    "content": f"Califica este lead: {json.dumps(input_data)}",
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
                    # No hay más function calls, terminamos
                    break

                # Ejecutar todas las function calls
                for tool_call in function_calls:
                    args = json.loads(tool_call.arguments)
                    result = await self._execute_function(tool_call.name, args)

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

            # Si no es JSON válido, extraer qualified del texto
            qualified = (
                'qualified": true' in output_text.lower()
                or '"qualified": true' in output_text
            )
            return {"qualified": qualified}

        except Exception as e:
            logger.error(f"Error en LeadAgent: {e}")
            return {"qualified": False, "error": str(e)}
