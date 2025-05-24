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
    Procesador principal de leads con agentes corregidos
    """

    def __init__(self):
        # Inicializar cliente de Supabase
        self.db_client = SupabaseCRMClient()

        # Inicializar agentes corregidos
        self.lead_qualifier = LeadAgent()
        self.outbound_agent = OutboundAgent()
        self.meeting_scheduler = MeetingSchedulerAgent()

        logger.info("LeadProcessor initialized with corrected agents")

    async def process_lead_workflow(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flujo completo del procesamiento de leads - CORREGIDO
        """
        try:
            logger.info(
                f"🚀 Iniciando workflow automatizado para lead: {lead_data.get('email')}"
            )

            # PASO 1: ¿Lead existe?
            existing_lead = await self._check_lead_exists(lead_data)

            if existing_lead:
                logger.info(f"✅ Lead existente encontrado: {existing_lead.id}")
                current_lead = existing_lead
            else:
                logger.info("📝 Creando nuevo lead...")
                current_lead = await self._create_new_lead(lead_data)

            logger.info(f"🔍 Procesando lead: {current_lead.id}")

            # PASO 2: Calificación de lead - CORREGIDO
            logger.info("🎯 Ejecutando calificación...")
            qualification_result = await self._qualify_lead_corrected(current_lead)

            if not qualification_result.get("qualified", False):
                logger.info("❌ Lead no calificado")
                return {
                    "status": "completed",
                    "lead_id": str(current_lead.id),
                    "qualified": False,
                    "reason": qualification_result.get(
                        "reason", "No qualification reason"
                    ),
                    "workflow_completed": True,
                }

            logger.info("✅ Lead calificado, continuando workflow...")

            # PASO 3: Contacto outbound - CORREGIDO
            logger.info("📞 Ejecutando contacto outbound...")
            outbound_result = await self._execute_outbound_corrected(current_lead)

            # PASO 4: Agendamiento de reunión - CORREGIDO
            logger.info("📅 Ejecutando agendamiento...")
            meeting_result = await self._schedule_meeting_corrected(current_lead)

            logger.info("🏁 Workflow completado")

            # PASO 5: Verificar estados finales en base de datos
            final_lead = self.db_client.get_lead(current_lead.id)

            return {
                "status": "completed",
                "lead_id": str(current_lead.id),
                "qualified": final_lead.qualified
                if final_lead
                else qualification_result.get("qualified", False),
                "contacted": final_lead.contacted
                if final_lead
                else outbound_result.get("success", False),
                "meeting_scheduled": final_lead.meeting_scheduled
                if final_lead
                else meeting_result.get("success", False),
                "meeting_url": meeting_result.get("meeting_url"),
                "outbound_message": outbound_result.get("message"),
                "event_type": meeting_result.get("event_type"),
                "workflow_completed": True,
            }

        except Exception as e:
            logger.error(f"❌ Error en workflow: {str(e)}")
            return {"status": "error", "error": str(e), "workflow_completed": False}

    async def _check_lead_exists(self, lead_data: Dict[str, Any]) -> Optional[Any]:
        """Verificar si el lead ya existe en la base de datos"""
        email = lead_data.get("email")
        if not email:
            return None

        # CORREGIDO: Usar método síncrono
        return self.db_client.get_lead_by_email(email)

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

        # CORREGIDO: Usar método síncrono
        return self.db_client.create_lead(lead_create)

    async def _qualify_lead_corrected(self, lead: Any) -> Dict[str, Any]:
        """
        Calificación corregida que actualiza la base de datos
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

            # El agente corregido debe actualizar la base de datos
            qualification_result = await self.lead_qualifier.run(lead_input)

            logger.info(f"Resultado de calificación: {qualification_result}")

            # Verificar que realmente se actualizó en la base de datos
            updated_lead = self.db_client.get_lead(lead.id)
            if updated_lead and updated_lead.qualified != lead.qualified:
                logger.info("✅ Estado de calificación actualizado en BD")
                qualification_result["database_updated"] = True
            else:
                logger.warning("⚠️ Estado de calificación NO actualizado en BD")
                qualification_result["database_updated"] = False

            return qualification_result

        except Exception as e:
            logger.error(f"Error en calificación: {e}")
            return {"qualified": False, "reason": f"Error en calificación: {str(e)}"}

    async def _execute_outbound_corrected(self, lead: Any) -> Dict[str, Any]:
        """
        Contacto outbound corregido que actualiza la base de datos
        """
        try:
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

            # El agente corregido debe marcar como contactado
            outbound_result = await self.outbound_agent.run(contact_input)

            logger.info(f"Resultado de contacto: {outbound_result}")

            # Verificar que realmente se actualizó en la base de datos
            updated_lead = self.db_client.get_lead(lead.id)
            if updated_lead and updated_lead.contacted != lead.contacted:
                logger.info("✅ Estado de contacto actualizado en BD")
                outbound_result["database_updated"] = True
            else:
                logger.warning("⚠️ Estado de contacto NO actualizado en BD")
                outbound_result["database_updated"] = False

            return outbound_result

        except Exception as e:
            logger.error(f"Error en contacto: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Error en contacto: {str(e)}",
            }

    async def _schedule_meeting_corrected(self, lead: Any) -> Dict[str, Any]:
        """
        Agendamiento corregido que actualiza la base de datos
        """
        try:
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

            # El agente corregido debe marcar reunión como agendada
            meeting_result = await self.meeting_scheduler.run(meeting_input)

            logger.info(f"Resultado de agendamiento: {meeting_result}")

            # Verificar que realmente se actualizó en la base de datos
            updated_lead = self.db_client.get_lead(lead.id)
            if (
                updated_lead
                and updated_lead.meeting_scheduled != lead.meeting_scheduled
            ):
                logger.info("✅ Estado de reunión actualizado en BD")
                meeting_result["database_updated"] = True
            else:
                logger.warning("⚠️ Estado de reunión NO actualizado en BD")
                meeting_result["database_updated"] = False

            return meeting_result

        except Exception as e:
            logger.error(f"Error en agendamiento: {e}")
            return {
                "success": False,
                "error": str(e),
                "meeting_url": "https://calendly.com/contact-support",
            }


# ===================== CLASE PRINCIPAL DE AGENTES - ACTUALIZADA =====================


class Agents:
    """
    Clase principal que orquesta todos los agentes del sistema - CORREGIDA
    """

    def __init__(self) -> None:
        self.lead_processor = LeadProcessor()
        logger.info("Agents system initialized with corrected workflow")

    async def run_workflow(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecutar el workflow completo para un lead - CORREGIDO
        """
        return await self.lead_processor.process_lead_workflow(lead_data)

    def run_workflow_sync(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Versión síncrona del workflow"""
        return asyncio.run(self.run_workflow(lead_data))

    async def get_lead_status(self, lead_id: str) -> Dict[str, Any]:
        """Obtener estado actual de un lead"""
        try:
            # CORREGIDO: Usar método síncrono
            lead = self.lead_processor.db_client.get_lead(lead_id)
            if not lead:
                return {"error": "Lead not found"}

            # CORREGIDO: Usar método síncrono
            conversations = self.lead_processor.db_client.list_conversations(
                lead_id=lead.id
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
        # CORREGIDO: Usar método síncrono
        return self.lead_processor.db_client.get_stats()


# ===================== EJEMPLO DE USO CORREGIDO =====================


async def example_corrected_workflow():
    """Ejemplo del workflow corregido"""

    # Inicializar sistema de agentes corregido
    agents = Agents()

    # Datos de ejemplo de un lead
    lead_data = {
        "name": "Carlos Test Mendoza",
        "email": "carlos.test@techstartup.com",
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

    # Ejecutar workflow CORREGIDO
    print("🚀 Iniciando workflow CRM corregido...")
    result = await agents.run_workflow(lead_data)

    print(f"✅ Resultado corregido: {result}")

    # Obtener estadísticas
    stats = await agents.get_system_stats()
    print(f"📊 Estadísticas del sistema: {stats}")


if __name__ == "__main__":
    # Ejecutar ejemplo
    print("Ejecutando workflow CRM corregido...")
    asyncio.run(example_corrected_workflow())
