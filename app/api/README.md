# API Documentation - PipeWise CRM with Authentication

Esta documentación describe todas las rutas API disponibles para conectar el frontend con el sistema de autenticación y CRM de PipeWise.

## Estructura General

El sistema está organizado en varios módulos:

- **Authentication (`/auth`)** - Sistema de autenticación con 2FA
- **CRM (`/api`)** - Gestión de leads, oportunidades, contactos y actividades
- **Webhooks (`/webhooks`)** - Webhooks y notificaciones
- **Search (`/search`)** - Búsqueda avanzada y exportación
- **Configuration (`/config`)** - Configuración del frontend

---

## 🔐 Authentication Routes (`/auth`)

### Registro y Login

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/auth/register` | Registrar nuevo usuario |
| `POST` | `/auth/login` | Login de usuario |
| `POST` | `/auth/login/2fa` | Login con código 2FA |
| `POST` | `/auth/logout` | Cerrar sesión |

### Gestión de Tokens

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/auth/refresh` | Renovar token de acceso |
| `GET` | `/auth/validate` | Validar token actual |

### Autenticación de Dos Factores

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/auth/2fa/enable` | Habilitar 2FA |
| `POST` | `/auth/2fa/verify` | Verificar configuración 2FA |
| `POST` | `/auth/2fa/disable` | Deshabilitar 2FA |

### Gestión de Perfil

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/auth/profile` | Obtener perfil del usuario |
| `PUT` | `/auth/profile` | Actualizar perfil |
| `POST` | `/auth/change-password` | Cambiar contraseña |

### Recuperación de Contraseña

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/auth/forgot-password` | Solicitar reset de contraseña |
| `POST` | `/auth/reset-password` | Confirmar reset de contraseña |

### Gestión de Sesiones

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/auth/sessions` | Obtener sesiones activas |
| `POST` | `/auth/sessions/revoke` | Revocar sesión específica |
| `POST` | `/auth/sessions/revoke-all` | Revocar todas las sesiones |

### Administración (Solo Admin)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/auth/admin/users` | Listar usuarios del sistema |
| `PUT` | `/auth/admin/users/{user_id}` | Actualizar usuario |
| `GET` | `/auth/admin/stats` | Estadísticas de autenticación |

### Health Check

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/auth/health` | Health check del sistema de auth |

---

## 📊 CRM Routes (`/api`)

### Gestión de Leads

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/leads` | Listar leads con filtros |
| `POST` | `/api/leads` | Crear nuevo lead |
| `GET` | `/api/leads/{lead_id}` | Obtener lead específico |
| `PUT` | `/api/leads/{lead_id}` | Actualizar lead |
| `DELETE` | `/api/leads/{lead_id}` | Eliminar lead |

**Parámetros de filtro para GET /api/leads:**
- `page` (int): Página actual
- `per_page` (int): Elementos por página
- `status_filter` (str): Filtrar por estado
- `source_filter` (str): Filtrar por fuente
- `owner_filter` (str): Filtrar por propietario
- `search` (str): Búsqueda de texto

### Gestión de Oportunidades

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/opportunities` | Listar oportunidades |
| `POST` | `/api/opportunities` | Crear oportunidad |
| `GET` | `/api/opportunities/{opp_id}` | Obtener oportunidad |
| `PUT` | `/api/opportunities/{opp_id}` | Actualizar oportunidad |
| `DELETE` | `/api/opportunities/{opp_id}` | Eliminar oportunidad |

### Gestión de Contactos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/contacts` | Listar contactos |
| `POST` | `/api/contacts` | Crear contacto |
| `GET` | `/api/contacts/{contact_id}` | Obtener contacto |
| `PUT` | `/api/contacts/{contact_id}` | Actualizar contacto |
| `DELETE` | `/api/contacts/{contact_id}` | Eliminar contacto |

### Gestión de Actividades

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/activities` | Listar actividades |
| `POST` | `/api/activities` | Crear actividad |
| `GET` | `/api/activities/{activity_id}` | Obtener actividad |
| `PUT` | `/api/activities/{activity_id}` | Actualizar actividad |
| `DELETE` | `/api/activities/{activity_id}` | Eliminar actividad |

### Dashboard y Métricas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/dashboard` | Datos del dashboard |
| `GET` | `/api/pipeline` | Datos del pipeline de ventas |

**Parámetros para dashboard:**
- `period` (str): Período de tiempo (7d, 30d, 90d, 1y)

### Reportes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/reports` | Listar reportes |
| `POST` | `/api/reports` | Generar reporte personalizado |

### Administración CRM (Solo Admin)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/admin/users` | Usuarios del sistema CRM |
| `GET` | `/api/admin/stats` | Estadísticas del sistema |

---

## 🔗 Webhooks & Notifications (`/webhooks`)

### Webhooks Entrantes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/webhooks/lead-capture` | Capturar leads desde formularios |
| `POST` | `/webhooks/form-submission` | Webhooks de formularios |
| `POST` | `/webhooks/email-event` | Eventos de email (opens, clicks) |

### Notificaciones

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/webhooks/notifications` | Listar notificaciones |
| `POST` | `/webhooks/notifications` | Crear notificación |
| `PUT` | `/webhooks/notifications/{id}/read` | Marcar como leída |
| `DELETE` | `/webhooks/notifications/{id}` | Eliminar notificación |

**Parámetros para GET notifications:**
- `unread_only` (bool): Solo no leídas
- `page` (int): Página actual
- `per_page` (int): Elementos por página

### Integraciones (Solo Admin)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/webhooks/integrations` | Listar integraciones |
| `POST` | `/webhooks/integrations` | Crear integración |
| `POST` | `/webhooks/trigger/{event_type}` | Disparar evento manual |

