import asyncio
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from app.supabase.supabase_client import (
    SupabaseCRMClient,
    LeadCreate,
)

# Import modern agents with AgentSDK
from app.agents.modern_agents import ModernAgents, TenantContext

# Legacy agents for backward compatibility
from app.agents.lead_qualifier import LeadAgent
from app.agents.meeting_scheduler import MeetingSchedulerAgent
from app.agents.outbound_contact import OutboundAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LeadProcessor:
    """
    Procesador principal de leads con agentes
    """

    def __init__(self):
        # Inicializar cliente de Supabase
        self.db_client = SupabaseCRMClient()
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

            # PASO 3: Agendamiento de reunión (REORDENADO: Ahora va antes del contacto outbound)
            logger.info("📅 Ejecutando agendamiento...")
            meeting_result = await self._schedule_meeting_corrected(current_lead)

            # PASO 4: Contacto outbound (REORDENADO: Ahora va después del agendamiento)
            logger.info("📞 Ejecutando contacto outbound...")
            outbound_result = await self._execute_outbound_corrected(current_lead)

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

        return self.db_client.create_lead(lead_create)

    async def _qualify_lead_corrected(self, lead: Any) -> Dict[str, Any]:
        """
        Calificación que actualiza la base de datos
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
        Contacto outbound que actualiza la base de datos
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
        Agendamiento que actualiza la base de datos
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
    Main orchestrator class for all system agents - Now using AgentSDK
    """

    def __init__(self, tenant_context: Optional[TenantContext] = None) -> None:
        # Modern AgentSDK implementation
        self.modern_agents = ModernAgents(tenant_context)
        
        # Legacy processor for backward compatibility
        self.lead_processor = LeadProcessor()
        
        self.use_modern_agents = True  # Flag to switch between implementations
        logger.info("Agents system initialized with AgentSDK and legacy compatibility")

    async def run_workflow(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complete workflow for a lead using modern AgentSDK
        """
        if self.use_modern_agents:
            logger.info("🚀 Using Modern AgentSDK workflow")
            return await self.modern_agents.run_workflow(lead_data)
        else:
            logger.info("🔄 Using Legacy workflow")
            return await self.lead_processor.process_lead_workflow(lead_data)

    def run_workflow_sync(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous version of workflow"""
        return asyncio.run(self.run_workflow(lead_data))

    async def get_lead_status(self, lead_id: str) -> Dict[str, Any]:
        """Get current status of a lead"""
        try:
            lead = self.lead_processor.db_client.get_lead(lead_id)
            if not lead:
                return {"error": "Lead not found"}

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
                "agent_version": "modern_agentsdk" if self.use_modern_agents else "legacy"
            }
        except Exception as e:
            return {"error": str(e)}

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        stats = self.lead_processor.db_client.get_stats()
        stats["agent_version"] = "modern_agentsdk" if self.use_modern_agents else "legacy"
        return stats

    # Modern AgentSDK-specific methods
    async def qualify_lead_only(self, lead_data: Dict[str, Any]):
        """Run only lead qualification using AgentSDK"""
        if self.use_modern_agents:
            return await self.modern_agents.qualify_lead_only(lead_data)
        else:
            raise NotImplementedError("Legacy agents don't support individual operations")

    async def contact_lead_only(self, lead_id: str, lead_data: Dict[str, Any]):
        """Run only outbound contact using AgentSDK"""
        if self.use_modern_agents:
            return await self.modern_agents.contact_lead_only(lead_id, lead_data)
        else:
            raise NotImplementedError("Legacy agents don't support individual operations")

    async def schedule_meeting_only(self, lead_id: str, lead_data: Dict[str, Any]):
        """Run only meeting scheduling using AgentSDK"""
        if self.use_modern_agents:
            return await self.modern_agents.schedule_meeting_only(lead_id, lead_data)
        else:
            raise NotImplementedError("Legacy agents don't support individual operations")

    def switch_to_legacy(self):
        """Switch to legacy agent implementation"""
        self.use_modern_agents = False
        logger.info("Switched to legacy agent implementation")

    def switch_to_modern(self):
        """Switch to modern AgentSDK implementation"""
        self.use_modern_agents = True
        logger.info("Switched to modern AgentSDK implementation")


# ===================== EJEMPLO DE USO CORREGIDO =====================


async def example_modern_workflow():
    """Example of modern AgentSDK workflow"""

    # Initialize modern agent system with tenant context
    tenant_context = TenantContext(
        tenant_id="example_corp",
        user_id="admin",
        is_premium=True,
        api_limits={"calls_per_hour": 1000},
        features_enabled=["advanced_qualification", "multi_channel_outbound", "calendar_integration"]
    )
    
    agents = Agents(tenant_context)

    # Example lead data
    lead_data = {
        "name": "Sarah Johnson",
        "email": "sarah.johnson@techcorp.com",
        "company": "TechCorp Solutions",
        "phone": "+1-555-0123",
        "message": "We're looking to implement an AI-powered CRM solution for our 150-person sales team. Budget is $50k annually.",
        "source": "website_form",
        "utm_params": {"campaign": "enterprise_landing", "medium": "paid_search"},
        "metadata": {
            "company_size": "100-500",
            "industry": "technology",
            "interest_level": "high",
            "budget_range": "$50k+",
            "decision_timeline": "Q1 2025"
        },
    }

    # Execute modern AgentSDK workflow
    print("🚀 Starting modern AgentSDK workflow...")
    result = await agents.run_workflow(lead_data)

    print(f"✅ Modern workflow result: {result}")

    # Test individual agent operations
    print("\n🔬 Testing individual agent operations...")
    
    try:
        # Test qualification only
        qualification = await agents.qualify_lead_only(lead_data)
        print(f"📊 Qualification result: {qualification}")
        
        # Get system statistics
        stats = await agents.get_system_stats()
        print(f"📈 System stats: {stats}")
        
    except Exception as e:
        print(f"⚠️ Error in individual operations: {e}")

    # Demonstrate legacy compatibility
    print("\n🔄 Testing legacy compatibility...")
    agents.switch_to_legacy()
    legacy_result = await agents.run_workflow(lead_data)
    print(f"🏗️ Legacy workflow result: {legacy_result}")
    
    # Switch back to modern
    agents.switch_to_modern()
    print("✅ Switched back to modern AgentSDK")


if __name__ == "__main__":
    # Execute modern example
    print("Executing modern AgentSDK workflow...")
    asyncio.run(example_modern_workflow())
