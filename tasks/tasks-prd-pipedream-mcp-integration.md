## Relevant Files

- `app/ai_agents/agents.py` - Updated with imports for agent-specific MCP server functions from refactored manager
- `app/ai_agents/tools/pipedream_mcp.py` - Existing Pipedream MCP client that needs enhancement for agent-specific MCPs
- `app/api/oauth_integration_manager.py` - OAuth manager that needs extension for MCP credential handling
- `app/ai_agents/mcp/__init__.py` - MCP module initialization with lazy imports and version info
- `app/ai_agents/mcp/mcp_server_manager.py` - Refactored to use AgentMCPFactory with agent-specific helper functions
- `app/ai_agents/mcp/agent_mcp_factory.py` - Factory pattern implementation with AgentType enum and specific MCP mappings per agent
- `app/ai_agents/mcp/error_handler.py` - Error handling and retry logic for MCP operations
- `app/ai_agents/mcp/health_monitor.py` - Health checking and monitoring for MCP services
- `app/core/config.py` - Configuration updates for MCP settings and timeouts
- `tests/test_mcp_integration.py` - Unit tests for MCP integration functionality
- `tests/test_agent_mcp_factory.py` - Unit tests for agent MCP factory
- `tests/test_mcp_error_handling.py` - Unit tests for MCP error handling and retry logic
- `tests/test_mcp_oauth_integration.py` - Unit tests for OAuth integration with MCPs
- `tests/integration/test_mcp_end_to_end.py` - End-to-end integration tests with real services
- `tests/integration/test_agent_workflows_with_mcp.py` - Integration tests for complete agent workflows using MCPs

### Notes

- Unit tests should be placed in the `/tests` directory as specified in the PRD requirements
- Integration tests with real services should be in `/tests/integration/` subdirectory
- Use `pytest` to run tests following the project's testing conventions
- MCP-related modules should be organized in `app/ai_agents/mcp/` for better structure

## Tasks

- [x] 1.0 Refactorizar Infraestructura MCP Base
  - [x] 1.1 Crear directorio `app/ai_agents/mcp/` y archivo `__init__.py`
  - [x] 1.2 Extraer lógica de creación de MCP de `agents.py` a módulo separado
  - [x] 1.3 Crear `agent_mcp_factory.py` con factory pattern para MCPs por agente
  - [x] 1.4 Refactorizar `create_mcp_servers_for_user()` para usar el nuevo factory
  - [x] 1.5 Actualizar `pipedream_mcp.py` con métodos específicos para cada tipo de agente
  - [x] 1.6 Agregar configuración de timeouts y connection pooling en `core/config.py`
  - [x] 1.7 Crear clase base `BaseMCPServer` para funcionalidad común

- [x] 2.0 Implementar Sistema de Manejo de Errores y Reintentos
  - [x] 2.1 Crear `mcp/error_handler.py` con clases de excepciones específicas de MCP
  - [x] 2.2 Implementar función de backoff exponencial con jitter (1s, 2s, 4s, 8s)
  - [x] 2.3 Crear decorador `@retry_mcp_operation` para reintentos automáticos (máximo 3 intentos)
  - [x] 2.4 Implementar circuit breaker pattern para servicios que fallan repetidamente
  - [x] 2.5 Crear función para generar mensajes de error user-friendly "Ups, hubo un error al conectarse con {nombre_del_mcp}"
  - [x] 2.6 Agregar logging detallado para debugging de fallos MCP
  - [x] 2.7 Integrar error handling en todos los métodos de conexión MCP

- [x] 3.0 Integrar MCP con Sistema OAuth Existente
  - [x] 3.1 Crear función en `mcp/oauth_integration.py` para mapear tokens OAuth a credenciales MCP
  - [x] 3.2 Modificar `agent_mcp_factory.py` para usar tokens reales en lugar de demo data
  - [x] 3.3 Implementar función `get_mcp_credentials_for_user(user_id, service_name)` que obtiene tokens de Supabase
  - [x] 3.4 Crear middleware para validar tokens OAuth antes de crear conexiones MCP
  - [x] 3.5 Agregar función para refrescar tokens OAuth expirados automáticamente
  - [x] 3.6 Implementar logging de uso de integraciones OAuth para analytics
  - [x] 3.7 Crear endpoint API para verificar estado de integraciones de usuario

