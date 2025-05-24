#!/usr/bin/env python3
"""
Calendly MCP Server para Lead CRM Agent
Permite a Claude interactuar directamente con Calendly para gestionar reuniones
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import requests
from dataclasses import dataclass

# MCP imports
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("calendly-mcp")


@dataclass
class CalendlyConfig:
    """Configuración para Calendly"""

    access_token: str
    base_url: str = "https://api.calendly.com"

    @classmethod
    def from_env(cls):
        token = os.getenv("CALENDLY_ACCESS_TOKEN")
        if not token:
            raise ValueError("CALENDLY_ACCESS_TOKEN environment variable required")
        return cls(access_token=token)


class CalendlyClient:
    """Cliente para interactuar con la API de Calendly"""

    def __init__(self, config: CalendlyConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self, method: str, endpoint: str, params: Dict = None, data: Dict = None
    ) -> Dict:
        """Realizar solicitud HTTP a la API de Calendly"""
        url = f"{self.config.base_url}{endpoint}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error en solicitud {method} {endpoint}: {e}")
            raise Exception(f"Error de API Calendly: {str(e)}")

    async def get_current_user(self) -> Dict:
        """Obtener información del usuario actual"""
        return self._make_request("GET", "/users/me")

    async def get_event_types(self, user_uri: str) -> Dict:
        """Obtener tipos de eventos disponibles"""
        params = {"user": user_uri}
        return self._make_request("GET", "/event_types", params=params)

    async def get_available_times(
        self, event_type_uri: str, start_time: str, end_time: str
    ) -> Dict:
        """Obtener horarios disponibles"""
        params = {
            "event_type": event_type_uri,
            "start_time": start_time,
            "end_time": end_time,
        }
        return self._make_request("GET", "/event_type_available_times", params=params)

    async def create_scheduling_link(
        self, event_type_uri: str, max_event_count: int = 1
    ) -> Dict:
        """Crear link de agendamiento único"""
        data = {
            "max_event_count": max_event_count,
            "owner": event_type_uri,
            "owner_type": "EventType",
        }
        return self._make_request("POST", "/scheduling_links", data=data)

    async def get_scheduled_events(
        self, user_uri: str, start_time: str = None, end_time: str = None
    ) -> Dict:
        """Obtener eventos programados"""
        params = {"user": user_uri}
        if start_time:
            params["min_start_time"] = start_time
        if end_time:
            params["max_start_time"] = end_time
        return self._make_request("GET", "/scheduled_events", params=params)

    async def get_event_details(self, event_uuid: str) -> Dict:
        """Obtener detalles de un evento específico"""
        return self._make_request("GET", f"/scheduled_events/{event_uuid}")

    async def cancel_event(
        self, event_uuid: str, reason: str = "Cancelado automáticamente"
    ) -> Dict:
        """Cancelar un evento"""
        data = {"reason": reason}
        return self._make_request(
            "POST", f"/scheduled_events/{event_uuid}/cancellation", data=data
        )


# Crear servidor MCP
server = Server("calendly-mcp")

# Instancia global del cliente
calendly_client: Optional[CalendlyClient] = None


def get_calendly_client() -> CalendlyClient:
    """Obtener cliente de Calendly, crearlo si no existe"""
    global calendly_client
    if calendly_client is None:
        config = CalendlyConfig.from_env()
        calendly_client = CalendlyClient(config)
    return calendly_client


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """Listar todas las herramientas disponibles"""
    return [
        types.Tool(
            name="get_calendly_user",
            description="Obtener información del usuario actual de Calendly",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_event_types",
            description="Obtener tipos de eventos disponibles para agendar",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_available_times",
            description="Obtener horarios disponibles para un tipo de evento específico",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type_uri": {
                        "type": "string",
                        "description": "URI del tipo de evento",
                    },
                    "days_ahead": {
                        "type": "integer",
                        "description": "Número de días hacia adelante para consultar (default: 7)",
                        "default": 7,
                    },
                },
                "required": ["event_type_uri"],
            },
        ),
        types.Tool(
            name="create_scheduling_link",
            description="Crear un link único para que un lead pueda agendar una reunión",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type_name": {
                        "type": "string",
                        "description": "Nombre del tipo de evento (ej: 'Sales Call', 'Demo')",
                    },
                    "event_type_uri": {
                        "type": "string",
                        "description": "URI del tipo de evento (opcional si se proporciona event_type_name)",
                    },
                    "max_uses": {
                        "type": "integer",
                        "description": "Máximo número de usos del link (default: 1)",
                        "default": 1,
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_scheduled_events",
            description="Obtener reuniones programadas en un rango de fechas",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "integer",
                        "description": "Días hacia adelante para consultar (default: 30)",
                        "default": 30,
                    },
                    "include_past": {
                        "type": "boolean",
                        "description": "Incluir eventos pasados (default: false)",
                        "default": False,
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get_event_details",
            description="Obtener detalles completos de un evento específico",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_uuid": {"type": "string", "description": "UUID del evento"}
                },
                "required": ["event_uuid"],
            },
        ),
        types.Tool(
            name="cancel_event",
            description="Cancelar un evento programado",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_uuid": {
                        "type": "string",
                        "description": "UUID del evento a cancelar",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Razón de la cancelación",
                        "default": "Cancelado por el sistema CRM",
                    },
                },
                "required": ["event_uuid"],
            },
        ),
        types.Tool(
            name="find_best_meeting_slot",
            description="Encontrar el mejor horario disponible para agendar una reunión",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type_name": {
                        "type": "string",
                        "description": "Tipo de reunión (ej: 'Sales Call', 'Demo')",
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "Hora preferida (ej: 'morning', 'afternoon', 'evening')",
                    },
                    "days_ahead": {
                        "type": "integer",
                        "description": "Buscar en los próximos X días (default: 7)",
                        "default": 7,
                    },
                },
                "required": ["event_type_name"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Ejecutar herramientas"""
    try:
        client = get_calendly_client()

        if name == "get_calendly_user":
            result = await client.get_current_user()
            user_info = {
                "name": result["resource"]["name"],
                "email": result["resource"]["email"],
                "timezone": result["resource"]["timezone"],
                "uri": result["resource"]["uri"],
            }
            return [
                types.TextContent(
                    type="text",
                    text=f"Usuario Calendly: {json.dumps(user_info, indent=2)}",
                )
            ]

        elif name == "get_event_types":
            user_data = await client.get_current_user()
            user_uri = user_data["resource"]["uri"]

            result = await client.get_event_types(user_uri)
            event_types = []

            for event_type in result["collection"]:
                event_types.append(
                    {
                        "name": event_type["name"],
                        "duration": event_type["duration"],
                        "uri": event_type["uri"],
                        "description": event_type.get("description_plain", ""),
                        "active": event_type["active"],
                    }
                )

            return [
                types.TextContent(
                    type="text",
                    text=f"Tipos de eventos disponibles:\n{json.dumps(event_types, indent=2)}",
                )
            ]

        elif name == "get_available_times":
            event_type_uri = arguments["event_type_uri"]
            days_ahead = arguments.get("days_ahead", 7)

            start_time = datetime.now().isoformat()
            end_time = (datetime.now() + timedelta(days=days_ahead)).isoformat()

            result = await client.get_available_times(
                event_type_uri, start_time, end_time
            )

            available_slots = []
            for slot in result["collection"]:
                start_dt = datetime.fromisoformat(
                    slot["start_time"].replace("Z", "+00:00")
                )
                available_slots.append(
                    {
                        "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
                        "day_of_week": start_dt.strftime("%A"),
                        "iso_time": slot["start_time"],
                    }
                )

            return [
                types.TextContent(
                    type="text",
                    text=f"Horarios disponibles:\n{json.dumps(available_slots, indent=2)}",
                )
            ]

        elif name == "create_scheduling_link":
            user_data = await client.get_current_user()
            user_uri = user_data["resource"]["uri"]

            # Si se proporciona event_type_name, buscar el URI
            if "event_type_name" in arguments and not arguments.get("event_type_uri"):
                event_types_data = await client.get_event_types(user_uri)
                event_type_uri = None

                for event_type in event_types_data["collection"]:
                    if (
                        event_type["name"].lower()
                        == arguments["event_type_name"].lower()
                    ):
                        event_type_uri = event_type["uri"]
                        break

                if not event_type_uri:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"❌ No se encontró el tipo de evento: {arguments['event_type_name']}",
                        )
                    ]
            else:
                event_type_uri = arguments.get("event_type_uri")
                if not event_type_uri:
                    # Usar el primer tipo de evento disponible
                    event_types_data = await client.get_event_types(user_uri)
                    if event_types_data["collection"]:
                        event_type_uri = event_types_data["collection"][0]["uri"]
                    else:
                        return [
                            types.TextContent(
                                type="text",
                                text="❌ No hay tipos de eventos disponibles",
                            )
                        ]

            max_uses = arguments.get("max_uses", 1)
            result = await client.create_scheduling_link(event_type_uri, max_uses)

            link_info = {
                "booking_url": result["resource"]["booking_url"],
                "max_event_count": result["resource"]["max_event_count"],
                "owner_type": result["resource"]["owner_type"],
            }

            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Link de agendamiento creado:\n{json.dumps(link_info, indent=2)}",
                )
            ]

        elif name == "get_scheduled_events":
            user_data = await client.get_current_user()
            user_uri = user_data["resource"]["uri"]

            days_ahead = arguments.get("days_ahead", 30)
            include_past = arguments.get("include_past", False)

            if include_past:
                start_time = (datetime.now() - timedelta(days=30)).isoformat()
            else:
                start_time = datetime.now().isoformat()

            end_time = (datetime.now() + timedelta(days=days_ahead)).isoformat()

            result = await client.get_scheduled_events(user_uri, start_time, end_time)

            events = []
            for event in result["collection"]:
                start_dt = datetime.fromisoformat(
                    event["start_time"].replace("Z", "+00:00")
                )
                events.append(
                    {
                        "name": event["name"],
                        "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
                        "status": event["status"],
                        "uuid": event["uri"].split("/")[-1],
                        "location": event.get("location", {}).get("type", "N/A"),
                    }
                )

            return [
                types.TextContent(
                    type="text",
                    text=f"Eventos programados:\n{json.dumps(events, indent=2)}",
                )
            ]

        elif name == "get_event_details":
            event_uuid = arguments["event_uuid"]
            result = await client.get_event_details(event_uuid)

            event = result["resource"]
            start_dt = datetime.fromisoformat(
                event["start_time"].replace("Z", "+00:00")
            )
            end_dt = datetime.fromisoformat(event["end_time"].replace("Z", "+00:00"))

            event_details = {
                "name": event["name"],
                "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
                "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
                "status": event["status"],
                "location": event.get("location", {}),
                "meeting_notes": event.get("meeting_notes_plain", ""),
                "invitees_counter": event.get("invitees_counter", {}),
            }

            return [
                types.TextContent(
                    type="text",
                    text=f"Detalles del evento:\n{json.dumps(event_details, indent=2)}",
                )
            ]

        elif name == "cancel_event":
            event_uuid = arguments["event_uuid"]
            reason = arguments.get("reason", "Cancelado por el sistema CRM")

            await client.cancel_event(event_uuid, reason)

            return [
                types.TextContent(
                    type="text",
                    text=f"✅ Evento {event_uuid} cancelado exitosamente. Razón: {reason}",
                )
            ]

        elif name == "find_best_meeting_slot":
            user_data = await client.get_current_user()
            user_uri = user_data["resource"]["uri"]

            # Buscar tipo de evento
            event_types_data = await client.get_event_types(user_uri)
            event_type_uri = None
            event_type_name = arguments["event_type_name"]

            for event_type in event_types_data["collection"]:
                if event_type_name.lower() in event_type["name"].lower():
                    event_type_uri = event_type["uri"]
                    break

            if not event_type_uri:
                return [
                    types.TextContent(
                        type="text",
                        text=f"❌ No se encontró el tipo de evento: {event_type_name}",
                    )
                ]

            # Obtener horarios disponibles
            days_ahead = arguments.get("days_ahead", 7)
            start_time = datetime.now().isoformat()
            end_time = (datetime.now() + timedelta(days=days_ahead)).isoformat()

            available_times = await client.get_available_times(
                event_type_uri, start_time, end_time
            )

            if not available_times["collection"]:
                return [
                    types.TextContent(
                        type="text",
                        text="❌ No hay horarios disponibles en el rango especificado",
                    )
                ]

            # Filtrar por preferencia de horario
            preferred_time = arguments.get("preferred_time", "").lower()
            best_slots = []

            for slot in available_times["collection"]:
                start_dt = datetime.fromisoformat(
                    slot["start_time"].replace("Z", "+00:00")
                )
                hour = start_dt.hour

                # Clasificar por horario
                time_category = ""
                if 6 <= hour < 12:
                    time_category = "morning"
                elif 12 <= hour < 18:
                    time_category = "afternoon"
                else:
                    time_category = "evening"

                # Dar prioridad si coincide con preferencia
                priority = 1
                if preferred_time and preferred_time in time_category:
                    priority = 0

                best_slots.append(
                    {
                        "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
                        "day_of_week": start_dt.strftime("%A"),
                        "time_category": time_category,
                        "priority": priority,
                        "iso_time": slot["start_time"],
                    }
                )

            # Ordenar por prioridad y tomar los mejores 5
            best_slots.sort(key=lambda x: (x["priority"], x["start_time"]))
            best_slots = best_slots[:5]

            return [
                types.TextContent(
                    type="text",
                    text=f"Mejores horarios disponibles:\n{json.dumps(best_slots, indent=2)}",
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
        return [types.TextContent(type="text", text=f"❌ Error: {str(e)}")]


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
        print("🔧 Configuración del Calendly MCP Server")
        print("\n1. Instalar dependencias:")
        print("   pip install mcp requests")
        print("\n2. Obtener token de Calendly:")
        print("   - Ve a: https://calendly.com/integrations/api_webhooks")
        print("   - Crea un Personal Access Token")
        print("\n3. Configurar variable de entorno:")
        print("   export CALENDLY_ACCESS_TOKEN='tu_token_aqui'")
        print("\n4. Agregar a tu configuración MCP:")
        print(
            json.dumps(
                {
                    "mcpServers": {
                        "calendly": {
                            "command": "python",
                            "args": [__file__],
                            "env": {"CALENDLY_ACCESS_TOKEN": "tu_token_aqui"},
                        }
                    }
                },
                indent=2,
            )
        )
        print("\n5. Ejecutar:")
        print("   python calendly_mcp.py")
    else:
        asyncio.run(main())
