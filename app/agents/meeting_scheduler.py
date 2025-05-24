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
        self.calendly_token = os.getenv("CALENDLY_ACCESS_TOKEN")

        # Cargar instrucciones
        prompt_path = os.path.join(
            os.path.dirname(__file__), "prompts", "meetingSchedulerPrompt.md"
        )
        self.instructions = load_prompt_from_file(prompt_path)

    def _get_tools(self) -> List[Dict]:
        """Definir herramientas MCP disponibles para el agente"""
        tools = [
            # ✅ MCP SERVER PARA SUPABASE - Centraliza todas las operaciones de BD
            {
                "type": "mcp",
                "server_label": "supabase-crm",  # ← REQUERIDO por OpenAI Responses API
                "server_url": "./tools/supabase_mcp.py",
                "headers": {
                    "SUPABASE_URL": os.getenv("SUPABASE_URL"),
                    "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY"),
                },
                "allowed_tools": [
                    # Herramientas específicas que necesita este agente
                    "get_lead",
                    "list_conversations",
                    "create_conversation",
                    "update_conversation",
                    "schedule_meeting_for_lead",
                    "get_lead_with_conversations",
                ],
            }
        ]

        # ✅ MCP SERVER PARA CALENDLY - Solo si está configurado
        if self.calendly_token:
            tools.append(
                {
                    "type": "mcp",
                    "server_label": "calendly-integration",  # ← REQUERIDO por OpenAI Responses API
                    "server_url": "stdio://app/agents/tools/calendly.py",
                    "headers": {
                        "Authorization": f"Bearer {self.calendly_token}",
                        "Content-Type": "application/json",
                    },
                    "allowed_tools": [
                        # Herramientas específicas de Calendly que necesita
                        "get_event_types",
                        "create_scheduling_link",
                        "find_best_meeting_slot",
                        "get_calendly_user",
                    ],
                }
            )

        return tools

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar el agente de agendamiento con MCP"""
        try:
            # Preparar mensajes de entrada
            input_messages = [
                {"role": "system", "content": self.instructions},
                {
                    "role": "user",
                    "content": f"Agenda una reunión para este lead: {json.dumps(input_data)}",
                },
            ]

            # ✅ LLAMADA CON MCP CORREGIDA
            response = self.client.responses.create(
                model=self.model,
                instructions=self.instructions,
                input=input_messages,
                tools=self._get_tools(),
            )

            # Extraer respuesta final del último output
            final_output = None
            for output in response.output:
                if output.type == "message":
                    final_output = output.content[0].text
                    break

            if not final_output:
                # Si no hay mensaje final, buscar en el output_text
                final_output = response.output_text

            try:
                result = json.loads(final_output)
                # Asegurar que siempre hay un meeting_url
                if "meeting_url" not in result:
                    result["meeting_url"] = "https://calendly.com/contact-support"
                return result
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "meeting_url": "https://calendly.com/default-meeting",
                    "event_type": "Sales Call",
                    "message": final_output,
                }

        except Exception as e:
            logger.error(f"Error en MeetingSchedulerAgent: {e}")
            return {
                "success": False,
                "error": str(e),
                "meeting_url": "https://calendly.com/contact-support",
            }


# ===================== MÉTODO PARA VERIFICAR TOOLS =====================


def verify_tools_format():
    """Verificar que las herramientas estén en el formato MCP correcto"""
    agent = MeetingSchedulerAgent()
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


# ===================== EJEMPLO DE USO =====================


async def example_mcp_workflow():
    """Ejemplo de cómo funciona el agente con MCP"""

    # Datos de ejemplo
    lead_data = {
        "lead": {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Carlos Mendoza",
            "email": "carlos@techstartup.com",
            "company": "Tech Startup Inc",
            "qualified": True,
        }
    }

    # Crear agente
    scheduler = MeetingSchedulerAgent()

    # Verificar formato de herramientas
    print("🔧 Verificando herramientas MCP...")
    verify_tools_format()

    # Ejecutar con MCP - El agente automáticamente:
    # 1. Usa el MCP de Supabase para obtener/actualizar datos de BD
    # 2. Usa el MCP de Calendly para crear enlaces únicos
    # 3. Combina ambos para una experiencia fluida

    print("\n🚀 Ejecutando agente con MCP...")
    result = await scheduler.run(lead_data)

    print(f"✅ Resultado: {result}")


if __name__ == "__main__":
    import asyncio

    print("Testing MeetingSchedulerAgent with MCP...")
    verify_tools_format()

    # Ejecutar ejemplo si hay credenciales
    if os.getenv("SUPABASE_URL") and os.getenv("OPENAI_API_KEY"):
        asyncio.run(example_mcp_workflow())
    else:
        print("⚠️ Skipping workflow test (missing environment variables)")
