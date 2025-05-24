import asyncio
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from dotenv import load_dotenv

# Importar cliente de Supabase (asumo que está en el mismo proyecto)
from supabase_crm_client import (
    SupabaseCRMClient,
    LeadCreate,
    LeadUpdate,
    ConversationCreate,
    MessageCreate,
)

# Importar agentes (ajustar las importaciones según tu estructura)
from lead_qualifier import LeadAgent
from meeting_scheduler import MeetingSchedulerAgent
from outbound_contact import OutboundAgent

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LeadProcessor:
    """
    Procesador principal de leads siguiendo el flujo completo del diagrama mermaid
    """

    def __init__(self):
        # Inicializar cliente de Supabase
        self.db_client = SupabaseCRMClient()

        # Inicializar agentes
        self.lead_qualifier = LeadAgent()
        self.outbound_agent = OutboundAgent()
        self.meeting_scheduler = MeetingSchedulerAgent()

        logger.info("LeadProcessor initialized with all agents and database client")

    async def process_lead_workflow(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flujo completo del procesamiento de leads según el diagrama mermaid

        Args:
            lead_data: Datos del lead (puede venir de POST /leads)

        Returns:
            Dict con el resultado del procesamiento
        """
        try:
            logger.info(f"🚀 Iniciando workflow para lead: {lead_data.get('email')}")

            # PASO 1: ¿Lead existe?
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
            logger.info(f"🔍 Procesando lead: {current_lead.id}")

            # PASO 4: lead_qualifier
            logger.info("🎯 Ejecutando calificación de lead...")
            qualification_result = await self._qualify_lead(current_lead)

            if not qualification_result["qualified"]:
                # PASO 5a: update_lead: qualified=False (FIN)
                logger.info("❌ Lead no calificado, finalizando workflow")
                await self._mark_lead_unqualified(
                    current_lead.id, qualification_result.get("reason")
                )
                return {
                    "status": "completed",
                    "lead_id": str(current_lead.id),
                    "qualified": False,
                    "reason": qualification_result.get("reason"),
                    "workflow_completed": True,
                }

            # PASO 5b: Lead calificado, continuar workflow
            logger.info("✅ Lead calificado, continuando workflow...")
            await self._mark_lead_qualified(current_lead.id)

            # PASO 6: insert_conversation
            logger.info("💬 Creando conversación...")
            conversation = await self._create_conversation(current_lead.id)

            # PASO 7: outbound_contact
            logger.info("📞 Ejecutando contacto outbound...")
            outbound_result = await self._execute_outbound_contact(
                current_lead, conversation
            )

            # PASO 8: insert_message
            logger.info("📨 Registrando mensaje de contacto...")
            await self._insert_contact_message(conversation.id, outbound_result)

            # PASO 9: update_lead: contacted=True
            logger.info("✅ Marcando lead como contactado...")
            await self._mark_lead_contacted(
                current_lead.id, outbound_result.get("contact_method")
            )

            # PASO 10: meeting_scheduler + Calendly
            logger.info("📅 Ejecutando agendamiento de reunión...")
            meeting_result = await self._schedule_meeting(current_lead, conversation)

            # PASO 11: update_lead: meeting_scheduled=True
            logger.info("🎉 Marcando reunión como agendada...")
            await self._mark_meeting_scheduled(
                current_lead.id,
                meeting_result.get("meeting_url"),
                meeting_result.get("event_type"),
            )

            # PASO 12: Fin OK
            logger.info("🏁 Workflow completado exitosamente")

            return {
                "status": "completed",
                "lead_id": str(current_lead.id),
                "conversation_id": str(conversation.id),
                "qualified": True,
                "contacted": True,
                "meeting_scheduled": True,
                "meeting_url": meeting_result.get("meeting_url"),
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

        return await self.db_client.get_lead_by_email(email)

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

        return await self.db_client.create_lead(lead_create)

    async def _qualify_lead(self, lead: Any) -> Dict[str, Any]:
        """Ejecutar la calificación del lead usando el agente"""
        try:
            # Preparar datos para el agente calificador
            lead_input = {
                "name": lead.name,
                "email": lead.email,
                "company": lead.company,
                "phone": lead.phone,
                "message": lead.message,
                "source": lead.source,
                "metadata": lead.metadata or {},
            }

            # Ejecutar agente calificador
            qualification_result = await self.lead_qualifier.run(lead_input)

            # El agente debe devolver un dict con 'qualified' y opcionalmente 'reason'
            return qualification_result

        except Exception as e:
            logger.error(f"Error en calificación: {e}")
            return {"qualified": False, "reason": f"Error en calificación: {str(e)}"}

    async def _mark_lead_qualified(self, lead_id: UUID) -> None:
        """Marcar lead como calificado"""
        await self.db_client.mark_lead_as_qualified(lead_id)

    async def _mark_lead_unqualified(self, lead_id: UUID, reason: str = None) -> None:
        """Marcar lead como no calificado"""
        metadata = {"disqualification_reason": reason} if reason else {}
        updates = LeadUpdate(qualified=False, status="disqualified", metadata=metadata)
        await self.db_client.update_lead(lead_id, updates)

    async def _create_conversation(self, lead_id: UUID) -> Any:
        """Crear nueva conversación para el lead"""
        conversation_data = ConversationCreate(
            lead_id=lead_id, channel="automated_workflow", status="active"
        )

        return await self.db_client.create_conversation(conversation_data)

    async def _execute_outbound_contact(
        self, lead: Any, conversation: Any
    ) -> Dict[str, Any]:
        """Ejecutar contacto outbound usando el agente"""
        try:
            # Preparar datos para el agente de outbound
            contact_input = {
                "lead": {
                    "id": str(lead.id),
                    "name": lead.name,
                    "email": lead.email,
                    "company": lead.company,
                    "phone": lead.phone,
                    "message": lead.message,
                },
                "conversation_id": str(conversation.id),
            }

            # Ejecutar agente de outbound
            outbound_result = await self.outbound_agent.run(contact_input)

            return outbound_result

        except Exception as e:
            logger.error(f"Error en outbound contact: {e}")
            return {
                "success": False,
                "error": str(e),
                "contact_method": "failed",
                "message": f"Error en contacto: {str(e)}",
            }

    async def _insert_contact_message(
        self, conversation_id: UUID, outbound_result: Dict[str, Any]
    ) -> None:
        """Insertar mensaje de contacto en la conversación"""
        message_data = MessageCreate(
            conversation_id=conversation_id,
            sender="outbound_agent",
            content=outbound_result.get("message", "Contacto realizado"),
            message_type="outbound_contact",
            metadata={
                "contact_method": outbound_result.get("contact_method"),
                "success": outbound_result.get("success", False),
                "details": outbound_result,
            },
        )

        await self.db_client.create_message(message_data)

    async def _mark_lead_contacted(
        self, lead_id: UUID, contact_method: str = None
    ) -> None:
        """Marcar lead como contactado"""
        await self.db_client.mark_lead_as_contacted(lead_id, contact_method)

    async def _schedule_meeting(self, lead: Any, conversation: Any) -> Dict[str, Any]:
        """Ejecutar agendamiento de reunión usando el agente + Calendly"""
        try:
            # Preparar datos para el agente de reuniones
            meeting_input = {
                "lead": {
                    "id": str(lead.id),
                    "name": lead.name,
                    "email": lead.email,
                    "company": lead.company,
                    "profile": lead.metadata or {},
                    "qualified": lead.qualified,
                },
                "conversation_id": str(conversation.id),
            }

            # Ejecutar agente de reuniones (que usará Calendly MCP)
            meeting_result = await self.meeting_scheduler.run(meeting_input)

            return meeting_result

        except Exception as e:
            logger.error(f"Error en meeting scheduling: {e}")
            return {
                "success": False,
                "error": str(e),
                "meeting_url": "https://calendly.com/contact-support",
            }

    async def _mark_meeting_scheduled(
        self, lead_id: UUID, meeting_url: str, event_type: str = None
    ) -> None:
        """Marcar reunión como agendada"""
        await self.db_client.schedule_meeting_for_lead(lead_id, meeting_url, event_type)


# ===================== CLASE PRINCIPAL DE AGENTES =====================


class Agents:
    """
    Clase principal que orquesta todos los agentes del sistema
    """

    def __init__(self) -> None:
        self.lead_processor = LeadProcessor()
        logger.info("Agents system initialized")

    async def run_workflow(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecutar el workflow completo para un lead

        Args:
            lead_data: Datos del lead (desde POST /leads)

        Returns:
            Resultado del procesamiento
        """
        return await self.lead_processor.process_lead_workflow(lead_data)

    # Método síncrono para compatibilidad con código existente
    def run_workflow_sync(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Versión síncrona del workflow"""
        return asyncio.run(self.run_workflow(lead_data))

    async def get_lead_status(self, lead_id: str) -> Dict[str, Any]:
        """Obtener estado actual de un lead"""
        try:
            lead = await self.lead_processor.db_client.get_lead(lead_id)
            if not lead:
                return {"error": "Lead not found"}

            conversations = await self.lead_processor.db_client.list_conversations(
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
        return self.lead_processor.db_client.get_stats()
