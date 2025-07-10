import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Any
from uuid import UUID, uuid4

from supabase import create_client, Client
from postgrest.exceptions import APIError

# IMPORTACIONES FALTANTES - Necesarias para los tipos
from app.models.lead import Lead
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.lead_schema import LeadCreate, LeadUpdate
from app.schemas.conversations_schema import ConversationCreate, ConversationUpdate
from app.schemas.messsage_schema import MessageCreate
from app.schemas.contacts_schema import (
    ContactCreate,
    ContactUpdate,
    OutreachMessageCreate,
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SupabaseCRMClient:
    """Cliente completo para operaciones CRM con Supabase"""

    def __init__(
        self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None
    ):
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_ANON_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY environment variables required"
            )

        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("Supabase CRM Client initialized")

    def table(self, table_name: str):
        """Direct access to table operations for compatibility with oauth_handler"""
        return self.client.table(table_name)

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
            # Usar serialize_for_json para manejar UUIDs correctamente
            lead_dict = serialize_for_json(lead_data.model_dump())
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
            raise  # This ensures the function always returns or raises

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
            return None

    def get_lead_by_email(self, email: str) -> Optional[Lead]:
        """Obtener un lead por email"""
        try:
            result = self.client.table("leads").select("*").eq("email", email).execute()

            if result.data:
                return Lead(**result.data[0])
            return None

        except Exception as e:
            self._handle_error("get_lead_by_email", e)
            return None

    def update_lead(self, lead_id: Union[str, UUID], updates: LeadUpdate) -> Lead:
        """Update lead in database with improved error handling"""
        try:
            # Convert UUID to string if needed
            lead_id_str = str(lead_id)

            # Convert updates to dict and exclude None values
            update_data = updates.model_dump(exclude_unset=True, exclude_none=True)

            # Don't try to set updated_at manually - let the trigger handle it
            update_data.pop("updated_at", None)

            # If update_data is empty after filtering, add a dummy field to trigger the update
            if not update_data:
                update_data = {"status": "new"}  # Default status

            logger.info(f"Updating lead {lead_id_str} with data: {update_data}")

            result = (
                self.client.table("leads")
                .update(update_data)
                .eq("id", lead_id_str)
                .execute()
            )

            if not result.data:
                raise ValueError(f"Lead {lead_id_str} not found or update failed")

            updated_lead = Lead(**result.data[0])
            logger.info(
                f"Lead updated successfully: {updated_lead.id} - {updated_lead.name}"
            )
            return updated_lead

        except Exception as e:
            logger.error(f"Error in update_lead: {e}")
            logger.error(
                f"Update data was: {update_data if 'update_data' in locals() else 'undefined'}"
            )

            # Try to provide helpful error context
            if "updated_at" in str(e):
                logger.error("Database schema issue: updated_at field not found")
                logger.error("Please run the database schema fix script")

            self._handle_error("update_lead", e)
            # _handle_error raises an exception, but add explicit raise for linter
            raise

    def delete_lead(self, lead_id: Union[str, UUID]) -> bool:
        """Eliminar un lead"""
        try:
            result = (
                self.client.table("leads").delete().eq("id", str(lead_id)).execute()
            )
            return len(result.data) > 0

        except Exception as e:
            self._handle_error("delete_lead", e)
            return False

    def list_leads(
        self,
        status: Optional[str] = None,
        qualified: Optional[bool] = None,
        contacted: Optional[bool] = None,
        meeting_scheduled: Optional[bool] = None,
        user_id: Optional[str] = None,
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
            if user_id is not None:
                query = query.eq("user_id", user_id)

            result = (
                query.order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            return [Lead(**lead) for lead in result.data]

        except Exception as e:
            self._handle_error("list_leads", e)
            return []

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
            raise  # This ensures the function always returns or raises

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
            return None

    def list_conversations(
        self,
        lead_id: Optional[Union[str, UUID]] = None,
        status: Optional[str] = None,
        limit: int = 50,
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
            return []

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
            raise  # This ensures the function always returns or raises

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
            raise  # This ensures the function always returns or raises

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
            return []

    def get_messages_with_filters(self, **kwargs) -> List[Message]:
        """Método alternativo para obtener mensajes con argumentos keyword"""
        conversation_id = kwargs.get("conversation_id")
        limit = kwargs.get("limit", 100)

        if not conversation_id:
            raise ValueError("conversation_id is required")

        return self.get_messages(conversation_id, limit)

    # ===================== FUNCIONES ESPECÍFICAS DEL NEGOCIO =====================

    def get_qualified_leads(self) -> List[Lead]:
        """Obtener leads calificados que no han sido contactados"""
        return self.list_leads(qualified=True, contacted=False)

    def get_contacted_leads_without_meeting(self) -> List[Lead]:
        """Obtener leads contactados sin reunión agendada"""
        return self.list_leads(contacted=True, meeting_scheduled=False)

    def get_active_conversations(
        self, lead_id: Optional[Union[str, UUID]] = None
    ) -> List[Conversation]:
        """Obtener conversaciones activas"""
        return self.list_conversations(lead_id=lead_id, status="active")

    def mark_lead_as_qualified(self, lead_id: Union[str, UUID]) -> Lead:
        """Marcar un lead como calificado"""
        updates = LeadUpdate(qualified=True, status="qualified")
        return self.update_lead(lead_id, updates)

    def mark_lead_as_contacted(
        self, lead_id: Union[str, UUID], contact_method: Optional[str] = None
    ) -> Lead:
        """Marcar un lead como contactado"""
        metadata = {
            "last_contact_method": contact_method,
            "last_contacted": self._get_current_timestamp(),
        }
        updates = LeadUpdate(contacted=True, status="contacted", metadata=metadata)
        return self.update_lead(lead_id, updates)

    def schedule_meeting_for_lead(
        self,
        lead_id: Union[str, UUID],
        meeting_url: str,
        meeting_type: Optional[str] = None,
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
        self, conversation_id: Union[str, UUID], summary: Optional[str] = None
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

    # ===================== OPERACIONES CONTACTOS =====================

    def create_contact(self, contact_data: ContactCreate) -> Dict[str, Any]:
        """Crear un nuevo contacto"""
        try:
            contact_dict = serialize_for_json(contact_data.model_dump())
            contact_dict["id"] = str(uuid4())
            contact_dict["created_at"] = self._get_current_timestamp()

            result = self.client.table("contacts").insert(contact_dict).execute()

            if result.data:
                logger.info(f"Contact created successfully: {result.data[0]['id']}")
                return result.data[0]
            else:
                raise Exception("No data returned from insert operation")

        except Exception as e:
            self._handle_error("create_contact", e)
            raise  # This ensures the function always returns or raises

    def get_contact(self, contact_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """Obtener un contacto por ID"""
        try:
            result = (
                self.client.table("contacts")
                .select("*")
                .eq("id", str(contact_id))
                .execute()
            )

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            self._handle_error("get_contact", e)
            return None

    def get_contact_by_platform(
        self, platform: str, platform_id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtener contacto por plataforma y platform_id"""
        try:
            result = (
                self.client.table("contacts")
                .select("*")
                .eq("platform", platform)
                .eq("platform_id", platform_id)
                .execute()
            )

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            self._handle_error("get_contact_by_platform", e)
            return None

    def list_contacts(
        self,
        platform: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Listar contactos con filtros opcionales"""
        try:
            query = self.client.table("contacts_with_stats").select("*")

            if platform:
                query = query.eq("platform", platform)
            if user_id:
                query = query.eq("user_id", user_id)

            result = (
                query.order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            return result.data

        except Exception as e:
            self._handle_error("list_contacts", e)
            return []

    def update_contact(
        self, contact_id: Union[str, UUID], updates: ContactUpdate
    ) -> Dict[str, Any]:
        """Actualizar un contacto"""
        try:
            update_data = {
                k: v for k, v in updates.model_dump().items() if v is not None
            }

            result = (
                self.client.table("contacts")
                .update(update_data)
                .eq("id", str(contact_id))
                .execute()
            )

            if result.data:
                logger.info(f"Contact updated successfully: {contact_id}")
                return result.data[0]
            else:
                raise Exception(f"Contact with ID {contact_id} not found")

        except Exception as e:
            self._handle_error("update_contact", e)
            raise  # This ensures the function always returns or raises

    def create_outreach_message(
        self, message_data: OutreachMessageCreate
    ) -> Dict[str, Any]:
        """Crear mensaje de outreach"""
        try:
            message_dict = message_data.model_dump()
            message_dict["id"] = str(uuid4())
            message_dict["sent_at"] = self._get_current_timestamp()

            result = (
                self.client.table("outreach_messages").insert(message_dict).execute()
            )

            if result.data:
                logger.info(f"Outreach message created: {result.data[0]['id']}")
                return result.data[0]
            else:
                raise Exception("No data returned from insert operation")

        except Exception as e:
            self._handle_error("create_outreach_message", e)
            raise  # This ensures the function always returns or raises

    def get_contact_messages(
        self, contact_id: Union[str, UUID]
    ) -> List[Dict[str, Any]]:
        """Obtener mensajes de un contacto"""
        try:
            result = (
                self.client.table("outreach_messages")
                .select("*")
                .eq("contact_id", str(contact_id))
                .order("sent_at", desc=True)
                .execute()
            )

            return result.data

        except Exception as e:
            self._handle_error("get_contact_messages", e)
            return []

    def get_contact_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtener estadísticas de contactos"""
        try:
            # Usar función SQL para obtener estadísticas agregadas
            result = self.client.rpc(
                "get_contact_stats", {"user_id_param": user_id}
            ).execute()

            if result.data:
                return result.data

            # Fallback: calcular estadísticas manualmente
            contacts = self.list_contacts(user_id=user_id)

            platform_counts = {}
            total_messages = 0
            meetings_scheduled = 0

            for contact in contacts:
                platform = contact["platform"]
                platform_counts[platform] = platform_counts.get(platform, 0) + 1
                total_messages += contact.get("total_messages", 0)
                if contact.get("meeting_scheduled", False):
                    meetings_scheduled += 1

            # Fix the max function call to filter None values and ensure type safety
            last_message_dates = [
                c.get("last_message_at")
                for c in contacts
                if c.get("last_message_at") is not None
            ]

            # Type safe max operation - cast to str to ensure comparability
            last_contact_date = None
            if last_message_dates:
                try:
                    # Filter and convert to strings if needed for comparison
                    valid_dates = [
                        str(date) for date in last_message_dates if date is not None
                    ]
                    last_contact_date = max(valid_dates) if valid_dates else None
                except (TypeError, ValueError):
                    last_contact_date = None

            return {
                "total_contacts": len(contacts),
                "contacts_by_platform": platform_counts,
                "messages_sent": total_messages,
                "meetings_scheduled": meetings_scheduled,
                "conversion_rate": (meetings_scheduled / len(contacts) * 100)
                if contacts
                else 0,
                "last_contact_date": last_contact_date,
            }

        except Exception as e:
            self._handle_error("get_contact_stats", e)
            return {}

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
        self, lead_id: Union[str, UUID], contact_method: Optional[str] = None
    ) -> Lead:
        """Versión async de mark_lead_as_contacted para function calling"""
        return self.mark_lead_as_contacted(lead_id, contact_method)

    async def async_schedule_meeting_for_lead(
        self,
        lead_id: Union[str, UUID],
        meeting_url: str,
        meeting_type: Optional[str] = None,
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


def get_supabase_client() -> SupabaseCRMClient:
    """Get a Supabase CRM client instance."""
    return SupabaseCRMClient()


def get_supabase_admin_client() -> SupabaseCRMClient:
    """Get a Supabase CRM client instance with admin privileges (bypasses RLS)."""
    # Use service role key instead of anon key for admin operations
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not service_role_key:
        logger.warning("SUPABASE_SERVICE_ROLE_KEY not found, falling back to anon key")
        service_role_key = os.getenv("SUPABASE_ANON_KEY")

    return SupabaseCRMClient(supabase_url=supabase_url, supabase_key=service_role_key)