- [ ] 4.0 Implementar MCPs Específicos por Agente
  - [ ] 4.1 Crear MCPs para Coordinator Agent (SendGrid + Twitter)
    - [ ] 4.1.1 Configurar SendGrid MCP para email marketing/transaccional
    - [ ] 4.1.2 Configurar Twitter/X MCP para social media outreach
    - [ ] 4.1.3 Reemplazar herramientas locales de comunicación con MCPs
  - [ ] 4.2 Crear MCPs para Meeting Scheduler Agent (Calendly + Google Calendar)
    - [ ] 4.2.1 Configurar Calendly MCP para scheduling links y eventos
    - [ ] 4.2.2 Configurar Google Calendar MCP para gestión de calendarios
    - [ ] 4.2.3 Reemplazar `schedule_meeting_for_lead()` con herramientas MCP
  - [ ] 4.3 Crear MCPs para Lead Administrator Agent (Pipedrive + Salesforce + Zoho)
    - [ ] 4.3.1 Configurar Pipedrive MCP para CRM operations
    - [ ] 4.3.2 Configurar Salesforce MCP para enterprise CRM
    - [ ] 4.3.3 Configurar Zoho CRM MCP para alternative CRM
    - [ ] 4.3.4 Reemplazar `mark_lead_as_contacted()` con herramientas MCP de CRM
  - [ ] 4.4 Actualizar `create_agents_with_proper_mcp_integration()` para usar MCPs específicos
  - [ ] 4.5 Crear mapeo de funciones locales → funciones MCP en documentación
  - [ ] 4.6 Mantener funciones Supabase (`create_lead_in_database()`, etc.) sin cambios

- [ ] 5.0 Crear Sistema de Testing Exhaustivo
  - [ ] 5.1 Crear tests unitarios para MCPs
    - [ ] 5.1.1 Test `test_mcp_integration.py` para funcionalidad básica de integración
    - [ ] 5.1.2 Test `test_agent_mcp_factory.py` para factory pattern y creación de MCPs
    - [ ] 5.1.3 Test `test_mcp_error_handling.py` para error handling y reintentos
    - [ ] 5.1.4 Test `test_mcp_oauth_integration.py` para integración OAuth
  - [ ] 5.2 Crear tests de integración end-to-end
    - [ ] 5.2.1 Test `integration/test_mcp_end_to_end.py` con servicios reales (Pipedream sandbox)
    - [ ] 5.2.2 Test `integration/test_agent_workflows_with_mcp.py` para workflows completos
    - [ ] 5.2.3 Configurar environment variables para testing con servicios reales
  - [ ] 5.3 Crear mocks y fixtures para testing
    - [ ] 5.3.1 Mock responses para cada servicio MCP
    - [ ] 5.3.2 Fixtures de OAuth tokens para testing
    - [ ] 5.3.3 Test data para diferentes escenarios de error
  - [ ] 5.4 Configurar pytest para ejecutar tests con `pytest tests/` y `pytest tests/integration/`
  - [ ] 5.5 Agregar coverage reports para verificar 100% coverage en componentes MCP

- [ ] 6.0 Implementar Observabilidad y Monitoreo
  - [ ] 6.1 Crear `mcp/health_monitor.py` con health checks periódicos (cada 5 minutos)
  - [ ] 6.2 Implementar logging estructurado para todas las operaciones MCP
    - [ ] 6.2.1 Log de conexiones exitosas/fallidas con métricas
    - [ ] 6.2.2 Log de uso por servicio y agente
    - [ ] 6.2.3 Log de errores de autenticación OAuth
  - [ ] 6.3 Crear sistema de alertas automáticas
    - [ ] 6.3.1 Alertas cuando servicios no están disponibles por > 2 minutos
    - [ ] 6.3.2 Alertas de rate limiting en APIs externas
    - [ ] 6.3.3 Alertas de fallos críticos en autenticación OAuth
  - [ ] 6.4 Implementar métricas de performance
    - [ ] 6.4.1 Tiempo de respuesta de operaciones MCP
    - [ ] 6.4.2 Tasa de éxito/fallo por servicio
    - [ ] 6.4.3 Número de reintentos por operación
  - [ ] 6.5 Crear endpoint `/health/mcp` para verificar estado de todos los MCPs
  - [ ] 6.6 Integrar métricas con sistema de logging existente en PipeWise 