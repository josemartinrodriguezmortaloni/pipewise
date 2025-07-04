# Google Calendar y Gmail Integration Guide

Esta guía detalla cómo usar las integraciones de Google Calendar y Gmail en PipeWise para automatizar la calificación de leads y programación de reuniones.

## Resumen de Funcionalidades

### ✅ Implementado y Funcional

- **Google Calendar OAuth**: Integración completa con endpoints OAuth
- **Gmail OAuth**: Integración completa con endpoints OAuth
- **Frontend configurado**: URLs OAuth actualizadas para coincidir con el backend
- **Herramientas para agentes**: Clases Python para interactuar con APIs de Google
- **Endpoints OAuth**: Rutas `/api/integrations/google_calendar/oauth/start` y `/api/integrations/gmail/oauth/start`

## Configuración OAuth

### 1. Variables de Entorno

El sistema usa las mismas credenciales OAuth de Google para ambas integraciones:

```bash
# .env
GOOGLE_CLIENT_ID=tu_google_client_id
GOOGLE_CLIENT_SECRET=tu_google_client_secret
OAUTH_BASE_URL=https://tu-dominio.com  # Para producción
```

### 2. Scopes Configurados

#### Google Calendar (`google_calendar`)
- `https://www.googleapis.com/auth/calendar.events`
- `https://www.googleapis.com/auth/userinfo.email`

#### Gmail (`gmail`)
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/gmail.compose`
- `https://www.googleapis.com/auth/userinfo.email`

### 3. URLs OAuth

- **Google Calendar**: `/api/integrations/google_calendar/oauth/start`
- **Gmail**: `/api/integrations/gmail/oauth/start`

## Uso en el Frontend

### Estado de las Integraciones

En `integrations-config.ts`:

```typescript
{
  key: "google_calendar",
  name: "Google Calendar",
  status: "active",
  oauthUrl: "/api/integrations/google_calendar/oauth/start",
},
{
  key: "gmail", 
  name: "Gmail",
  status: "active",
  oauthUrl: "/api/integrations/gmail/oauth/start",
}
```

### Conectar Integraciones

1. Usuario hace clic en "Conectar" en la página de integraciones
2. Sistema redirige a Google OAuth
3. Usuario autoriza permisos
4. Sistema guarda tokens OAuth
5. Integraciones quedan disponibles para los agentes

## Herramientas para Agentes

### Google Calendar (`app/agents/tools/google_calendar.py`)

#### Funcionalidades Principales

```python
from app.agents.tools.google_calendar import GoogleCalendarMCPServer

# Inicializar servidor
calendar_server = GoogleCalendarMCPServer(access_token)

# Crear evento
event = await calendar_server.create_event(
    title="Reunión de Calificación",
    description="Llamada con lead potencial",
    start_time="2024-01-15T14:00:00Z",
    end_time="2024-01-15T15:00:00Z",
    attendees=["lead@example.com"],
    location="Google Meet"
)

# Verificar disponibilidad
availability = await calendar_server.check_availability(
    start_time="2024-01-15T14:00:00Z",
    end_time="2024-01-15T15:00:00Z"
)

# Listar calendarios
calendars = await calendar_server.list_calendars()

# Obtener eventos próximos
events = await calendar_server.get_upcoming_events(max_results=10)
```

### Gmail (`app/agents/tools/gmail.py`)

#### Funcionalidades Principales

```python
from app.agents.tools.gmail import GmailMCPServer

# Inicializar servidor
gmail_server = GmailMCPServer(access_token)

# Enviar email
result = await gmail_server.send_email(
    to="lead@example.com",
    subject="Confirmación de Reunión",
    body="Hola, confirmo nuestra reunión...",
    is_html=False
)

# Buscar emails
emails = await gmail_server.search_emails(
    query="is:unread subject:inquiry",
    max_results=10
)

# Obtener mensajes
messages = await gmail_server.get_messages(max_results=5)

# Responder a mensaje
reply = await gmail_server.reply_to_message(
    message_id="message_id_here",
    reply_body="Gracias por tu mensaje..."
)
```

## Flujo de Trabajo: Calificación de Leads

### 1. Detección de Nuevos Leads

```python
# Buscar emails de leads potenciales
lead_emails = await gmail_server.search_emails(
    query="is:unread subject:inquiry OR subject:demo OR subject:interest",
    max_results=10
)
```

### 2. Calificación Automática

```python
def qualify_lead(email_content: str) -> bool:
    """Calificar lead basado en contenido del email"""
    qualification_keywords = [
        "budget", "empresa", "equipo", "implementación", 
        "decisión", "compra", "solución"
    ]
    
    score = sum(1 for keyword in qualification_keywords 
                if keyword in email_content.lower())
    
    return score >= 2
```

### 3. Programación de Reuniones

```python
# Verificar disponibilidad
availability = await calendar_server.check_availability(
    start_time=proposed_time,
    end_time=proposed_end_time
)

if availability["is_available"]:
    # Crear evento
    event = await calendar_server.create_event(
        title=f"Calificación - {lead_name}",
        description="Reunión de calificación de lead",
        start_time=proposed_time,
        end_time=proposed_end_time,
        attendees=[lead_email]
    )
    
    # Enviar confirmación
    await gmail_server.send_email(
        to=lead_email,
        subject="Reunión Programada",
        body=f"Hola {lead_name}, he programado nuestra reunión..."
    )
```

## Ejemplo de Uso Completo

### Script de Demostración

