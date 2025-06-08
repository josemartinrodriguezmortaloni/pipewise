# PipeWise CRM - Configuración Supabase

Este documento te guía para configurar Supabase con PipeWise CRM, incluyendo autenticación real y Google Authenticator.

## 📋 Requisitos Previos

- Cuenta en [Supabase](https://supabase.com)
- Python 3.8+ con uv instalado
- Node.js 18+ para el frontend

## 🚀 Configuración Paso a Paso

### 1. Crear Proyecto en Supabase

1. Ve a [supabase.com](https://supabase.com) y crea una cuenta
2. Crea un nuevo proyecto
3. Elige un nombre para tu proyecto (ej: "pipewise-crm")
4. Selecciona una región cercana
5. Crea una contraseña segura para la base de datos

### 2. Configurar Base de Datos

1. Ve a la sección **SQL Editor** en tu proyecto Supabase
2. Copia y pega el contenido del archivo `database_setup.sql`
3. Ejecuta el script haciendo clic en "Run"

Esto creará:
- ✅ Tabla de usuarios con soporte para 2FA
- ✅ Tablas del CRM (leads, contacts, tasks, pipelines, integrations)
- ✅ Políticas RLS (Row Level Security)
- ✅ Triggers automáticos
- ✅ Índices para performance

### 3. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Optional: Server Configuration
HOST=0.0.0.0
PORT=8000
ENV=development
```

**¿Dónde encontrar las claves?**

1. Ve a **Settings** → **API** en tu proyecto Supabase
2. Copia la **Project URL** como `SUPABASE_URL`
3. Copia la **anon/public** key como `SUPABASE_ANON_KEY`
4. Copia la **service_role** key como `SUPABASE_SERVICE_KEY` (opcional)

### 4. Configurar Autenticación

1. Ve a **Authentication** → **Settings** en Supabase
2. Configura las URLs permitidas:
   - Site URL: `http://localhost:3000`
   - Redirect URLs: `http://localhost:3000/**`
3. Habilita los proveedores de autenticación que necesites

### 5. Instalar Dependencias

```bash
# Backend
uv add supabase qrcode[pil] pyotp fastapi uvicorn

# Frontend (si no están instaladas)
cd frontend
npm install @supabase/supabase-js
```

### 6. Ejecutar el Sistema

```bash
# Terminal 1: Backend
python __main__.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

## 🔒 Características de Seguridad

### Row Level Security (RLS)

Todas las tablas tienen políticas RLS configuradas:
- Los usuarios solo pueden acceder a sus propios datos
- Separación completa de datos entre usuarios
- Políticas automáticas para CRUD operations

### Google Authenticator (2FA)

El sistema incluye soporte completo para 2FA:
- Generación de códigos QR
- Verificación TOTP
- Códigos de backup
- Habilitación/deshabilitación de 2FA

## 📊 Estructura de la Base de Datos

```
users                 # Perfiles de usuario + 2FA
├── id (UUID)
├── email
├── full_name
├── company
├── phone
├── has_2fa
├── totp_secret
└── ...

leads                 # Prospectos/Leads
├── id (UUID)
├── user_id (FK)
├── name
├── email
├── status
└── ...

contacts              # Interacciones
├── id (UUID)
├── user_id (FK)
├── lead_id (FK)
├── type
└── ...

tasks                 # Tareas
├── id (UUID)
├── user_id (FK)
├── lead_id (FK)
├── title
└── ...

pipelines             # Embudos de venta
├── id (UUID)
├── user_id (FK)
├── name
├── stages (JSONB)
└── ...

integrations          # Integraciones externas
├── id (UUID)
├── user_id (FK)
├── type
├── config (JSONB)
└── ...
```

## 🔧 API Endpoints

### Autenticación
- `POST /auth/register` - Registrar usuario
- `POST /auth/login` - Login (con 2FA opcional)
- `POST /auth/refresh` - Renovar token
- `GET /auth/validate` - Validar token
- `GET /auth/profile` - Obtener perfil
- `POST /auth/logout` - Logout

### 2FA (Google Authenticator)
- `POST /auth/2fa/enable` - Habilitar 2FA
- `POST /auth/2fa/verify` - Verificar y activar 2FA
- `POST /auth/2fa/disable` - Deshabilitar 2FA

### CRM (próximamente)
- `/api/leads/*` - Gestión de leads
- `/api/contacts/*` - Gestión de contactos
- `/api/tasks/*` - Gestión de tareas
- `/api/pipelines/*` - Gestión de pipelines

## 🔍 Monitoreo y Logs

El sistema incluye logging completo:
- Todas las operaciones de autenticación
- Errores y excepciones
- Métricas de performance
- Archivo de log: `pipewise.log`

## 🛠️ Desarrollo y Debug

### Verificar Conexión Supabase

```bash
curl http://localhost:8000/health
```

### Ver Logs en Tiempo Real

```bash
tail -f pipewise.log
```

### Documentación API Interactiva

Una vez ejecutando, visita:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🚨 Troubleshooting

### Error: "Missing Supabase configuration"
- Verifica que el archivo `.env` existe
- Confirma que `SUPABASE_URL` y `SUPABASE_ANON_KEY` están configuradas

### Error: "Failed to fetch"
- Verifica que el backend esté ejecutándose en puerto 8000
- Confirma la configuración CORS
- Verifica las claves de Supabase

### Error de Base de Datos
- Ejecuta nuevamente el script `database_setup.sql`
- Verifica las políticas RLS en Supabase Dashboard

### Error de 2FA
- Verifica que la librería `pyotp` esté instalada
- Confirma que el código TOTP es válido (6 dígitos)
- Verifica que el reloj del dispositivo esté sincronizado

## 📚 Recursos Adicionales

- [Documentación Supabase](https://supabase.com/docs)
- [Documentación FastAPI](https://fastapi.tiangolo.com)
- [Google Authenticator](https://support.google.com/accounts/answer/1066447)
- [pyotp Documentation](https://pyauth.github.io/pyotp/)

## 🤝 Soporte

Si encuentras problemas:
1. Revisa los logs del servidor
2. Verifica la configuración de Supabase
3. Consulta este documento
4. Crea un issue con detalles del error

---

✅ **Sistema listo para producción con autenticación real y separación de datos por usuario** 