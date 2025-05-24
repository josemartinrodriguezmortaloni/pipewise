import asyncio
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from dotenv import load_dotenv

# IMPORTACIONES ACTUALIZADAS - Con MCP
from app.supabase.supabase_client import (
    SupabaseCRMClient,
    LeadCreate,
    LeadUpdate,
    ConversationCreate,
    MessageCreate,
)

# Importar agentes actualizados con MCP
from app.agents.lead_qualifier import LeadAgent
from app.agents.meeting_scheduler import MeetingSchedulerAgent
from app.agents.outbound_contact import OutboundAgent

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LeadProcessor:
    """
    Procesador principal de leads con agentes que usan MCP automático
    """

    def __init__(self):
        # Inicializar cliente de Supabase
        self.db_client = SupabaseCRMClient()

        # Inicializar agentes con MCP
        self.lead_qualifier = LeadAgent()
        self.outbound_agent = OutboundAgent()
        self.meeting_scheduler = MeetingSchedulerAgent()

        logger.info("LeadProcessor initialized with MCP agents")

    async def process_lead_workflow(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flujo completo del procesamiento de leads - AHORA CON MCP AUTOMÁTICO

        Los agentes ahora manejan automáticamente:
        - Consultas a la base de datos vía MCP Supabase
        - Actualizaciones de estado
        - Creación de conversaciones y mensajes
        - Integración con Calendly vía MCP
        """
        try:
            logger.info(
                f"🚀 Iniciando workflow automatizado para lead: {lead_data.get('email')}"
            )

            # PASO 1: ¿Lead existe? (ahora automático via MCP)
            existing_lead = await self._check_lead_exists(lead_data)

            if existing_lead:
                # PASO 2a: get_lead
                logger.info(f"✅ Lead existente encontrado: {existing_lead.id}")
                current_lead = existing_lead
            else:
                # PASO 2b: insert_lead
                logger.info("📝 Creando nuevo lead...")
                current_lead = await self._create_new_lead(lead_data)

            # PASO 3: LeadProcessor (ya estamos aquí)
            logger.info(f"🔍 Procesando lead con agentes MCP: {current_lead.id}")

            # PASO 4: lead_qualifier - AHORA CON MCP AUTOMÁTICO
            logger.info("🎯 Ejecutando calificación automática con MCP...")
            qualification_result = await self._qualify_lead_automated(current_lead)

            if not qualification_result["qualified"]:
                # PASO 5a: update_lead: qualified=False (FIN) - YA MANEJADO POR MCP
                logger.info("❌ Lead no calificado por el agente automático")
                return {
                    "status": "completed",
                    "lead_id": str(current_lead.id),
                    "qualified": False,
                    "reason": qualification_result.get("reason"),
                    "workflow_completed": True,
                }

            # PASO 5b: Lead calificado - AGENTE YA ACTUALIZÓ VIA MCP
            logger.info("✅ Lead calificado automáticamente, continuando workflow...")

            # PASO 6-9: outbound_contact - AHORA MANEJA TODO AUTOMÁTICAMENTE VIA MCP
            logger.info("📞 Ejecutando contacto outbound automatizado...")
            outbound_result = await self._execute_outbound_automated(current_lead)

            # PASO 10-11: meeting_scheduler - AHORA MANEJA TODO VIA MCP + CALENDLY
            logger.info("📅 Ejecutando agendamiento automatizado...")
            meeting_result = await self._schedule_meeting_automated(current_lead)

            # PASO 12: Fin OK - TODO AUTOMATIZADO VIA MCP
            logger.info("🏁 Workflow completado automáticamente")

            return {
                "status": "completed",
                "lead_id": str(current_lead.id),
                "qualified": True,
                "contacted": True,
                "meeting_scheduled": True,
                "meeting_url": meeting_result.get("meeting_url"),
                "outbound_message": outbound_result.get("message"),
                "event_type": meeting_result.get("event_type"),
                "workflow_completed": True,
            }

        except Exception as e:
            logger.error(f"❌ Error en workflow automatizado: {str(e)}")
            return {"status": "error", "error": str(e), "workflow_completed": False}

    async def _check_lead_exists(self, lead_data: Dict[str, Any]) -> Optional[Any]:
        """Verificar si el lead ya existe en la base de datos"""
        email = lead_data.get("email")
        if not email:
            return None

        return await self.db_client.async_get_lead_by_email(email)

    async def _create_new_lead(self, lead_data: Dict[str, Any]) -> Any:
        """Crear un nuevo lead en la base de datos"""
        lead_create = LeadCreate(
            name=lead_data.get("name", ""),
            email=lead_data.get("email", ""),
            company=lead_data.get("company", ""),
            phone=lead_data.get("phone"),
            message=lead_data.get("message"),
            source=lead_data.get("source", "api"),
            utm_params=lead_data.get("utm_params", {}),
            metadata=lead_data.get("metadata", {}),
        )

        return await self.db_client.async_create_lead(lead_create)

    async def _qualify_lead_automated(self, lead: Any) -> Dict[str, Any]:
        """
        NUEVO: Calificación automatizada con MCP
        El agente maneja automáticamente vía MCP:
        - Buscar leads duplicados
        - Actualizar estado de calificación
        - Registrar metadata
        """
        try:
            # Preparar datos para el agente
            lead_input = {
                "id": str(lead.id),
                "name": lead.name,
                "email": lead.email,
                "company": lead.company,
                "phone": lead.phone,
                "message": lead.message,
                "source": lead.source,
                "metadata": lead.metadata or {},
            }

            # El agente maneja TODO automáticamente via MCP
            qualification_result = await self.lead_qualifier.run(lead_input)

            logger.info(f"Resultado de calificación automática: {qualification_result}")
            return qualification_result

        except Exception as e:
            logger.error(f"Error en calificación automatizada: {e}")
            return {"qualified": False, "reason": f"Error en calificación: {str(e)}"}

    async def _execute_outbound_automated(self, lead: Any) -> Dict[str, Any]:
        """
        NUEVO: Contacto outbound automatizado con MCP
        El agente maneja automáticamente vía MCP:
        - Obtener info del lead
        - Buscar/crear conversación
        - Crear mensaje personalizado
        - Marcar como contactado
        """
        try:
            # El agente necesita mínima información
            contact_input = {
                "lead": {
                    "id": str(lead.id),
                    "name": lead.name,
                    "email": lead.email,
                    "company": lead.company,
                    "phone": lead.phone,
                    "message": lead.message,
                },
            }

            # El agente maneja TODO automáticamente via MCP
            outbound_result = await self.outbound_agent.run(contact_input)

            logger.info(f"Resultado de contacto automatizado: {outbound_result}")
            return outbound_result

        except Exception as e:
            logger.error(f"Error en contacto automatizado: {e}")
            return {
                "success": False,
                "error": str(e),
                "contact_method": "failed",
                "message": f"Error en contacto automatizado: {str(e)}",
            }

    async def _schedule_meeting_automated(self, lead: Any) -> Dict[str, Any]:
        """
        NUEVO: Agendamiento automatizado con MCP Supabase + MCP Calendly
        El agente maneja automáticamente vía MCP:
        - Obtener lead y conversaciones
        - Crear/actualizar conversación
        - Integrar con Calendly para crear link único
        - Marcar reunión como agendada
        - Actualizar estado de conversación
        """
        try:
            # Preparar datos para el agente
            meeting_input = {
                "lead": {
                    "id": str(lead.id),
                    "name": lead.name,
                    "email": lead.email,
                    "company": lead.company,
                    "profile": lead.metadata or {},
                    "qualified": lead.qualified,
                },
            }

            # El agente maneja TODO automáticamente via MCP
            meeting_result = await self.meeting_scheduler.run(meeting_input)

            logger.info(f"Resultado de agendamiento automatizado: {meeting_result}")
            return meeting_result

        except Exception as e:
            logger.error(f"Error en agendamiento automatizado: {e}")
            return {
                "success": False,
                "error": str(e),
                "meeting_url": "https://calendly.com/contact-support",
            }


# ===================== CLASE PRINCIPAL DE AGENTES - ACTUALIZADA PARA MCP =====================


class Agents:
    """
    Clase principal que orquesta todos los agentes del sistema
    AHORA CON MCP AUTOMÁTICO
    """

    def __init__(self) -> None:
        self.lead_processor = LeadProcessor()
        logger.info("Agents system initialized with automated MCP")

    async def run_workflow(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecutar el workflow completo para un lead
        AHORA COMPLETAMENTE AUTOMATIZADO VIA MCP

        Args:
            lead_data: Datos del lead (desde POST /leads)

        Returns:
            Resultado del procesamiento automatizado
        """
        return await self.lead_processor.process_lead_workflow(lead_data)

    # Método síncrono para compatibilidad con código existente
    def run_workflow_sync(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Versión síncrona del workflow automatizado"""
        return asyncio.run(self.run_workflow(lead_data))

    async def get_lead_status(self, lead_id: str) -> Dict[str, Any]:
        """Obtener estado actual de un lead"""
        try:
            lead = await self.lead_processor.db_client.async_get_lead(lead_id)
            if not lead:
                return {"error": "Lead not found"}

            conversations = (
                await self.lead_processor.db_client.async_list_conversations(
                    lead_id=lead.id
                )
            )

            return {
                "lead_id": str(lead.id),
                "status": lead.status,
                "qualified": lead.qualified,
                "contacted": lead.contacted,
                "meeting_scheduled": lead.meeting_scheduled,
                "conversations": len(conversations),
                "metadata": lead.metadata,
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_system_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del sistema"""
        return await self.lead_processor.db_client.async_health_check()


# ===================== EJEMPLO DE USO AUTOMATIZADO CON MCP =====================


async def example_mcp_workflow():
    """Ejemplo de cómo funciona el nuevo workflow automatizado con MCP"""

    # Inicializar sistema de agentes automatizado
    agents = Agents()

    # Datos de ejemplo de un lead (como vendría de POST /leads)
    lead_data = {
        "name": "Carlos Mendoza",
        "email": "carlos@techstartup.com",
        "company": "Tech Startup Inc",
        "phone": "+1234567890",
        "message": "Necesitamos automatizar nuestro proceso de ventas para escalarlo. Tenemos un equipo de 25 personas",
        "source": "website_form",
        "utm_params": {"campaign": "automation_landing", "medium": "organic"},
        "metadata": {
            "company_size": "25-50",
            "industry": "technology",
            "interest_level": "high",
        },
    }

    # Ejecutar workflow COMPLETAMENTE AUTOMATIZADO CON MCP
    print("🚀 Iniciando workflow CRM completamente automatizado con MCP...")
    result = await agents.run_workflow(lead_data)

    print(f"✅ Resultado automatizado: {result}")

    # Obtener estadísticas
    stats = await agents.get_system_stats()
    print(f"📊 Estadísticas del sistema: {stats}")


# ===================== CONFIGURACIÓN MCP REQUERIDA =====================

"""
Variables de entorno necesarias:

1. Supabase:
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

2. OpenAI:
OPENAI_API_KEY=sk-...

3. Calendly (opcional, para MCP):
CALENDLY_ACCESS_TOKEN=eyJraW...

Servidores MCP requeridos:
- app/agents/tools/supabase_mcp.py (todas las operaciones de BD)
- app/agents/tools/calendly.py (integración con Calendly)

Instalación de dependencias:
pip install openai supabase pydantic python-dotenv mcp
"""

if __name__ == "__main__":
    # Ejecutar ejemplo
    print("Ejecutando workflow CRM automatizado con MCP...")
    asyncio.run(example_mcp_workflow())
