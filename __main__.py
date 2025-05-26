#!/usr/bin/env python3
"""
Workflow Visualizer - Herramienta para visualizar el comportamiento de los agentes CRM
Permite ver paso a paso qué hacen los agentes, qué herramientas llaman y qué datos procesan.
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import time

# Importaciones del sistema
from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.lead_schema import LeadCreate
from app.agents.agent import Agents

# Para interceptar function calls
from app.agents.lead_qualifier import LeadAgent
from app.agents.outbound_contact import OutboundAgent
from app.agents.meeting_scheduler import MeetingSchedulerAgent

# Cargar variables de entorno
load_dotenv()

# =====================================================
# CONFIGURACIÓN DEL LEAD - MODIFICA ESTOS DATOS
# =====================================================

LEAD_DATA = {
    "name": "María González",
    "email": f"maria.gonzalez.{datetime.now().strftime('%Y%m%d%H%M%S')}@techcorp.com",
    "company": "TechCorp Solutions",
    "phone": "+34 612 345 678",
    "message": """
    Somos una empresa de tecnología con 45 empleados.
    Necesitamos automatizar nuestro proceso de ventas porque estamos creciendo rápidamente.
    Actualmente perdemos muchos leads por falta de seguimiento.
    Buscamos una solución que se integre con nuestras herramientas existentes.
    """,
    "source": "website_form",
    "utm_params": {
        "campaign": "automation_landing",
        "medium": "organic",
        "source": "google",
    },
    "metadata": {
        "company_size": "25-50",
        "industry": "technology",
        "interest_level": "high",
        "current_tools": ["Slack", "Google Workspace", "Hubspot"],
        "budget_range": "5000-10000",
        "timeline": "Q1 2025",
    },
}

# =====================================================
# CONFIGURACIÓN DE VISUALIZACIÓN
# =====================================================

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    handlers=[
        logging.FileHandler(
            f"workflow_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
        logging.StreamHandler(),
    ],
)

# Silenciar logs no relevantes
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class WorkflowVisualizer:
    """Visualizador detallado del workflow de agentes"""

    def __init__(self):
        self.step_count = 0
        self.function_calls = []
        self.agent_results = {}

        # Parche para interceptar function calls
        self._patch_agents()

    def _patch_agents(self):
        """Interceptar las llamadas a funciones de los agentes"""
        # Guardar métodos originales
        self._original_methods = {
            "lead_execute": LeadAgent._execute_function,
            "outbound_execute": OutboundAgent._execute_function,
            "meeting_execute": MeetingSchedulerAgent._execute_function,
        }

        # Crear wrappers
        def create_wrapper(agent_name, original_method):
            def wrapper(
                self_agent, function_name: str, arguments: Dict[str, Any]
            ) -> str:
                # Log antes de ejecutar
                self._log_function_call(agent_name, function_name, arguments)

                # Ejecutar función original
                result = original_method(self_agent, function_name, arguments)

                # Log después de ejecutar
                self._log_function_result(agent_name, function_name, result)

                return result

            return wrapper

        # Aplicar patches
        LeadAgent._execute_function = create_wrapper(
            "LeadQualifier", self._original_methods["lead_execute"]
        )
        OutboundAgent._execute_function = create_wrapper(
            "OutboundAgent", self._original_methods["outbound_execute"]
        )
        MeetingSchedulerAgent._execute_function = create_wrapper(
            "MeetingScheduler", self._original_methods["meeting_execute"]
        )

    def _log_function_call(
        self, agent_name: str, function_name: str, arguments: Dict[str, Any]
    ):
        """Registrar llamada a función"""
        self.print_box(f"🔧 FUNCTION CALL: {agent_name} -> {function_name}", "yellow")
        print(f"📥 Arguments:")
        for key, value in arguments.items():
            print(f"   • {key}: {value}")
        print()

        # Guardar para resumen
        self.function_calls.append(
            {
                "agent": agent_name,
                "function": function_name,
                "arguments": arguments,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _log_function_result(self, agent_name: str, function_name: str, result: str):
        """Registrar resultado de función"""
        try:
            result_data = json.loads(result)
            print(f"📤 Result:")
            self._print_json_pretty(result_data, indent=3)
        except:
            print(f"📤 Result: {result[:200]}...")
        print()

    def print_separator(self, char="=", length=80):
        """Imprimir separador visual"""
        print(char * length)

    def print_box(self, text: str, color: str = "blue"):
        """Imprimir texto en una caja visual"""
        colors = {
            "blue": "\033[94m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "red": "\033[91m",
            "purple": "\033[95m",
            "cyan": "\033[96m",
        }
        reset = "\033[0m"

        self.print_separator()
        print(f"{colors.get(color, '')}{text}{reset}")
        self.print_separator()

    def print_step(self, title: str, description: str = ""):
        """Imprimir un paso del workflow"""
        self.step_count += 1
        print(f"\n🔸 STEP {self.step_count}: {title}")
        if description:
            print(f"   {description}")
        print()

    def _print_json_pretty(self, data: Any, indent: int = 0):
        """Imprimir JSON de forma legible"""
        prefix = " " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    print(f"{prefix}{key}:")
                    self._print_json_pretty(value, indent + 3)
                else:
                    print(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                print(f"{prefix}[{i}]:")
                self._print_json_pretty(item, indent + 3)
        else:
            print(f"{prefix}{data}")

    async def visualize_workflow(self, lead_data: Dict[str, Any]):
        """Ejecutar y visualizar el workflow completo"""

        self.print_box("🚀 CRM WORKFLOW VISUALIZER", "purple")
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"👤 Lead: {lead_data['name']} ({lead_data['email']})")
        print(f"🏢 Company: {lead_data['company']}")
        print()

        # Mostrar datos del lead
        self.print_step("Lead Data Input", "Datos iniciales del lead")
        self._print_json_pretty(lead_data)

        try:
            # Verificar entorno
            self.print_step("Environment Check", "Verificando configuración")
            self._check_environment()

            # Inicializar sistema
            self.print_step("System Initialization", "Inicializando agentes")
            agents = Agents()
            print("✅ Agents system initialized")

            # Mostrar agentes disponibles
            print("\n📋 Available Agents:")
            print("   • LeadQualifier - Califica leads entrantes")
            print("   • OutboundAgent - Contacta leads calificados")
            print("   • MeetingScheduler - Agenda reuniones con leads")

            # Ejecutar workflow
            self.print_box("🔄 STARTING WORKFLOW EXECUTION", "green")

            # Interceptar el workflow para mostrar cada agente
            lead_processor = agents.lead_processor

            # PASO 1: Verificar/Crear Lead
            self.print_step("Lead Processing", "Verificando si el lead existe")
            existing_lead = await lead_processor._check_lead_exists(lead_data)

            if existing_lead:
                print(f"✅ Lead existente encontrado: {existing_lead.id}")
                current_lead = existing_lead
            else:
                print("📝 Creando nuevo lead...")
                current_lead = await lead_processor._create_new_lead(lead_data)
                print(f"✅ Lead creado: {current_lead.id}")

            print(f"\n📊 Lead Status:")
            print(f"   • ID: {current_lead.id}")
            print(f"   • Qualified: {current_lead.qualified}")
            print(f"   • Contacted: {current_lead.contacted}")
            print(f"   • Meeting Scheduled: {current_lead.meeting_scheduled}")

            # PASO 2: Calificación
            self.print_box("🎯 AGENT 1: LEAD QUALIFIER", "cyan")
            print("Este agente analiza si el lead cumple criterios de calificación")
            await asyncio.sleep(1)  # Pausa dramática

            qualification_result = await lead_processor._qualify_lead_corrected(
                current_lead
            )
            self.agent_results["qualification"] = qualification_result

            print(f"\n📊 Qualification Result:")
            print(f"   • Qualified: {qualification_result.get('qualified', False)}")
            print(f"   • Reason: {qualification_result.get('reason', 'N/A')}")

            if not qualification_result.get("qualified", False):
                self.print_box("❌ WORKFLOW STOPPED - Lead Not Qualified", "red")
                return

            # PASO 3: Agendamiento de reunión (REORDENADO: Ahora va antes del contacto outbound)
            self.print_box("📅 AGENT 2: MEETING SCHEDULER", "cyan")
            print("Este agente crea links de Calendly y agenda reuniones")
            await asyncio.sleep(1)

            meeting_result = await lead_processor._schedule_meeting_corrected(
                current_lead
            )
            self.agent_results["meeting"] = meeting_result

            print(f"\n📊 Meeting Result:")
            print(f"   • Success: {meeting_result.get('success', False)}")
            print(f"   • Meeting URL: {meeting_result.get('meeting_url', 'N/A')}")
            print(f"   • Event Type: {meeting_result.get('event_type', 'N/A')}")

            # PASO 4: Contacto Outbound (REORDENADO: Ahora va después del agendamiento)
            self.print_box("📞 AGENT 3: OUTBOUND CONTACT", "cyan")
            print("Este agente genera y envía mensajes personalizados al lead")
            await asyncio.sleep(1)

            outbound_result = await lead_processor._execute_outbound_corrected(
                current_lead
            )
            self.agent_results["outbound"] = outbound_result

            print(f"\n📊 Outbound Result:")
            print(f"   • Success: {outbound_result.get('success', False)}")
            if "message" in outbound_result:
                print(f"   • Message Preview: {outbound_result['message'][:100]}...")

            # Resumen final
            self.print_box("✅ WORKFLOW COMPLETED", "green")
            self._print_final_summary(current_lead)

        except Exception as e:
            self.print_box(f"❌ ERROR: {str(e)}", "red")
            logger.error(f"Workflow error: {e}", exc_info=True)

    def _check_environment(self):
        """Verificar variables de entorno"""
        env_vars = {
            "SUPABASE_URL": "✅" if os.getenv("SUPABASE_URL") else "❌",
            "SUPABASE_ANON_KEY": "✅" if os.getenv("SUPABASE_ANON_KEY") else "❌",
            "OPENAI_API_KEY": "✅" if os.getenv("OPENAI_API_KEY") else "❌",
            "CALENDLY_ACCESS_TOKEN": "✅"
            if os.getenv("CALENDLY_ACCESS_TOKEN")
            else "⚠️ (Optional)",
        }

        for var, status in env_vars.items():
            print(f"   {status} {var}")

    def _print_final_summary(self, lead):
        """Imprimir resumen final del workflow"""
        # Obtener estado final del lead
        db_client = SupabaseCRMClient()
        final_lead = db_client.get_lead(lead.id)

        print(f"\n📊 FINAL LEAD STATUS:")
        print(f"   • ID: {final_lead.id}")
        print(f"   • Status: {final_lead.status}")
        print(f"   • Qualified: {'✅' if final_lead.qualified else '❌'}")
        print(f"   • Contacted: {'✅' if final_lead.contacted else '❌'}")
        print(
            f"   • Meeting Scheduled: {'✅' if final_lead.meeting_scheduled else '❌'}"
        )

        # Mostrar mensaje outbound final si existe
        outbound_message = self.agent_results.get("outbound", {}).get(
            "outbound_message"
        )
        meeting_url = self.agent_results.get("meeting", {}).get("meeting_url")
        if outbound_message:
            self.print_box("📨 MENSAJE ENVIADO AL CLIENTE (OUTBOUND)", "green")
            print(outbound_message.strip())
            if meeting_url and meeting_url not in outbound_message:
                print(f"\nAgenda tu reunión aquí: {meeting_url}")
            print()

        print(f"\n🔧 FUNCTION CALLS SUMMARY:")
        print(f"   • Total function calls: {len(self.function_calls)}")

        # Agrupar por agente
        agent_calls = {}
        for call in self.function_calls:
            agent = call["agent"]
            if agent not in agent_calls:
                agent_calls[agent] = []
            agent_calls[agent].append(call["function"])

        for agent, functions in agent_calls.items():
            print(f"\n   {agent}:")
            for func in functions:
                print(f"      • {func}")

        # Guardar resumen detallado
        summary_file = (
            f"workflow_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(summary_file, "w") as f:
            json.dump(
                {
                    "lead_data": LEAD_DATA,
                    "final_status": {
                        "id": str(final_lead.id),
                        "status": final_lead.status,
                        "qualified": final_lead.qualified,
                        "contacted": final_lead.contacted,
                        "meeting_scheduled": final_lead.meeting_scheduled,
                    },
                    "function_calls": self.function_calls,
                    "agent_results": self.agent_results,
                },
                f,
                indent=2,
                default=str,
            )

        print(f"\n💾 Detailed summary saved to: {summary_file}")


async def main():
    """Función principal"""
    visualizer = WorkflowVisualizer()
    await visualizer.visualize_workflow(LEAD_DATA)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("CRM WORKFLOW VISUALIZER")
    print("=" * 80)
    print(
        "\n📌 Para modificar los datos del lead, edita LEAD_DATA al inicio del archivo"
    )
    print("📌 El workflow mostrará paso a paso qué hace cada agente\n")

    input("Presiona ENTER para comenzar...")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Workflow interrumpido por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
        import traceback

        traceback.print_exc()
