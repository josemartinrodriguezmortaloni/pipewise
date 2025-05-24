#!/usr/bin/env python3
"""
Supabase MCP Server para Lead CRM Agent
Permite a Claude interactuar directamente con Supabase para gestionar leads, conversaciones y mensajes
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from dataclasses import dataclass
from pathlib import Path

# Agregar el directorio raíz al path para importaciones
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# MCP imports
try:
    from mcp import types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:
    print("Error: mcp library not installed. Run: pip install mcp")
    sys.exit(1)

# Supabase CRM imports
try:
    from app.supabase.supabase_client import SupabaseCRMClient
    from app.schemas.lead_schema import LeadCreate, LeadUpdate
    from app.schemas.conversations_schema import ConversationCreate, ConversationUpdate
    from app.schemas.messsage_schema import MessageCreate
except ImportError as e:
    # Fallback para testing
    print(f"Warning: Could not import CRM modules: {e}")
    print("This is normal during setup testing")
    SupabaseCRMClient = None

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("supabase-mcp")


@dataclass
class SupabaseConfig:
    """Configuración para Supabase"""

    supabase_url: str
    supabase_key: str

    @classmethod
    def from_env(cls):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY environment variables required"
            )
        return cls(supabase_url=url, supabase_key=key)


# Crear servidor MCP
server = Server("supabase-mcp")

# Instancia global del cliente
supabase_client: Optional[SupabaseCRMClient] = None


def get_supabase_client() -> SupabaseCRMClient:
    """Obtener cliente de Supabase, crearlo si no existe"""
    global supabase_client
    if supabase_client is None:
        if SupabaseCRMClient is None:
            raise Exception("SupabaseCRMClient not available")
        config = SupabaseConfig.from_env()
        supabase_client = SupabaseCRMClient(config.supabase_url, config.supabase_key)
    return supabase_client


def serialize_for_json(obj):
    """Serializar objetos para JSON (manejo de UUID y datetime)"""
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, "model_dump"):
        return serialize_for_json(obj.model_dump())
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    return obj


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """Listar todas las herramientas disponibles"""
    return [
        # ===================== LEADS =====================
        types.Tool(
            name="get_lead",
            description="Obtener un lead por ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "ID del lead a buscar"}
                },
                "required": ["lead_id"],
            },
        ),
        types.Tool(
            name="get_lead_by_email",
            description="Obtener un lead por email",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email del lead a buscar",
                    }
                },
                "required": ["email"],
            },
        ),
        types.Tool(
            name="update_lead",
            description="Actualizar un lead existente",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {
                        "type": "string",
                        "description": "ID del lead a actualizar",
                    },
                    "qualified": {
                        "type": ["boolean", "null"],
                        "description": "Estado de calificación",
                    },
                    "contacted": {
                        "type": ["boolean", "null"],
                        "description": "Estado de contacto",
                    },
                    "meeting_scheduled": {
                        "type": ["boolean", "null"],
                        "description": "Estado de reunión",
                    },
                    "status": {
                        "type": ["string", "null"],
                        "description": "Nuevo estado",
                    },
                    "metadata": {
                        "type": ["object", "null"],
                        "description": "Nueva metadata",
                    },
                },
                "required": ["lead_id"],
            },
        ),
        types.Tool(
            name="list_leads",
            description="Listar leads con filtros opcionales",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": ["string", "null"],
                        "description": "Filtrar por email",
                    },
                    "status": {
                        "type": ["string", "null"],
                        "description": "Filtrar por estado",
                    },
                    "qualified": {
                        "type": ["boolean", "null"],
                        "description": "Filtrar por calificación",
                    },
                    "limit": {
                        "type": ["integer", "null"],
                        "description": "Límite de resultados (default: 100)",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="mark_lead_as_qualified",
            description="Marcar un lead como calificado",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "ID del lead"}
                },
                "required": ["lead_id"],
            },
        ),
        # ===================== CONVERSATIONS =====================
        types.Tool(
            name="list_conversations",
            description="Listar conversaciones con filtros",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {
                        "type": ["string", "null"],
                        "description": "ID del lead",
                    },
                    "status": {
                        "type": ["string", "null"],
                        "description": "Estado de la conversación",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="create_conversation",
            description="Crear una nueva conversación para un lead",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "ID del lead"},
                    "agent_id": {
                        "type": ["string", "null"],
                        "description": "ID del agente",
                    },
                    "channel": {
                        "type": ["string", "null"],
                        "description": "Canal de comunicación",
                    },
                    "status": {
                        "type": ["string", "null"],
                        "description": "Estado inicial",
                    },
                },
                "required": ["lead_id"],
            },
        ),
        types.Tool(
            name="update_conversation",
            description="Actualizar una conversación",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "ID de la conversación",
                    },
                    "status": {
                        "type": ["string", "null"],
                        "description": "Nuevo estado",
                    },
                    "summary": {
                        "type": ["string", "null"],
                        "description": "Resumen de la conversación",
                    },
                },
                "required": ["conversation_id"],
            },
        ),
        # ===================== MESSAGES =====================
        types.Tool(
            name="create_message",
            description="Crear un nuevo mensaje en una conversación",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "ID de la conversación",
                    },
                    "sender": {
                        "type": "string",
                        "description": "Remitente del mensaje",
                    },
                    "content": {
                        "type": "string",
                        "description": "Contenido del mensaje",
                    },
                    "message_type": {
                        "type": ["string", "null"],
                        "description": "Tipo de mensaje",
                    },
                },
                "required": ["conversation_id", "sender", "content"],
            },
        ),
        types.Tool(
            name="get_messages",
            description="Obtener mensajes de una conversación",
            inputSchema={
                "type": "object",
                "properties": {
                    "conversation_id": {
                        "type": "string",
                        "description": "ID de la conversación",
                    }
                },
                "required": ["conversation_id"],
            },
        ),
        # ===================== FUNCIONES ESPECÍFICAS DEL NEGOCIO =====================
        types.Tool(
            name="mark_lead_as_contacted",
            description="Marcar un lead como contactado",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "ID del lead"},
                    "contact_method": {
                        "type": ["string", "null"],
                        "description": "Método de contacto",
                    },
                },
                "required": ["lead_id"],
            },
        ),
        types.Tool(
            name="schedule_meeting_for_lead",
            description="Marcar un lead con reunión agendada",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "ID del lead"},
                    "meeting_url": {
                        "type": "string",
                        "description": "URL de la reunión",
                    },
                    "meeting_type": {
                        "type": ["string", "null"],
                        "description": "Tipo de reunión",
                    },
                },
                "required": ["lead_id", "meeting_url"],
            },
        ),
        types.Tool(
            name="get_active_conversations",
            description="Obtener conversaciones activas",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {
                        "type": ["string", "null"],
                        "description": "ID del lead específico",
                    }
                },
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Ejecutar herramientas"""
    try:
        client = get_supabase_client()

        # ===================== LEADS =====================
        if name == "get_lead":
            result = await client.async_get_lead(arguments["lead_id"])
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        serialize_for_json(result) if result else None, indent=2
                    ),
                )
            ]

        elif name == "get_lead_by_email":
            result = await client.async_get_lead_by_email(arguments["email"])
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        serialize_for_json(result) if result else None, indent=2
                    ),
                )
            ]

        elif name == "update_lead":
            lead_id = arguments.pop("lead_id")
            # Filtrar argumentos None
            update_data = {k: v for k, v in arguments.items() if v is not None}
            updates = LeadUpdate(**update_data)
            result = await client.async_update_lead(lead_id, updates)
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Lead actualizado exitosamente:\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        elif name == "list_leads":
            # Filtrar argumentos None
            filter_args = {k: v for k, v in arguments.items() if v is not None}
            result = await client.async_list_leads(**filter_args)
            return [
                types.TextContent(
                    type="text",
                    text=f"📋 Leads encontrados ({len(result)}):\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        elif name == "mark_lead_as_qualified":
            result = await client.async_mark_lead_as_qualified(arguments["lead_id"])
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Lead marcado como calificado:\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        # ===================== CONVERSATIONS =====================
        elif name == "list_conversations":
            # Filtrar argumentos None
            filter_args = {k: v for k, v in arguments.items() if v is not None}
            result = await client.async_list_conversations(**filter_args)
            return [
                types.TextContent(
                    type="text",
                    text=f"💬 Conversaciones encontradas ({len(result)}):\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        elif name == "create_conversation":
            # Filtrar argumentos None
            conv_data_dict = {k: v for k, v in arguments.items() if v is not None}
            conv_data = ConversationCreate(**conv_data_dict)
            result = await client.async_create_conversation(conv_data)
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Conversación creada:\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        elif name == "update_conversation":
            conversation_id = arguments.pop("conversation_id")
            # Filtrar argumentos None
            update_data = {k: v for k, v in arguments.items() if v is not None}
            updates = ConversationUpdate(**update_data)
            result = await client.async_update_conversation(conversation_id, updates)
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Conversación actualizada:\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        # ===================== MESSAGES =====================
        elif name == "create_message":
            # Filtrar argumentos None
            msg_data_dict = {k: v for k, v in arguments.items() if v is not None}
            msg_data = MessageCreate(**msg_data_dict)
            result = await client.async_create_message(msg_data)
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Mensaje creado:\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        elif name == "get_messages":
            result = await client.async_get_messages(arguments["conversation_id"])
            return [
                types.TextContent(
                    type="text",
                    text=f"📨 Mensajes encontrados ({len(result)}):\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        # ===================== FUNCIONES ESPECÍFICAS DEL NEGOCIO =====================
        elif name == "mark_lead_as_contacted":
            lead_id = arguments["lead_id"]
            contact_method = arguments.get("contact_method")
            result = await client.async_mark_lead_as_contacted(lead_id, contact_method)
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Lead marcado como contactado:\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        elif name == "schedule_meeting_for_lead":
            result = await client.async_schedule_meeting_for_lead(
                arguments["lead_id"],
                arguments["meeting_url"],
                arguments.get("meeting_type"),
            )
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Reunión agendada para el lead:\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        elif name == "get_active_conversations":
            lead_id = arguments.get("lead_id")
            result = client.get_active_conversations(lead_id)
            return [
                types.TextContent(
                    type="text",
                    text=f"💬 Conversaciones activas ({len(result)}):\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        else:
            return [
                types.TextContent(
                    type="text", text=f"❌ Herramienta desconocida: {name}"
                )
            ]

    except Exception as e:
        logger.error(f"Error ejecutando herramienta {name}: {e}")
        return [
            types.TextContent(type="text", text=f"❌ Error ejecutando {name}: {str(e)}")
        ]


async def main():
    """Ejecutar servidor MCP"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    # Script de configuración para facilitar el setup
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        print("🔧 Configuración del Supabase MCP Server")
        print("\n1. Instalar dependencias:")
        print("   pip install mcp")
        print("\n2. Configurar variables de entorno:")
        print("   export SUPABASE_URL='https://tu-proyecto.supabase.co'")
        print("   export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'")
        print("\n3. Ejecutar:")
        print("   python app/agents/tools/supabase_mcp.py")
    else:
        asyncio.run(main())
