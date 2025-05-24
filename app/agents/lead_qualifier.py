import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI

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

        # Cargar instrucciones
        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "leadQualifierPrompt.md"
        )
        self.instructions = load_prompt_from_file(prompt_path)

    def _get_tools(self) -> List[Dict]:
        """Definir herramientas MCP para el agente de calificación"""
        return [
            {
                "type": "mcp",
                "server_label": "supabase-crm",  # ← REQUERIDO por OpenAI Responses API
                "server_url": "./tools/supabase_mcp.py",
                "headers": {
                    "SUPABASE_URL": os.getenv("SUPABASE_URL"),
                    "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY"),
                },
                "allowed_tools": [
                    # Solo las herramientas que necesita para calificación
                    "get_lead",
                    "get_lead_by_email",
                    "update_lead",
                    "list_leads",
                    "mark_lead_as_qualified",
                ],
            }
        ]

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar el agente calificador con MCP"""
        try:
            # Preparar mensajes de entrada
            input_messages = [
                {"role": "system", "content": self.instructions},
                {
                    "role": "user",
                    "content": f"Califica este lead: {json.dumps(input_data)}",
                },
            ]

            # ✅ LLAMADA CON MCP CORREGIDA
            response = self.client.responses.create(
                model=self.model,
                instructions=self.instructions,
                input=input_messages,
                tools=self._get_tools(),
            )

            # Extraer respuesta final
            final_output = None
            for output in response.output:
                if output.type == "message":
                    final_output = output.content[0].text
                    break

            if not final_output:
                final_output = response.output_text

            # Intentar parsear como JSON
            try:
                result = json.loads(final_output)
                if "qualified" in result:
                    return result
            except json.JSONDecodeError:
                pass

            # Si no es JSON válido, extraer qualified del texto
            qualified = (
                'qualified": true' in final_output.lower()
                or '"qualified": true' in final_output
            )
            return {"qualified": qualified}

        except Exception as e:
            logger.error(f"Error en LeadAgent: {e}")
            return {"qualified": False, "error": str(e)}


# ===================== MÉTODO PARA VERIFICAR TOOLS =====================


def verify_tools_format():
    """Verificar que las herramientas estén en el formato MCP correcto"""
    agent = LeadAgent()
    tools = agent._get_tools()

    print("🔧 Verificando formato de herramientas MCP:")
    for i, tool in enumerate(tools):
        print(f"\nTool {i + 1}:")
        print(f"  Type: {tool.get('type')}")
        print(f"  Server Label: {tool.get('server_label', 'MISSING!')}")
        print(f"  Server URL: {tool.get('server_url')}")
        print(f"  Allowed Tools: {len(tool.get('allowed_tools', []))}")

        # Verificar formato correcto
        if tool.get("type") != "mcp":
            print("  ❌ Type should be 'mcp'")
        elif not tool.get("server_label"):
            print("  ❌ Missing required 'server_label'")
        else:
            print("  ✅ Format OK")


if __name__ == "__main__":
    verify_tools_format()
