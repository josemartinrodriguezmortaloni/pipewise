# 🚀 Guía de Configuración - Integración Leads Frontend/Backend

Esta guía te ayudará a configurar y probar la integración completa entre el frontend Next.js y el backend FastAPI para mostrar leads usando el componente DataTable.

## 📋 Resumen de la Implementación

### Backend (FastAPI)
- ✅ **Endpoint GET /api/leads** - Lista leads con filtros y paginación
- ✅ **Autenticación** - Middleware de autenticación (pendiente activar)
- ✅ **Datos de demo** - Leads de ejemplo para testing
- ✅ **CORS configurado** - Para requests desde el frontend

### Frontend (Next.js)
- ✅ **Hook useLeads** - Manejo de estado y polling automático
- ✅ **Página /leads** - Integración con DataTable component
- ✅ **Mapeo de datos** - Transformación Lead → TableRow
- ✅ **Tiempo real** - Actualización cada 5 segundos
- ✅ **Manejo de errores** - Estados de loading y error

## 🛠️ Configuración

### 1. Instalar Dependencias del Backend

```bash
cd pipewise
pip install fastapi uvicorn python-multipart
```

### 2. Instalar Dependencias del Frontend

```bash
cd frontend
npm install
# o
pnpm install
```

### 3. Configurar Variables de Entorno (Opcional)

Crear `.env` en la raíz del proyecto:

```env
# Backend
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Supabase (opcional para demo)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## 🚀 Iniciar los Servicios

### Terminal 1: Backend (FastAPI)

```bash
# Opción 1: Usar el script
python start-backend.py

# Opción 2: Directamente con uvicorn
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

El backend estará disponible en: `http://localhost:8000`

### Terminal 2: Frontend (Next.js)

```bash
cd frontend
npm run dev
# o
pnpm dev
```

El frontend estará disponible en: `http://localhost:3000`

## 🧪 Probar la Integración

### 1. Verificar Backend

Abrir `http://localhost:8000/docs` para ver la documentación Swagger.

Probar el endpoint manualmente:
```bash
curl http://localhost:8000/api/leads
```

Deberías ver una respuesta JSON con leads de demo:
```json
{
  "leads": [
    {
      "id": "demo_lead_1",
      "name": "John Smith",
      "email": "john.smith@acme.com",
      "company": "Acme Corporation",
      "status": "new"
    }
  ],
  "total": 3,
  "page": 1,
  "per_page": 50
}
```

### 2. Verificar Frontend

1. Ir a `http://localhost:3000/leads`
2. Deberías ver la tabla DataTable con 3 leads de demo
3. La tabla se actualiza automáticamente cada 5 segundos
4. Puedes usar todas las funciones del DataTable (filtros, paginación, etc.)

### 3. Verificar Proxy

El frontend hace requests a `/api/leads` que se redirigen automáticamente al backend en `http://localhost:8000/api/leads` gracias a la configuración en `next.config.ts`.

## 📊 Estructura de Datos

### Lead (Backend)
```typescript
interface Lead {
  id: string
  name: string
  email: string
  company: string
  phone?: string
  status: string
  qualified: boolean
  contacted: boolean
  meeting_scheduled: boolean
  source?: string
  owner_id?: string
  created_at: string
}
```

### TableRow (Frontend)
```typescript
interface TableRow {
  id: number          // Índice numérico
  header: string      // lead.name
  type: string        // lead.company
  status: string      // Estado procesado
  target: string      // lead.email
  limit: string       // lead.phone
  reviewer: string    // lead.owner_id procesado
}
```

## 🔧 Funcionalidades Implementadas

### Backend
- [x] **GET /api/leads** - Listado con filtros
- [x] **Paginación** - page, per_page, total_pages
- [x] **Filtros** - status_filter, source_filter, owner_filter
- [x] **Búsqueda** - search parameter
- [x] **Datos demo** - 3 leads de ejemplo
- [x] **CORS** - Configurado para localhost:3000

### Frontend
- [x] **Hook useLeads** - Gestión de estado reactivo
- [x] **Polling automático** - Actualización cada 5s
- [x] **Loading states** - Indicadores de carga
- [x] **Error handling** - Manejo de errores de red
- [x] **Mapeo de datos** - Lead → TableRow
- [x] **Integración DataTable** - Tabla completa funcional

## 🎯 Próximos Pasos

### Autenticación
- [ ] Implementar login/logout en frontend
- [ ] Activar middleware de autenticación en backend
- [ ] Gestión de tokens JWT

### Funcionalidades Adicionales
- [ ] **WebSocket** - Reemplazar polling por suscripción push
- [ ] **Filtros avanzados** - UI para filtros en la tabla
- [ ] **Paginación real** - Integrar con paginación del DataTable
- [ ] **CRUD completo** - Crear, editar, eliminar leads
- [ ] **Optimistic updates** - Actualizaciones optimistas

### Producción
- [ ] **Variables de entorno** - Configuración por ambiente
- [ ] **Error boundaries** - Manejo de errores robusto
- [ ] **Testing** - Tests e2e para la integración
- [ ] **Deployment** - Docker, CI/CD

## 🐛 Troubleshooting

### Backend no inicia
```bash
# Verificar que FastAPI esté instalado
pip install fastapi uvicorn

# Verificar puerto disponible
lsof -i :8000
```

### Frontend no conecta al backend
1. Verificar que el backend esté corriendo en puerto 8000
2. Revisar configuración de proxy en `next.config.ts`
3. Verificar CORS en `app/api/main.py`

### Error 401 (No autorizado)
- La autenticación está deshabilitada temporalmente para testing
- Para activarla, descomentar el middleware en el backend

### Datos no aparecen
1. Verificar respuesta del backend en `/api/leads`
2. Revisar consola del navegador para errores
3. Verificar mapeo de datos en `transformLeadToRow`

## 📚 Documentación Adicional

- **FastAPI Docs**: `http://localhost:8000/docs`
- **API Schema**: `http://localhost:8000/redoc`
- **Next.js Docs**: [https://nextjs.org/docs](https://nextjs.org/docs)

---

**¡La integración está lista para usar!** 🎉

La tabla de leads se actualiza automáticamente cada 5 segundos mostrando los datos del backend en tiempo real usando el potente componente DataTable. 