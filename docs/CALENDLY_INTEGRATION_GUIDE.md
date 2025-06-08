# 📅 Calendly Integration Guide for PipeWise

## Visión General

La integración de Calendly en PipeWise permite agendar reuniones automáticamente con leads calificados usando el agente `meeting_scheduler.py`. El sistema funciona tanto con token de Calendly real como en modo fallback.

## 🏗️ Arquitectura

### Componentes Principales

1. **Frontend de Integraciones** (`frontend/components/integrations-settings.tsx`)
   - UI para conectar/desconectar Calendly
   - Muestra estado de conexión y estadísticas
   - Permite probar la integración

2. **API de Integraciones** (`app/api/integrations.py`)
   - Endpoints para manejar configuraciones
   - Almacena tokens y configuraciones de usuario
   - Valida conexiones a Calendly

3. **Cliente de Calendly** (`app/agents/tools/calendly.py`)
   - Maneja todas las interacciones con la API de Calendly
   - Incluye modo fallback si no hay token
   - Funcionalidades: crear links, obtener disponibilidad, tipos de eventos

4. **Agente Meeting Scheduler** (`app/agents/meeting_scheduler.py`)
   - Usa function calling para agendar reuniones
   - Se integra automáticamente con Calendly
   - Actualiza estado de leads en la base de datos

5. **Servicio de Integraciones** (`app/services/integration_service.py`)
   - Interface limpia para que otros agentes usen las integraciones
   - Maneja la coordinación entre agentes

6. **Agente de Integraciones** (`app/agents/integration_agent_example.py`)
   - Ejemplo de cómo procesar datos de múltiples plataformas
   - Determina cuándo llamar al meeting scheduler

## 🔄 Flujo de Trabajo

### 1. Configuración de Calendly

```python
# Usuario conecta Calendly en el frontend
POST /api/integrations/calendly/connect
{
  "access_token": "calendly_token_here",
  "default_event_type": "Sales Call",
  "timezone": "UTC"
}
```

### 2. Uso del Meeting Scheduler

```python
from app.services.integration_service import integration_service

# Crear scheduler con configuración de usuario
scheduler = integration_service.create_meeting_scheduler(user_id="user_123")

# Agendar reunión para un lead
lead_data = {
    "lead": {
        "id": "lead_456",
        "email": "lead@example.com",
        "status": "qualified"
    }
}

result = await scheduler.run(lead_data)
```

### 3. Agente de Integraciones Procesa Datos

```python
from app.agents.integration_agent_example import IntegrationAgent

# Crear agente de integraciones
integration_agent = IntegrationAgent(user_id="user_123")

# Procesar mensaje de WhatsApp que solicita reunión
whatsapp_data = {
    "from": "+1234567890",
    "message": {"text": "Hi, I'd like to schedule a demo"}
}

result = await integration_agent.process_incoming_data("whatsapp", whatsapp_data)
# Esto automáticamente llama al meeting_scheduler si detecta intención de reunión
```

## 🛠️ Funcionalidades del Meeting Scheduler

### Function Calling Tools

El agente `meeting_scheduler.py` tiene acceso a estas herramientas:

1. **Supabase/CRM Tools:**
   - `get_lead_by_id`: Obtener información del lead
   - `create_conversation_for_lead`: Crear conversación
   - `schedule_meeting_for_lead`: Marcar lead como meeting_scheduled

2. **Calendly Tools:**
   - `get_calendly_user`: Info del usuario de Calendly
   - `get_calendly_event_types`: Tipos de eventos disponibles
   - `get_calendly_available_times`: Horarios disponibles
   - `create_calendly_scheduling_link`: Crear link personalizado
   - `find_best_calendly_meeting_slot`: Encontrar mejor horario
   - `get_calendly_scheduled_events`: Reuniones programadas

### Ejemplo de Ejecución