```python
# Ver: app/agents/tools/google_integration_demo.py
from app.agents.tools.google_integration_demo import run_demo

# Ejecutar demo con token OAuth real
await run_demo(access_token="tu_token_oauth_aqui")
```

### Integración con Agentes

```python
# En app/agents/agents.py
from app.agents.tools.google_calendar import create_calendar_event
from app.agents.tools.gmail import send_gmail_email

class LeadQualifierAgent:
    def __init__(self, access_token: str):
        self.access_token = access_token
    
    async def process_lead(self, lead_email: str):
        """Procesar lead calificado"""
        
        # Programar reunión
        meeting = await create_calendar_event(
            access_token=self.access_token,
            title="Calificación de Lead",
            description="Reunión automática programada",
            start_time="2024-01-15T14:00:00Z",
            end_time="2024-01-15T15:00:00Z",
            attendees=[lead_email]
        )
        
        # Enviar email de confirmación
        if meeting["success"]:
            await send_gmail_email(
                access_token=self.access_token,
                to=lead_email,
                subject="Reunión Programada",
                body="Tu reunión ha sido programada exitosamente."
            )
        
        return meeting
```

## Casos de Uso Específicos

### 1. Seguimiento de Leads

```python
# Buscar leads que no han respondido
no_response_leads = await gmail_server.search_emails(
    query="from:leads@company.com older_than:3d",
    max_results=20
)

# Enviar email de seguimiento
for lead in no_response_leads:
    await gmail_server.send_email(
        to=lead["from"],
        subject="Seguimiento - ¿Seguimos interesados?",
        body="Hola, quería hacer un seguimiento..."
    )
```

### 2. Programación Inteligente

```python
# Encontrar próximo slot disponible
def find_next_available_slot(calendar_server):
    """Encontrar próximo slot de 1 hora disponible"""
    current_time = datetime.now()
    
    for days_ahead in range(1, 8):  # Próximos 7 días
        for hour in range(9, 17):  # 9 AM - 5 PM
            slot_start = current_time.replace(
                hour=hour, minute=0, second=0
            ) + timedelta(days=days_ahead)
            
            slot_end = slot_start + timedelta(hours=1)
            
            availability = await calendar_server.check_availability(
                start_time=slot_start.isoformat(),
                end_time=slot_end.isoformat()
            )
            
            if availability["is_available"]:
                return slot_start, slot_end
    
    return None, None
```

### 3. Análisis de Emails

```python
# Analizar emails para insights
def analyze_lead_emails(messages):
    """Analizar emails para extraer insights"""
    insights = {
        "industries": [],
        "company_sizes": [],
        "pain_points": [],
        "urgency_levels": []
    }
    
    for message in messages:
        body = message.get("body", "").lower()
        
        # Detectar industria
        if "healthcare" in body or "hospital" in body:
            insights["industries"].append("healthcare")
        elif "finance" in body or "bank" in body:
            insights["industries"].append("finance")
        
        # Detectar tamaño de empresa
        if "enterprise" in body or "corporation" in body:
            insights["company_sizes"].append("enterprise")
        elif "startup" in body or "small business" in body:
            insights["company_sizes"].append("small")
        
        # Detectar nivel de urgencia
        if "urgent" in body or "asap" in body:
            insights["urgency_levels"].append("high")
        elif "exploring" in body or "considering" in body:
            insights["urgency_levels"].append("low")
    
    return insights
```

## Mejores Prácticas

### 1. Gestión de Tokens OAuth

- Almacenar tokens de forma segura en la base de datos
- Implementar refresh automático de tokens
- Manejar errores de autenticación adecuadamente

### 2. Rate Limiting

- Respetar límites de API de Google (Gmail: 250 quota units/user/second)
- Implementar retry con backoff exponencial
- Monitorear uso de quota

### 3. Privacidad y Seguridad

- Solo solicitar permisos necesarios
- Cifrar tokens almacenados
- Auditar acceso a datos sensibles
- Cumplir con GDPR/CCPA

### 4. Experiencia del Usuario

- Proporcionar feedback claro durante OAuth
- Manejar errores de forma amigable
- Permitir desconexión fácil de integraciones

## Próximos Pasos

### Funcionalidades Adicionales

1. **Google Drive Integration**: Para almacenar documentos de leads
2. **Google Sheets Integration**: Para reportes y análisis
3. **Google Meet Integration**: Para crear enlaces de reuniones automáticamente
4. **Advanced Email Templates**: Plantillas personalizables para diferentes tipos de leads

### Optimizaciones

1. **Caching**: Cachear datos de calendario y emails para mejor performance
2. **Batch Operations**: Procesar múltiples operaciones en lotes
3. **Webhooks**: Recibir notificaciones en tiempo real de cambios
4. **AI Enhancement**: Usar OpenAI para análisis más sofisticado de emails

## Solución de Problemas

### Errores Comunes

1. **Token Expired**: Implementar refresh automático
2. **Insufficient Permissions**: Verificar scopes OAuth
3. **Rate Limiting**: Implementar retry con backoff
4. **API Quota Exceeded**: Monitorear y optimizar uso

### Logs y Debugging

```python
import logging

# Configurar logging para debug
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Los servidores ya incluyen logging detallado
calendar_server = GoogleCalendarMCPServer(access_token)
gmail_server = GmailMCPServer(access_token)
```

¡Las integraciones de Google Calendar y Gmail están completamente implementadas y listas para usar! 🚀 