---

## 🔍 Search & Export (`/search`)

### Búsqueda Avanzada

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/search/` | Búsqueda avanzada |
| `GET` | `/search/suggestions` | Sugerencias de búsqueda |
| `GET` | `/search/recent` | Búsquedas recientes |

**Parámetros para sugerencias:**
- `q` (str): Query de búsqueda
- `limit` (int): Límite de resultados

### Exportación de Datos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/search/export/leads` | Exportar leads |
| `GET` | `/search/export/opportunities` | Exportar oportunidades |
| `GET` | `/search/export/contacts` | Exportar contactos |

**Parámetros de exportación:**
- `format` (str): Formato (csv, json, xlsx)
- `status_filter` (str): Filtro de estado
- `date_from` (date): Fecha desde
- `date_to` (date): Fecha hasta

### Importación de Datos (Manager/Admin)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/search/import/leads` | Importar leads |
| `GET` | `/search/import/status/{import_id}` | Estado de importación |

---

## ⚙️ Configuration (`/config`)

### Configuración del Frontend

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/config/routes` | Rutas disponibles por rol |
| `GET` | `/config/frontend` | Configuración completa |
| `GET` | `/config/permissions` | Permisos del usuario |
| `GET` | `/config/features` | Funcionalidades disponibles |

---

## 🏥 Health Checks

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Endpoint raíz con información |
| `GET` | `/health` | Health check completo |
| `GET` | `/metrics` | Métricas del sistema |

---

## 🔒 Autenticación

Todas las rutas (excepto `/auth/register`, `/auth/login`, `/webhooks/lead-capture` y health checks) requieren autenticación.

### Headers Requeridos

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Manejo de Errores

Los errores se devuelven en formato JSON:

```json
{
  "error": "Error message",
  "detail": "Detailed description",
  "status_code": 400,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Códigos de Estado Comunes

- `200` - Éxito
- `201` - Creado
- `400` - Error de validación
- `401` - No autenticado
- `403` - Sin permisos
- `404` - No encontrado
- `429` - Rate limit excedido
- `500` - Error interno del servidor

---

## 📱 Integración con Frontend

### Configuración Inicial

1. Obtener configuración del frontend:
```javascript
GET /config/frontend
```

2. Verificar token de autenticación:
```javascript
GET /auth/validate
```

3. Obtener rutas disponibles:
```javascript
GET /config/routes
```

### Manejo de Sesiones

```javascript
// Login
POST /auth/login
{
  "email": "user@example.com",
  "password": "password"
}

// Refresh token
POST /auth/refresh
{
  "refresh_token": "refresh_token_here"
}

// Logout
POST /auth/logout
```

### Gestión de Datos

```javascript
// Crear lead
POST /api/leads
{
  "name": "John Doe",
  "email": "john@example.com",
  "company": "Acme Corp"
}

// Buscar
POST /search/
{
  "query": "john doe",
  "entity_types": ["leads", "contacts"]
}

// Exportar
GET /search/export/leads?format=csv&status_filter=qualified
```

### WebSockets (Futuro)

Para notificaciones en tiempo real, se puede implementar WebSocket en:
```
ws://localhost:8000/ws/notifications
```

---

## 🚀 Ejemplos de Uso

### Flujo de Autenticación Completo

```javascript
// 1. Login
const loginResponse = await fetch('/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password'
  })
});

const { access_token, refresh_token, requires_2fa } = await loginResponse.json();

// 2. Si requiere 2FA
if (requires_2fa) {
  const tfaResponse = await fetch('/auth/login/2fa', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'X-2FA-Token': temp_token 
    },
    body: JSON.stringify({
      email: 'user@example.com',
      password: 'password',
      totp_code: '123456'
    })
  });
}

// 3. Usar token para requests
const leadsResponse = await fetch('/api/leads', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  }
});
```

### Gestión de Leads

```javascript
// Crear lead
const createLead = async (leadData) => {
  const response = await fetch('/api/leads', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(leadData)
  });
  return response.json();
};

// Obtener leads con filtros
const getLeads = async (filters = {}) => {
  const params = new URLSearchParams(filters);
  const response = await fetch(`/api/leads?${params}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};
```

### Rate Limiting

El sistema implementa rate limiting por rol:

- **User**: 60 req/min
- **Manager**: 120 req/min  
- **Admin**: 300 req/min

Cuando se excede el límite, se devuelve código `429` con headers:
```
X-Rate-Limit-Limit: 60
X-Rate-Limit-Remaining: 0
X-Rate-Limit-Reset: 1640995200
Retry-After: 3600
```

---

## 🧪 Testing

Para probar las rutas, usar herramientas como:

- **Postman**: Importar collection desde `/docs`
- **curl**: Ejemplos en documentación interactiva
- **Frontend**: Integración directa con React/Vue/Angular

### Documentación Interactiva

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 📝 Notas Importantes

1. **Seguridad**: Todas las rutas implementan validación de permisos
2. **Rate Limiting**: Límites diferentes por rol de usuario
3. **CORS**: Configurado para dominios específicos
4. **Logging**: Todos los requests se loggean para auditoría
5. **Background Tasks**: Tareas pesadas se ejecutan en background
6. **Caching**: Redis para sesiones y rate limiting
7. **Validation**: Validación estricta con Pydantic
8. **Error Handling**: Manejo centralizado de errores

Esta documentación se actualiza automáticamente con cada cambio en las rutas. 