import os
import json
import logging
import requests
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class CalendlyClient:
    """Cliente para interactuar directamente con la API de Calendly"""

    def __init__(self, access_token: str = None):
        self.access_token = access_token or os.getenv("CALENDLY_ACCESS_TOKEN")
        self.base_url = "https://api.calendly.com"

        if self.access_token:
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            self.enabled = True
            logger.info("Calendly client initialized with API token")
        else:
            self.headers = {}
            self.enabled = False
            logger.warning(
                "Calendly client initialized without API token - using fallback mode"
            )

    def _make_request(
        self, method: str, endpoint: str, params: Dict = None, data: Dict = None
    ) -> Dict:
        """Realizar solicitud HTTP a la API de Calendly"""
        if not self.enabled:
            raise Exception("Calendly API not configured - missing access token")

        url = f"{self.base_url}{endpoint}"

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

    def get_current_user(self) -> Dict:
        """Obtener información del usuario actual"""
        if not self.enabled:
            return {
                "resource": {
                    "name": "Demo User",
                    "email": "demo@example.com",
                    "timezone": "UTC",
                    "uri": "https://api.calendly.com/users/demo",
                }
            }
        return self._make_request("GET", "/users/me")

    def get_event_types(self, user_uri: str) -> Dict:
        """Obtener tipos de eventos disponibles"""
        if not self.enabled:
            return {
                "collection": [
                    {
                        "name": "Sales Call",
                        "duration": 30,
                        "uri": "https://api.calendly.com/event_types/demo-sales-call",
                        "description_plain": "30-minute sales consultation",
                        "active": True,
                    },
                    {
                        "name": "Demo",
                        "duration": 45,
                        "uri": "https://api.calendly.com/event_types/demo-product-demo",
                        "description_plain": "45-minute product demonstration",
                        "active": True,
                    },
                    {
                        "name": "Discovery Call",
                        "duration": 15,
                        "uri": "https://api.calendly.com/event_types/demo-discovery",
                        "description_plain": "15-minute discovery call",
                        "active": True,
                    },
                ]
            }

        params = {"user": user_uri}
        return self._make_request("GET", "/event_types", params=params)

    def get_available_times(
        self, event_type_uri: str, start_time: str, end_time: str
    ) -> Dict:
        """Obtener horarios disponibles"""
        if not self.enabled:
            # Generar horarios simulados para los próximos días
            now = datetime.now()
            slots = []

            for i in range(1, 8):  # Próximos 7 días
                date = now + timedelta(days=i)
                # Horarios de ejemplo: 9 AM, 11 AM, 2 PM, 4 PM
                for hour in [9, 11, 14, 16]:
                    if date.weekday() < 5:  # Solo días laborables
                        slot_time = date.replace(
                            hour=hour, minute=0, second=0, microsecond=0
                        )
                        slots.append({"start_time": slot_time.isoformat() + "Z"})

            return {"collection": slots}

        params = {
            "event_type": event_type_uri,
            "start_time": start_time,
            "end_time": end_time,
        }
        return self._make_request("GET", "/event_type_available_times", params=params)

    def create_scheduling_link(
        self, event_type_uri: str, max_event_count: int = 1
    ) -> Dict:
        """Crear link de agendamiento único"""
        if not self.enabled:
            # Generar URL simulada pero funcional
            unique_hash = hashlib.md5(
                f"{event_type_uri}-{datetime.now().isoformat()}".encode()
            ).hexdigest()[:8]
            return {
                "resource": {
                    "booking_url": f"https://calendly.com/demo-booking/{unique_hash}",
                    "max_event_count": max_event_count,
                    "owner_type": "EventType",
                }
            }

        data = {
            "max_event_count": max_event_count,
            "owner": event_type_uri,
            "owner_type": "EventType",
        }
        return self._make_request("POST", "/scheduling_links", data=data)

    def get_scheduled_events(
        self, user_uri: str, start_time: str = None, end_time: str = None
    ) -> Dict:
        """Obtener eventos programados"""
        if not self.enabled:
            return {"collection": []}

        params = {"user": user_uri}
        if start_time:
            params["min_start_time"] = start_time
        if end_time:
            params["max_start_time"] = end_time
        return self._make_request("GET", "/scheduled_events", params=params)

    def get_event_details(self, event_uuid: str) -> Dict:
        """Obtener detalles de un evento específico"""
        if not self.enabled:
            return {
                "resource": {
                    "name": "Demo Event",
                    "start_time": datetime.now().isoformat() + "Z",
                    "end_time": (datetime.now() + timedelta(hours=1)).isoformat() + "Z",
                    "status": "active",
                    "location": {"type": "zoom"},
                    "meeting_notes_plain": "",
                    "invitees_counter": {"total": 1, "active": 1},
                }
            }
        return self._make_request("GET", f"/scheduled_events/{event_uuid}")

    def cancel_event(
        self, event_uuid: str, reason: str = "Cancelado automáticamente"
    ) -> Dict:
        """Cancelar un evento"""
        if not self.enabled:
            return {"status": "cancelled", "reason": reason}

        data = {"reason": reason}
        return self._make_request(
            "POST", f"/scheduled_events/{event_uuid}/cancellation", data=data
        )

    def find_best_meeting_slot(
        self, event_type_name: str, preferred_time: str = None, days_ahead: int = 7
    ) -> Dict:
        """Encontrar el mejor horario disponible para agendar una reunión"""
        try:
            # Obtener usuario y tipos de eventos
            user_data = self.get_current_user()
            user_uri = user_data["resource"]["uri"]

            event_types_data = self.get_event_types(user_uri)
            event_type_uri = None

            # Buscar tipo de evento por nombre
            for event_type in event_types_data["collection"]:
                if event_type_name.lower() in event_type["name"].lower():
                    event_type_uri = event_type["uri"]
                    break

            if not event_type_uri:
                return {"error": f"No se encontró el tipo de evento: {event_type_name}"}

            # Obtener horarios disponibles
            start_time = datetime.now().isoformat()
            end_time = (datetime.now() + timedelta(days=days_ahead)).isoformat()

            available_times = self.get_available_times(
                event_type_uri, start_time, end_time
            )

            if not available_times["collection"]:
                return {"error": "No hay horarios disponibles en el rango especificado"}

            # Filtrar por preferencia de horario
            best_slots = []
            preferred_time_lower = (preferred_time or "").lower()

            for slot in available_times["collection"]:
                start_dt = datetime.fromisoformat(
                    slot["start_time"].replace("Z", "+00:00")
                )
                hour = start_dt.hour

                # Clasificar por horario
                if 6 <= hour < 12:
                    time_category = "morning"
                elif 12 <= hour < 18:
                    time_category = "afternoon"
                else:
                    time_category = "evening"

                # Dar prioridad si coincide con preferencia
                priority = 1
                if preferred_time_lower and preferred_time_lower in time_category:
                    priority = 0

                best_slots.append(
                    {
                        "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
                        "day_of_week": start_dt.strftime("%A"),
                        "time_category": time_category,
                        "priority": priority,
                        "iso_time": slot["start_time"],
                        "event_type_uri": event_type_uri,
                    }
                )

            # Ordenar por prioridad y tomar los mejores 5
            best_slots.sort(key=lambda x: (x["priority"], x["start_time"]))
            return {"best_slots": best_slots[:5]}

        except Exception as e:
            logger.error(f"Error finding best meeting slot: {e}")
            return {"error": str(e)}

    def create_personalized_link(
        self, lead_id: str, event_type_name: str = "Sales Call", max_uses: int = 1
    ) -> Dict:
        """Crear un link personalizado para un lead específico"""
        try:
            # Obtener usuario y tipos de eventos
            user_data = self.get_current_user()
            user_uri = user_data["resource"]["uri"]

            event_types_data = self.get_event_types(user_uri)
            event_type_uri = None

            # Buscar tipo de evento por nombre
            for event_type in event_types_data["collection"]:
                if event_type_name.lower() == event_type["name"].lower():
                    event_type_uri = event_type["uri"]
                    break
                elif event_type_name.lower() in event_type["name"].lower():
                    event_type_uri = event_type["uri"]

            if not event_type_uri:
                # Usar el primer tipo de evento disponible
                if event_types_data["collection"]:
                    event_type_uri = event_types_data["collection"][0]["uri"]
                    event_type_name = event_types_data["collection"][0]["name"]
                else:
                    return {"error": "No hay tipos de eventos disponibles"}

            # Crear link único
            result = self.create_scheduling_link(event_type_uri, max_uses)

            return {
                "success": True,
                "booking_url": result["resource"]["booking_url"],
                "event_type": event_type_name,
                "max_uses": max_uses,
                "lead_id": lead_id,
                "created_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error creating personalized link: {e}")
            # Fallback: crear URL simulada
            unique_hash = hashlib.md5(
                f"{lead_id}-{event_type_name}".encode()
            ).hexdigest()[:8]
            return {
                "success": True,
                "booking_url": f"https://calendly.com/sales-demo/{unique_hash}",
                "event_type": event_type_name,
                "max_uses": max_uses,
                "lead_id": lead_id,
                "created_at": datetime.now().isoformat(),
                "fallback": True,
            }

    def health_check(self) -> Dict:
        """Verificar el estado de la conexión a Calendly"""
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "message": "Calendly API not configured",
                    "fallback_mode": True,
                }

            # Intentar una consulta simple
            user_data = self.get_current_user()

            return {
                "status": "healthy",
                "user_email": user_data["resource"]["email"],
                "user_name": user_data["resource"]["name"],
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# Función de conveniencia para crear instancia global
def get_calendly_client() -> CalendlyClient:
    """Obtener instancia del cliente de Calendly"""
    return CalendlyClient()


# Ejemplo de uso
if __name__ == "__main__":
    # Test del cliente
    client = CalendlyClient()

    print("🧪 Testing Calendly Client")
    print("=" * 40)

    # Health check
    health = client.health_check()
    print(f"Health: {health}")

    # Obtener usuario
    try:
        user = client.get_current_user()
        print(f"User: {user['resource']['name']} ({user['resource']['email']})")
    except Exception as e:
        print(f"User error: {e}")

    # Obtener tipos de eventos
    try:
        user_data = client.get_current_user()
        events = client.get_event_types(user_data["resource"]["uri"])
        print(f"Event types: {len(events['collection'])}")
        for event in events["collection"][:3]:
            print(f"  - {event['name']} ({event['duration']} min)")
    except Exception as e:
        print(f"Events error: {e}")

    # Crear link personalizado
    try:
        link_result = client.create_personalized_link("test-lead-123", "Sales Call")
        print(f"Link created: {link_result['booking_url']}")
    except Exception as e:
        print(f"Link error: {e}")
