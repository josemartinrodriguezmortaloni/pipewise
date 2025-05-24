import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Any
from uuid import UUID, uuid4
import json

from supabase import create_client, Client
from postgrest.exceptions import APIError

# IMPORTACIONES FALTANTES - Necesarias para los tipos
from app.models.lead import Lead
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.lead_schema import LeadCreate, LeadUpdate
from app.schemas.conversations_schema import ConversationCreate, ConversationUpdate
from app.schemas.messsage_schema import MessageCreate

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupabaseCRMClient:
    """Cliente completo para operaciones CRM con Supabase"""

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_ANON_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY environment variables required"
            )

        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("Supabase CRM Client initialized")

    def _get_current_timestamp(self) -> str:
        """Obtener timestamp actual en formato ISO"""
        return datetime.now(timezone.utc).isoformat()

    def _handle_error(self, operation: str, error: Exception) -> None:
        """Manejar errores de manera consistente"""
        logger.error(f"Error in {operation}: {str(error)}")
        if isinstance(error, APIError):
            logger.error(f"API Error details: {error.details}")
        raise

    # ===================== OPERACIONES LEADS =====================

    def create_lead(self, lead_data: LeadCreate) -> Lead:
        """Crear un nuevo lead"""
        try:
            # Preparar datos para inserción
            lead_dict = lead_data.model_dump()
            lead_dict["id"] = str(uuid4())
            lead_dict["created_at"] = self._get_current_timestamp()
            lead_dict["status"] = "new"
            lead_dict["qualified"] = False
            lead_dict["contacted"] = False
            lead_dict["meeting_scheduled"] = False

            # Asegurar que los campos JSON no sean None
            if lead_dict.get("utm_params") is None:
                lead_dict["utm_params"] = {}
            if lead_dict.get("metadata") is None:
                lead_dict["metadata"] = {}

            result = self.client.table("leads").insert(lead_dict).execute()

            if result.data:
                logger.info(f"Lead created successfully: {result.data[0]['id']}")
                return Lead(**result.data[0])
            else:
                raise Exception("No data returned from insert operation")

        except Exception as e:
            self._handle_error("create_lead", e)

    def get_lead(self, lead_id: Union[str, UUID]) -> Optional[Lead]:
        """Obtener un lead por ID"""
        try:
            result = (
                self.client.table("leads").select("*").eq("id", str(lead_id)).execute()
            )

            if result.data:
                return Lead(**result.data[0])
            return None

        except Exception as e:
            self._handle_error("get_lead", e)

    def get_lead_by_email(self, email: str) -> Optional[Lead]:
        """Obtener un lead por email"""
        try:
            result = self.client.table("leads").select("*").eq("email", email).execute()

            if result.data:
                return Lead(**result.data[0])
            return None

        except Exception as e:
            self._handle_error("get_lead_by_email", e)

    def update_lead(self, lead_id: Union[str, UUID], updates: LeadUpdate) -> Lead:
        """Actualizar un lead"""
        try:
            # Filtrar campos None y preparar datos
            update_data = {
                k: v for k, v in updates.model_dump().items() if v is not None
            }

            result = (
                self.client.table("leads")
                .update(update_data)
                .eq("id", str(lead_id))
                .execute()
            )

            if result.data:
                logger.info(f"Lead updated successfully: {lead_id}")
                return Lead(**result.data[0])
            else:
                raise Exception(f"Lead with ID {lead_id} not found")

        except Exception as e:
            self._handle_error("update_lead", e)

    def delete_lead(self, lead_id: Union[str, UUID]) -> bool:
        """Eliminar un lead"""
        try:
            result = (
                self.client.table("leads").delete().eq("id", str(lead_id)).execute()
            )
            return len(result.data) > 0

        except Exception as e:
            self._handle_error("delete_lead", e)

    def list_leads(
        self,
        status: str = None,
        qualified: bool = None,
        contacted: bool = None,
        meeting_scheduled: bool = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Lead]:
        """Listar leads con filtros opcionales"""
        try:
            query = self.client.table("leads").select("*")

            if status:
                query = query.eq("status", status)
            if qualified is not None:
                query = query.eq("qualified", qualified)
            if contacted is not None:
                query = query.eq("contacted", contacted)
            if meeting_scheduled is not None:
                query = query.eq("meeting_scheduled", meeting_scheduled)

            result = (
                query.order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            return [Lead(**lead) for lead in result.data]

        except Exception as e:
            self._handle_error("list_leads", e)

    # ===================== OPERACIONES CONVERSATIONS =====================

    def create_conversation(
        self, conversation_data: ConversationCreate
    ) -> Conversation:
        """Crear una nueva conversación"""
        try:
            # Usar serialize_for_json para manejar UUIDs correctamente
            conv_dict = serialize_for_json(conversation_data.model_dump())
            conv_dict["id"] = str(uuid4())
            conv_dict["started_at"] = self._get_current_timestamp()

            result = self.client.table("conversations").insert(conv_dict).execute()

            if result.data:
                logger.info(f"Conversation created: {result.data[0]['id']}")
                return Conversation(**result.data[0])
            else:
                raise Exception("No data returned from insert operation")

        except Exception as e:
            self._handle_error("create_conversation", e)

    def get_conversation(
        self, conversation_id: Union[str, UUID]
    ) -> Optional[Conversation]:
        """Obtener una conversación por ID"""
        try:
            result = (
                self.client.table("conversations")
                .select("*")
                .eq("id", str(conversation_id))
                .execute()
            )

            if result.data:
                return Conversation(**result.data[0])
            return None

        except Exception as e:
            self._handle_error("get_conversation", e)

    def list_conversations(
        self, lead_id: Union[str, UUID] = None, status: str = None, limit: int = 50
    ) -> List[Conversation]:
        """Listar conversaciones con filtros"""
        try:
            query = self.client.table("conversations").select("*")

            if lead_id:
                query = query.eq("lead_id", str(lead_id))
            if status:
                query = query.eq("status", status)

            result = query.order("started_at", desc=True).limit(limit).execute()

            return [Conversation(**conv) for conv in result.data]

        except Exception as e:
            self._handle_error("list_conversations", e)

    def update_conversation(
        self, conversation_id: Union[str, UUID], updates: ConversationUpdate
    ) -> Conversation:
        """Actualizar una conversación"""
        try:
            update_data = {
                k: v for k, v in updates.model_dump().items() if v is not None
            }

            # Si se está cerrando la conversación, agregar ended_at
            if updates.status and updates.status in ["closed", "completed"]:
                update_data["ended_at"] = self._get_current_timestamp()

            result = (
                self.client.table("conversations")
                .update(update_data)
                .eq("id", str(conversation_id))
                .execute()
            )

            if result.data:
                return Conversation(**result.data[0])
            else:
                raise Exception(f"Conversation with ID {conversation_id} not found")

        except Exception as e:
            self._handle_error("update_conversation", e)

    # ===================== OPERACIONES MESSAGES =====================

    def create_message(self, message_data: MessageCreate) -> Message:
        """Crear un nuevo mensaje"""
        try:
            # Usar serialize_for_json para manejar UUIDs correctamente
            msg_dict = serialize_for_json(message_data.model_dump())
            msg_dict["id"] = str(uuid4())
            msg_dict["sent_at"] = self._get_current_timestamp()

            result = self.client.table("messages").insert(msg_dict).execute()

            if result.data:
                logger.info(f"Message created: {result.data[0]['id']}")
                return Message(**result.data[0])
            else:
                raise Exception("No data returned from insert operation")

        except Exception as e:
            self._handle_error("create_message", e)

    def get_messages(
        self, conversation_id: Union[str, UUID], limit: int = 100
    ) -> List[Message]:
        """Obtener mensajes de una conversación"""
        try:
            result = (
                self.client.table("messages")
                .select("*")
                .eq("conversation_id", str(conversation_id))
                .order("sent_at", desc=False)
                .limit(limit)
                .execute()
            )

            return [Message(**msg) for msg in result.data]

        except Exception as e:
            self._handle_error("get_messages", e)

    # ===================== FUNCIONES ESPECÍFICAS DEL NEGOCIO =====================

    def get_qualified_leads(self) -> List[Lead]:
        """Obtener leads calificados que no han sido contactados"""
        return self.list_leads(qualified=True, contacted=False)

    def get_contacted_leads_without_meeting(self) -> List[Lead]:
        """Obtener leads contactados sin reunión agendada"""
        return self.list_leads(contacted=True, meeting_scheduled=False)

    def get_active_conversations(
        self, lead_id: Union[str, UUID] = None
    ) -> List[Conversation]:
        """Obtener conversaciones activas"""
        return self.list_conversations(lead_id=lead_id, status="active")

    def mark_lead_as_qualified(self, lead_id: Union[str, UUID]) -> Lead:
        """Marcar un lead como calificado"""
        updates = LeadUpdate(qualified=True, status="qualified")
        return self.update_lead(lead_id, updates)

    def mark_lead_as_contacted(
        self, lead_id: Union[str, UUID], contact_method: str = None
    ) -> Lead:
        """Marcar un lead como contactado"""
        metadata = {
            "last_contact_method": contact_method,
            "last_contacted": self._get_current_timestamp(),
        }
        updates = LeadUpdate(contacted=True, status="contacted", metadata=metadata)
        return self.update_lead(lead_id, updates)

    def schedule_meeting_for_lead(
        self, lead_id: Union[str, UUID], meeting_url: str, meeting_type: str = None
    ) -> Lead:
        """Marcar un lead con reunión agendada"""
        metadata = {
            "meeting_url": meeting_url,
            "meeting_scheduled_at": self._get_current_timestamp(),
            "meeting_type": meeting_type,
        }
        updates = LeadUpdate(
            meeting_scheduled=True, status="meeting_scheduled", metadata=metadata
        )
        return self.update_lead(lead_id, updates)

    def close_conversation(
        self, conversation_id: Union[str, UUID], summary: str = None
    ) -> Conversation:
        """Cerrar una conversación"""
        updates = ConversationUpdate(status="closed", summary=summary)
        return self.update_conversation(conversation_id, updates)

    def get_lead_with_conversations(
        self, lead_id: Union[str, UUID]
    ) -> Optional[Dict[str, Any]]:
        """Obtener un lead con sus conversaciones"""
        lead = self.get_lead(lead_id)
        if not lead:
            return None

        conversations = self.list_conversations(lead_id=lead_id)

        return {
            "lead": lead,
            "conversations": conversations,
            "active_conversations": [c for c in conversations if c.status == "active"],
            "total_conversations": len(conversations),
        }

    def get_conversation_with_messages(
        self, conversation_id: Union[str, UUID]
    ) -> Optional[Dict[str, Any]]:
        """Obtener una conversación con sus mensajes"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        messages = self.get_messages(conversation_id)

        return {
            "conversation": conversation,
            "messages": messages,
            "message_count": len(messages),
        }

    # ===================== UTILIDADES =====================

    def health_check(self) -> Dict[str, Any]:
        """Verificar el estado de la conexión a Supabase"""
        try:
            # Intentar una consulta simple
            result = self.client.table("leads").select("id").limit(1).execute()

            return {
                "status": "healthy",
                "timestamp": self._get_current_timestamp(),
                "connection": "ok",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": self._get_current_timestamp(),
                "error": str(e),
            }

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del CRM"""
        try:
            # Contar leads por estado
            total_leads = len(self.client.table("leads").select("id").execute().data)
            qualified_leads = len(
                self.client.table("leads")
                .select("id")
                .eq("qualified", True)
                .execute()
                .data
            )
            contacted_leads = len(
                self.client.table("leads")
                .select("id")
                .eq("contacted", True)
                .execute()
                .data
            )
            meetings_scheduled = len(
                self.client.table("leads")
                .select("id")
                .eq("meeting_scheduled", True)
                .execute()
                .data
            )

            # Contar conversaciones
            total_conversations = len(
                self.client.table("conversations").select("id").execute().data
            )
            active_conversations = len(
                self.client.table("conversations")
                .select("id")
                .eq("status", "active")
                .execute()
                .data
            )

            return {
                "leads": {
                    "total": total_leads,
                    "qualified": qualified_leads,
                    "contacted": contacted_leads,
                    "meetings_scheduled": meetings_scheduled,
                    "conversion_rate": (qualified_leads / total_leads * 100)
                    if total_leads > 0
                    else 0,
                },
                "conversations": {
                    "total": total_conversations,
                    "active": active_conversations,
                },
                "generated_at": self._get_current_timestamp(),
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}

    # ===================== MÉTODOS ASYNC PARA COMPATIBILIDAD CON FUNCTION CALLING =====================

    async def async_create_lead(self, lead_data: LeadCreate) -> Lead:
        """Versión async de create_lead para function calling"""
        return self.create_lead(lead_data)

    async def async_get_lead(self, lead_id: Union[str, UUID]) -> Optional[Lead]:
        """Versión async de get_lead para function calling"""
        return self.get_lead(lead_id)

    async def async_get_lead_by_email(self, email: str) -> Optional[Lead]:
        """Versión async de get_lead_by_email para function calling"""
        return self.get_lead_by_email(email)

    async def async_update_lead(
        self, lead_id: Union[str, UUID], updates: LeadUpdate
    ) -> Lead:
        """Versión async de update_lead para function calling"""
        return self.update_lead(lead_id, updates)

    async def async_list_leads(self, **kwargs) -> List[Lead]:
        """Versión async de list_leads para function calling"""
        return self.list_leads(**kwargs)

    async def async_create_conversation(
        self, conversation_data: ConversationCreate
    ) -> Conversation:
        """Versión async de create_conversation para function calling"""
        return self.create_conversation(conversation_data)

    async def async_get_conversation(
        self, conversation_id: Union[str, UUID]
    ) -> Optional[Conversation]:
        """Versión async de get_conversation para function calling"""
        return self.get_conversation(conversation_id)

    async def async_list_conversations(self, **kwargs) -> List[Conversation]:
        """Versión async de list_conversations para function calling"""
        return self.list_conversations(**kwargs)

    async def async_update_conversation(
        self, conversation_id: Union[str, UUID], updates: ConversationUpdate
    ) -> Conversation:
        """Versión async de update_conversation para function calling"""
        return self.update_conversation(conversation_id, updates)

    async def async_create_message(self, message_data: MessageCreate) -> Message:
        """Versión async de create_message para function calling"""
        return self.create_message(message_data)

    async def async_get_messages(
        self, conversation_id: Union[str, UUID], limit: int = 100
    ) -> List[Message]:
        """Versión async de get_messages para function calling"""
        return self.get_messages(conversation_id, limit)

    async def async_mark_lead_as_qualified(self, lead_id: Union[str, UUID]) -> Lead:
        """Versión async de mark_lead_as_qualified para function calling"""
        return self.mark_lead_as_qualified(lead_id)

    async def async_mark_lead_as_contacted(
        self, lead_id: Union[str, UUID], contact_method: str = None
    ) -> Lead:
        """Versión async de mark_lead_as_contacted para function calling"""
        return self.mark_lead_as_contacted(lead_id, contact_method)

    async def async_schedule_meeting_for_lead(
        self, lead_id: Union[str, UUID], meeting_url: str, meeting_type: str = None
    ) -> Lead:
        """Versión async de schedule_meeting_for_lead para function calling"""
        return self.schedule_meeting_for_lead(lead_id, meeting_url, meeting_type)

    async def async_delete_lead(self, lead_id: Union[str, UUID]) -> bool:
        """Versión async de delete_lead para function calling"""
        return self.delete_lead(lead_id)

    async def async_health_check(self) -> Dict[str, Any]:
        """Versión async de health_check para function calling"""
        return self.health_check()


def safe_uuid_to_str(obj: Any) -> str:
    """Convertir UUID a string de manera segura"""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, str):
        return obj
    else:
        return str(obj)


def safe_str_to_uuid(obj: Any) -> UUID:
    """Convertir string a UUID de manera segura"""
    if isinstance(obj, UUID):
        return obj
    elif isinstance(obj, str):
        return UUID(obj)
    else:
        raise ValueError(f"Cannot convert {type(obj)} to UUID")


def serialize_for_json(obj: Any) -> Any:
    """Serializar objeto para JSON, convirtiendo UUIDs a strings"""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(v) for v in obj]
    else:
        return obj
