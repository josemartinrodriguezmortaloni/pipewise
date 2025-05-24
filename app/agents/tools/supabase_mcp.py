#!/usr/bin/env python3
"""
Supabase MCP Server para Lead CRM Agent
Permite a Claude interactuar directamente con Supabase para gestionar leads, conversaciones y mensajes
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from dataclasses import dataclass

# MCP imports
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Supabase CRM imports
from app.supabase.supabase_client import SupabaseCRMClient
from app.schemas.lead_schema import LeadCreate, LeadUpdate
from app.schemas.conversations_schema import ConversationCreate, ConversationUpdate
from app.schemas.messsage_schema import MessageCreate

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
            name="create_lead",
            description="Crear un nuevo lead",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nombre del lead"},
                    "email": {"type": "string", "description": "Email del lead"},
                    "company": {"type": "string", "description": "Empresa del lead"},
                    "phone": {
                        "type": ["string", "null"],
                        "description": "Teléfono del lead",
                    },
                    "message": {
                        "type": ["string", "null"],
                        "description": "Mensaje del lead",
                    },
                    "source": {
                        "type": ["string", "null"],
                        "description": "Fuente del lead",
                    },
                    "utm_params": {
                        "type": ["object", "null"],
                        "description": "Parámetros UTM",
                    },
                    "metadata": {
                        "type": ["object", "null"],
                        "description": "Metadata adicional",
                    },
                },
                "required": ["name", "email", "company"],
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
                    "name": {"type": ["string", "null"], "description": "Nuevo nombre"},
                    "email": {"type": ["string", "null"], "description": "Nuevo email"},
                    "company": {
                        "type": ["string", "null"],
                        "description": "Nueva empresa",
                    },
                    "phone": {
                        "type": ["string", "null"],
                        "description": "Nuevo teléfono",
                    },
                    "message": {
                        "type": ["string", "null"],
                        "description": "Nuevo mensaje",
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
                    "utm_params": {
                        "type": ["object", "null"],
                        "description": "Nuevos parámetros UTM",
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
                    "status": {
                        "type": ["string", "null"],
                        "description": "Filtrar por estado",
                    },
                    "qualified": {
                        "type": ["boolean", "null"],
                        "description": "Filtrar por calificación",
                    },
                    "contacted": {
                        "type": ["boolean", "null"],
                        "description": "Filtrar por contacto",
                    },
                    "meeting_scheduled": {
                        "type": ["boolean", "null"],
                        "description": "Filtrar por reunión",
                    },
                    "limit": {
                        "type": ["integer", "null"],
                        "description": "Límite de resultados (default: 100)",
                    },
                    "offset": {
                        "type": ["integer", "null"],
                        "description": "Offset para paginación (default: 0)",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="delete_lead",
            description="Eliminar un lead",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {
                        "type": "string",
                        "description": "ID del lead a eliminar",
                    }
                },
                "required": ["lead_id"],
            },
        ),
        # ===================== CONVERSATIONS =====================
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
            name="get_conversation",
            description="Obtener una conversación por ID",
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
                    "limit": {
                        "type": ["integer", "null"],
                        "description": "Límite de resultados",
                    },
                },
                "required": [],
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
                    "agent_id": {
                        "type": ["string", "null"],
                        "description": "Nuevo agente",
                    },
                    "status": {
                        "type": ["string", "null"],
                        "description": "Nuevo estado",
                    },
                    "summary": {
                        "type": ["string", "null"],
                        "description": "Resumen de la conversación",
                    },
                    "channel": {
                        "type": ["string", "null"],
                        "description": "Nuevo canal",
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
                    "metadata": {
                        "type": ["object", "null"],
                        "description": "Metadata del mensaje",
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
                    },
                    "limit": {
                        "type": ["integer", "null"],
                        "description": "Límite de mensajes",
                    },
                },
                "required": ["conversation_id"],
            },
        ),
        # ===================== FUNCIONES ESPECÍFICAS DEL NEGOCIO =====================
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
            name="get_qualified_leads",
            description="Obtener leads calificados que no han sido contactados",
            inputSchema={"type": "object", "properties": {}, "required": []},
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
        types.Tool(
            name="get_lead_with_conversations",
            description="Obtener un lead con todas sus conversaciones",
            inputSchema={
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string", "description": "ID del lead"}
                },
                "required": ["lead_id"],
            },
        ),
        # ===================== UTILIDADES =====================
        types.Tool(
            name="health_check",
            description="Verificar el estado de la conexión a Supabase",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_stats",
            description="Obtener estadísticas del CRM",
            inputSchema={"type": "object", "properties": {}, "required": []},
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

        elif name == "create_lead":
            # Filtrar argumentos None
            lead_data_dict = {k: v for k, v in arguments.items() if v is not None}
            lead_data = LeadCreate(**lead_data_dict)
            result = await client.async_create_lead(lead_data)
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Lead creado exitosamente:\n{json.dumps(serialize_for_json(result), indent=2)}",
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

        elif name == "delete_lead":
            result = await client.async_delete_lead(arguments["lead_id"])
            return [types.TextContent(type="text", text=f"✅ Lead eliminado: {result}")]

        # ===================== CONVERSATIONS =====================
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

        elif name == "get_conversation":
            result = await client.async_get_conversation(arguments["conversation_id"])
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        serialize_for_json(result) if result else None, indent=2
                    ),
                )
            ]

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
            conversation_id = arguments["conversation_id"]
            limit = arguments.get("limit", 100)
            result = await client.async_get_messages(conversation_id, limit)
            return [
                types.TextContent(
                    type="text",
                    text=f"📨 Mensajes encontrados ({len(result)}):\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        # ===================== FUNCIONES ESPECÍFICAS DEL NEGOCIO =====================
        elif name == "mark_lead_as_qualified":
            result = await client.async_mark_lead_as_qualified(arguments["lead_id"])
            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Lead marcado como calificado:\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

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

        elif name == "get_qualified_leads":
            result = client.get_qualified_leads()
            return [
                types.TextContent(
                    type="text",
                    text=f"🎯 Leads calificados ({len(result)}):\n{json.dumps(serialize_for_json(result), indent=2)}",
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

        elif name == "get_lead_with_conversations":
            result = client.get_lead_with_conversations(arguments["lead_id"])
            return [
                types.TextContent(
                    type="text",
                    text=f"👤 Lead con conversaciones:\n{json.dumps(serialize_for_json(result), indent=2)}",
                )
            ]

        # ===================== UTILIDADES =====================
        elif name == "health_check":
            result = await client.async_health_check()
            return [
                types.TextContent(
                    type="text",
                    text=f"🔍 Estado de Supabase:\n{json.dumps(result, indent=2)}",
                )
            ]

        elif name == "get_stats":
            result = client.get_stats()
            return [
                types.TextContent(
                    type="text",
                    text=f"📊 Estadísticas del CRM:\n{json.dumps(result, indent=2)}",
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
        print("\n3. Agregar a tu configuración MCP:")
        print(
            json.dumps(
                {
                    "mcpServers": {
                        "supabase": {
                            "command": "python",
                            "args": [__file__],
                            "env": {
                                "SUPABASE_URL": "https://tu-proyecto.supabase.co",
                                "SUPABASE_ANON_KEY": "tu_key_aqui",
                            },
                        }
                    }
                },
                indent=2,
            )
        )
        print("\n4. Ejecutar:")
        print("   python supabase_mcp.py")
    else:
        asyncio.run(main())
