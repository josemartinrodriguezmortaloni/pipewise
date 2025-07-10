# PRD: Integración de Pipedream MCPs con Agentes de IA

## Introducción/Overview

Este documento define los requisitos para integrar completamente los MCPs (Model Context Protocol) de Pipedream con los agentes de IA de PipeWise, reemplazando las herramientas locales existentes (excepto Supabase) con herramientas MCP específicas por agente, incluyendo manejo robusto de errores, autenticación OAuth por usuario, y testing exhaustivo.

### Problema que Resuelve
Actualmente los agentes de IA utilizan herramientas locales limitadas, lo que restringe su capacidad de interactuar con servicios externos como Calendly, CRMs, email, y redes sociales. La integración con Pipedream MCPs proporcionará acceso a 2,700+ APIs y 10,000+ herramientas directamente desde los agentes.

## Objetivos

1. **Integración Específica por Agente**: Asignar servicios MCP específicos a cada agente según su función
2. **Manejo Robusto de Errores**: Implementar fallbacks y reintentos automáticos con mensajes de error claros
3. **Autenticación OAuth**: Integrar con el sistema OAuth existente para credenciales por usuario
4. **Reemplazo de Herramientas**: Sustituir herramientas locales por MCPs (manteniendo Supabase)
5. **Observabilidad**: Implementar logging y alertas para monitoreo del sistema
6. **Testing Completo**: Crear tests unitarios e integración end-to-end

## User Stories

### US1: Coordinator con Herramientas de Comunicación
**Como** coordinator agent, **quiero** acceder a herramientas de email (SendGrid) y redes sociales (Twitter) via MCP **para que** pueda comunicarme efectivamente con prospects a través de múltiples canales.

### US2: Meeting Scheduler con Calendarios
**Como** meeting scheduler agent, **quiero** acceso a Calendly y Google Calendar via MCP **para que** pueda programar reuniones automáticamente sin herramientas locales.

### US3: Lead Administrator con CRMs
**Como** lead administrator agent, **quiero** acceso a Pipedrive, Salesforce y Zoho CRM via MCP **para que** pueda gestionar leads en sistemas CRM externos.

### US4: Manejo de Errores Transparente
**Como** usuario, **quiero** recibir mensajes claros cuando un servicio MCP falle **para que** entienda qué está pasando y el sistema se recupere automáticamente.

### US5: Autenticación Seamless
**Como** usuario, **quiero** que mis credenciales OAuth se usen automáticamente para MCPs **para que** no tenga que reautenticarme constantemente.

## Functional Requirements

### FR1: Mapeo de Servicios por Agente
1.1. **Coordinator Agent** debe tener acceso a:
   - SendGrid (email marketing/transaccional)
   - Twitter/X (social media outreach)
   - Herramientas de comunicación general

1.2. **Meeting Scheduler Agent** debe tener acceso a:
   - Calendly (scheduling links y eventos)
   - Google Calendar (gestión de calendarios)
   - Herramientas de scheduling

1.3. **Lead Administrator Agent** debe tener acceso a:
   - Pipedrive (CRM operations)
   - Salesforce (enterprise CRM)
   - Zoho CRM (alternative CRM)
   - Herramientas de gestión de leads

### FR2: Sistema de Manejo de Errores
2.1. El sistema debe detectar cuando una conexión MCP falla
2.2. Debe mostrar mensaje de error: "Ups, hubo un error al conectarse con {nombre_del_mcp}"
2.3. Debe implementar reintentos automáticos con backoff exponencial (1s, 2s, 4s, 8s)
2.4. Debe limitar reintentos a máximo 3 intentos por operación
2.5. Debe mantener logs detallados de fallos para debugging

### FR3: Integración OAuth
3.1. Debe utilizar el sistema OAuth existente en `oauth_integration_manager.py`
3.2. Debe verificar tokens válidos antes de crear conexiones MCP
3.3. Debe manejar refresh de tokens automáticamente
3.4. Debe fallback a modo demo si no hay credenciales válidas

### FR4: Reemplazo de Herramientas Locales
4.1. Debe reemplazar `mark_lead_as_contacted()` con herramientas MCP de CRM
4.2. Debe reemplazar `schedule_meeting_for_lead()` con Calendly/Google Calendar MCPs
4.3. Debe mantener `create_lead_in_database()` y otras funciones Supabase
4.4. Debe crear mapeo de funciones locales → funciones MCP