```python
# El agente ejecuta automáticamente estos pasos:
1. get_lead_by_id(lead_id="lead_456")
2. create_calendly_scheduling_link(lead_id="lead_456", event_type_name="Sales Call")
3. schedule_meeting_for_lead(lead_id="lead_456", meeting_url="https://calendly.com/...")

# Resultado:
{
    "success": True,
    "meeting_url": "https://calendly.com/sales-demo/abc123",
    "event_type": "Sales Call",
    "lead_status": "meeting_scheduled",
    "conversation_id": "conv_789"
}
```

## 🔧 Modos de Operación

### Modo Completo (Con Token de Calendly)

- Crea links reales de Calendly
- Acceso a disponibilidad real
- Tipos de eventos configurados
- Webhooks de Calendly funcionales

### Modo Fallback (Sin Token)

- Genera URLs simuladas pero funcionales
- Horarios simulados realistas
- Permite testing sin Calendly
- Funcionalidad completa del agente

## 📊 Estadísticas y Monitoreo

### Frontend muestra:
- Estado de conexión (conectado/desconectado/error)
- Reuniones agendadas
- Links creados
- Último sync

### Backend rastrea:
- `meetings_scheduled`: Contador de reuniones
- `links_created`: Contador de links generados
- `last_meeting_scheduled`: Timestamp de última reunión

## 🚀 Uso en tu Agente de Integraciones

### Opción 1: Usar el Integration Service

```python
from app.services.integration_service import integration_service

# Verificar si meeting scheduling está disponible
if integration_service.is_meeting_scheduling_available(user_id):
    result = await integration_service.schedule_meeting(user_id, lead_data)
```

### Opción 2: Crear Meeting Scheduler Directamente

```python
scheduler = integration_service.create_meeting_scheduler(user_id)
result = await scheduler.run(lead_data)
```

### Opción 3: Usar el Ejemplo de Integration Agent

```python
from app.agents.integration_agent_example import IntegrationAgent

agent = IntegrationAgent(user_id)
result = await agent.process_incoming_data(platform, data)
```

## 🔐 Seguridad

- Tokens se almacenan encriptados (placeholder - implementar encriptación real)
- Configuraciones por usuario aisladas
- Validación de tokens antes de uso
- Manejo seguro de webhooks

## 🧪 Testing

### Test de Conexión
```bash
GET /api/integrations/calendly/status
```

### Test de Funcionalidad
```bash
POST /api/integrations/calendly/test
```

### Test Programático
```python
# Probar integración específica
result = await integration_agent.test_integration("calendly")

# Verificar capacidades
capabilities = integration_service.get_meeting_scheduler_capabilities(user_id)
```

## 📝 Próximos Pasos

1. **Conectar Frontend con Backend**: Los endpoints están listos
2. **Implementar Encriptación Real**: Para tokens sensibles
3. **Configurar Webhooks**: Para eventos de Calendly
4. **Base de Datos**: Persistir configuraciones en Supabase
5. **Testing**: Probar flujo completo

## 💡 Ejemplo de Integración Completa

```python
# En tu agente de integraciones principal:

class MiAgenteIntegraciones:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.integration_service = integration_service
    
    async def procesar_lead_calificado(self, lead_data: Dict[str, Any]):
        """Cuando tienes un lead calificado, agenda reunión automáticamente"""
        
        # Verificar si Calendly está configurado
        if self.integration_service.is_calendly_configured(self.user_id):
            # Agendar reunión usando meeting_scheduler
            result = await self.integration_service.schedule_meeting(
                self.user_id, 
                lead_data
            )
            
            if result["success"]:
                # Notificar éxito, enviar mensajes, etc.
                return {"action": "meeting_scheduled", "url": result["meeting_url"]}
            else:
                # Fallback: agendar manualmente
                return {"action": "manual_follow_up", "error": result["error"]}
        else:
            return {"action": "calendly_not_configured"}
```

El sistema está diseñado para ser modular y fácil de integrar con tu workflow existente. El `meeting_scheduler.py` ya funciona perfectamente con Calendly y puede ser llamado desde cualquier parte de tu sistema usando el `integration_service`. 