### FR5: Observabilidad y Monitoreo
5.1. Debe implementar logging básico de conexiones exitosas/fallidas
5.2. Debe crear alertas automáticas cuando servicios no están disponibles
5.3. Debe trackear métricas de uso por servicio y agente
5.4. Debe generar health checks periódicos

### FR6: Testing Exhaustivo
6.1. Debe incluir tests unitarios para cada conexión MCP
6.2. Debe incluir tests de integración end-to-end con servicios reales
6.3. Debe verificar manejo de errores y reintentos
6.4. Debe validar autenticación OAuth
6.5. Tests deben ubicarse en carpeta `/tests`

## Non-Goals (Out of Scope)

- No migrar gradualmente: reemplazo completo excepto Supabase
- No mantener herramientas locales como fallback permanente
- No implementar credenciales globales del sistema
- No crear nuevos servicios MCP (solo usar los existentes en Pipedream)
- No modificar la estructura de agentes existente
- No implementar caching avanzado de respuestas MCP

## Design Considerations

### Arquitectura MCP
- Utilizar `MCPServerSse` para conexiones Pipedream
- Implementar factory pattern para creación de servidores MCP por agente
- Mantener configuración centralizada en `pipedream_mcp.py`

### Error Handling Strategy
- Circuit breaker pattern para servicios que fallan repetidamente
- Exponential backoff con jitter para reintentos
- Fallback graceful a funcionalidad limitada cuando sea posible

### OAuth Integration
- Extender `oauth_integration_manager.py` para soportar MCPs
- Crear método `get_mcp_credentials(user_id, service_name)`
- Implementar token refresh automático

## Technical Considerations

### Dependencias
- Mantener dependencia de `agents` SDK de OpenAI
- Utilizar `PipedreamMCPClient` existente
- Integrar con sistema Supabase actual
- Requerir configuración OAuth válida por usuario

### Performance
- Implementar connection pooling para MCPs
- Usar cache de 5 minutos para health checks
- Timeout de 30 segundos para operaciones MCP

### Security
- Validar tokens OAuth antes de cada operación MCP
- No logging de credenciales en logs
- Encriptar credenciales en storage si es necesario

## Success Metrics

### Funcionalidad
- ✅ 100% de herramientas locales reemplazadas (excepto Supabase)
- ✅ Todos los agentes pueden usar sus MCPs asignados
- ✅ Manejo de errores funciona correctamente

### Reliability
- ✅ 95% de operaciones MCP exitosas
- ✅ Tiempo de recuperación < 10 segundos en fallos
- ✅ 0 fallos críticos en autenticación OAuth

### Testing
- ✅ 100% coverage en tests unitarios para MCPs
- ✅ Tests end-to-end pasan con servicios reales
- ✅ Tests de error handling cubren todos los casos

### Observabilidad
- ✅ Logs estructurados para todas las operaciones MCP
- ✅ Alertas funcionando para servicios caídos
- ✅ Health checks reportando estado correcto

## Open Questions

1. **Rate Limiting**: ¿Cómo manejar límites de API de servicios externos?
2. **User Onboarding**: ¿Cómo guiar a usuarios para conectar sus cuentas OAuth?
3. **Service Priorities**: ¿Qué servicios son críticos vs opcionales?
4. **Monitoring Dashboard**: ¿Necesitamos UI para ver estado de MCPs?
5. **Development Environment**: ¿Cómo testing en dev sin afectar cuentas reales?

## Implementation Plan

### Fase 1: Infraestructura Base (Semanas 1-2)
- Refactorizar `create_mcp_servers_for_user()` en `agents.py`
- Implementar factory de MCPs por agente
- Integrar con OAuth manager existente
- Crear sistema base de error handling

### Fase 2: Integración por Agente (Semanas 3-4)
- Coordinator: SendGrid + Twitter MCPs
- Meeting Scheduler: Calendly + Google Calendar MCPs  
- Lead Administrator: CRM MCPs (Pipedrive, Salesforce, Zoho)
- Reemplazar herramientas locales correspondientes

### Fase 3: Testing y Observabilidad (Semana 5)
- Implementar tests unitarios completos
- Crear tests de integración end-to-end
- Agregar logging y alertas
- Health checks y monitoring

### Fase 4: Refinamiento y Optimización (Semana 6)
- Performance tuning
- Error handling refinement
- Documentation y user guides
- Production deployment preparation 