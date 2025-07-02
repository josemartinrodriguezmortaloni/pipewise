# OAuth Environment Setup

Esta guía te ayudará a configurar las variables de entorno necesarias para las integraciones OAuth en PipeWise.

## 🔧 **Configuración de Desarrollador vs Usuario**

### **IMPORTANTE: Diferencia entre claves**

#### 🏗️ **Claves de Aplicación** (van en `.env`):
Estas son las credenciales de tu aplicación registrada en cada proveedor. Son necesarias para que el sistema OAuth funcione.

#### 👤 **Tokens de Usuario** (automáticos):
Estos se obtienen automáticamente cuando cada usuario autoriza la integración. **NO van en el archivo .env**.

## ⚙️ **Variables de Entorno Requeridas**

### **Configuración de Seguridad**
```bash
# Clave de cifrado para tokens OAuth (genera una nueva)
PIPEWISE_FERNET_KEY=tu_clave_fernet_aqui

# URLs de la aplicación
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```

### **Calendly** 🗓️
```bash
# Credenciales de aplicación (necesarias)
CALENDLY_CLIENT_ID=tu_calendly_client_id
CALENDLY_CLIENT_SECRET=tu_calendly_client_secret

# ❌ NO incluyas esto - se obtiene automáticamente:
# CALENDLY_ACCESS_TOKEN=  ← ELIMINAR
```

### **Google Calendar** 📅
```bash
# Credenciales de aplicación (necesarias)
GOOGLE_CLIENT_ID=tu_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu_google_client_secret

# ❌ NO incluyas tokens de usuario:
# GOOGLE_ACCESS_TOKEN=  ← ELIMINAR
```

### **Pipedrive** 🏢
```bash
# Credenciales de aplicación (necesarias)
PIPEDRIVE_CLIENT_ID=tu_pipedrive_client_id
PIPEDRIVE_CLIENT_SECRET=tu_pipedrive_client_secret

# ❌ NO incluyas tokens de usuario:
# PIPEDRIVE_ACCESS_TOKEN=  ← ELIMINAR
```

### **Salesforce** ⚡
```bash
# Credenciales de aplicación (necesarias)
SALESFORCE_CLIENT_ID=tu_salesforce_consumer_key
SALESFORCE_CLIENT_SECRET=tu_salesforce_consumer_secret

# ❌ NO incluyas tokens de usuario:
# SALESFORCE_ACCESS_TOKEN=  ← ELIMINAR
```

### **Zoho CRM** 📊
```bash
# Credenciales de aplicación (necesarias)
ZOHO_CLIENT_ID=tu_zoho_client_id
ZOHO_CLIENT_SECRET=tu_zoho_client_secret

# ❌ NO incluyas tokens de usuario:
# ZOHO_ACCESS_TOKEN=  ← ELIMINAR
```

### **Twitter/X** 🐦
```bash
# Credenciales de aplicación (necesarias)
TWITTER_CLIENT_ID=tu_twitter_client_id
TWITTER_CLIENT_SECRET=tu_twitter_client_secret

# ❌ NO incluyas tokens de usuario:
# TWITTER_ACCESS_TOKEN=  ← ELIMINAR
# TWITTER_ACCESS_TOKEN_SECRET=  ← ELIMINAR
```

### **SendGrid** 📧
```bash
# Credenciales de aplicación (necesarias)
SENDGRID_CLIENT_ID=tu_sendgrid_client_id
SENDGRID_CLIENT_SECRET=tu_sendgrid_client_secret

# ❌ NO incluyas API keys de usuario:
# SENDGRID_API_KEY=  ← ELIMINAR
```

### **Instagram** 📸
```bash
# Credenciales de aplicación (necesarias)
INSTAGRAM_CLIENT_ID=tu_instagram_app_id
INSTAGRAM_CLIENT_SECRET=tu_instagram_app_secret

# ❌ NO incluyas tokens de usuario:
# INSTAGRAM_ACCESS_TOKEN=  ← ELIMINAR
```

## 🔄 **Flujo de Integración para Usuarios**

### **Paso 1: Usuario inicia integración**
1. Usuario hace clic en "Conectar" en la interfaz
2. Se redirige al proveedor (ej: Calendly, Google, etc.)
3. Usuario autoriza la aplicación en el sitio del proveedor

### **Paso 2: Sistema obtiene tokens automáticamente**
1. Proveedor regresa con código de autorización
2. Sistema intercambia código por access token
3. Token se cifra y guarda en Supabase para ese usuario
4. Usuario queda conectado - ¡listo para usar!

## ✅ **Ejemplo de .env Correcto**

```bash
# ===== SEGURIDAD =====
PIPEWISE_FERNET_KEY=gAAAAABh7x8y9K2mN5pQ1rS3tU4vW6xY7zA8bC9dE0fG1hI2jK3lM4n

# ===== URLS =====
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000

# ===== CALENDLY =====
CALENDLY_CLIENT_ID=tu_calendly_client_id
CALENDLY_CLIENT_SECRET=tu_calendly_client_secret

# ===== GOOGLE CALENDAR =====
GOOGLE_CLIENT_ID=123456789.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu_google_client_secret

# ===== PIPEDRIVE =====
PIPEDRIVE_CLIENT_ID=tu_pipedrive_client_id
PIPEDRIVE_CLIENT_SECRET=tu_pipedrive_client_secret

# ===== SALESFORCE =====
SALESFORCE_CLIENT_ID=tu_salesforce_consumer_key
SALESFORCE_CLIENT_SECRET=tu_salesforce_consumer_secret

# ===== ZOHO CRM =====
ZOHO_CLIENT_ID=tu_zoho_client_id
ZOHO_CLIENT_SECRET=tu_zoho_client_secret

# ===== TWITTER =====
TWITTER_CLIENT_ID=tu_twitter_client_id
TWITTER_CLIENT_SECRET=tu_twitter_client_secret

# ===== SENDGRID =====
SENDGRID_CLIENT_ID=tu_sendgrid_client_id
SENDGRID_CLIENT_SECRET=tu_sendgrid_client_secret

# ===== INSTAGRAM =====
INSTAGRAM_CLIENT_ID=tu_instagram_app_id
INSTAGRAM_CLIENT_SECRET=tu_instagram_app_secret
```

## 🚀 **Configuración Rápida**

### **Opción 1: Script Automático**
```bash
python app/scripts/setup_oauth.py --generate-env
```

### **Opción 2: Manual**
1. Copia el ejemplo de arriba
2. Reemplaza `tu_*_client_id` y `tu_*_client_secret` con tus credenciales reales
3. Genera una clave Fernet: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## ❗ **Errores Comunes**

### **❌ Error: Incluir tokens de usuario en .env**
```bash
# INCORRECTO - NO hagas esto:
CALENDLY_ACCESS_TOKEN=v1.abc123...
GOOGLE_ACCESS_TOKEN=ya29.def456...
```

### **✅ Correcto: Solo credenciales de aplicación**
```bash
# CORRECTO - Solo esto:
CALENDLY_CLIENT_ID=tu_client_id
CALENDLY_CLIENT_SECRET=tu_client_secret
```

## 🔍 **Verificación**

Para verificar que tu configuración es correcta:

```bash
# Ejecutar script de verificación
python app/scripts/setup_oauth.py --validate

# Iniciar servidor y probar integraciones
python server.py
```

Luego visita `http://localhost:3000/integrations` y prueba conectar cualquier servicio.

## Configuración de Desarrollo

### 1. Generar Clave de Cifrado

```bash
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

### 2. Archivo .env Local

Crea un archivo `.env` en la raíz del proyecto con todas las variables:

```bash
# Copia todas las variables de arriba y ajusta los valores
OAUTH_BASE_URL=http://localhost:8000
ENCRYPTION_KEY=tu_clave_generada_aqui
# ... resto de variables
```

### 3. Configuración para Desarrollo Local

Para desarrollo local, usa `http://localhost:8000` como `OAUTH_BASE_URL`. Asegúrate de registrar estas URLs en cada proveedor OAuth:

- Calendly: `http://localhost:8000/api/integrations/calendly/oauth/callback`
- Google: `http://localhost:8000/api/integrations/google_calendar/oauth/callback`
- Pipedrive: `http://localhost:8000/api/integrations/pipedrive/oauth/callback`
- Salesforce: `http://localhost:8000/api/integrations/salesforce_rest_api/oauth/callback`
- Zoho: `http://localhost:8000/api/integrations/zoho_crm/oauth/callback`
- Twitter: `http://localhost:8000/api/integrations/twitter_account/oauth/callback`

## Configuración de Producción

### 1. Variables de Entorno en Servidor

En producción, usa tu dominio real:

```bash
OAUTH_BASE_URL=https://tu-dominio.com
```

### 2. Actualizar Redirect URIs

Actualiza todos los redirect URIs en cada proveedor OAuth para usar tu dominio de producción.

### 3. Seguridad

- ✅ Usa inyección de variables de entorno (no archivos .env)
- ✅ Genera una clave de cifrado fuerte única
- ✅ Cambia el ENCRYPTION_SALT a un valor único
- ✅ Nunca cometas credenciales reales al control de versiones
- ✅ Rota regularmente tus credenciales OAuth

## Verificación de Configuración

### 1. Verificar Variables de Entorno

```bash
python -c "
import os
from app.core.oauth_config import get_oauth_config

# Verificar cada servicio
services = ['calendly', 'google_calendar', 'pipedrive', 'salesforce_rest_api', 'zoho_crm', 'twitter_account']
for service in services:
    config = get_oauth_config(service)
    if config:
        print(f'✅ {service}: Configurado')
    else:
        print(f'❌ {service}: Falta configuración')
"
```

### 2. Probar Cifrado

```bash
python -c "
from app.core.security import encrypt_oauth_tokens, decrypt_oauth_tokens

# Probar cifrado
test_tokens = {'access_token': 'test', 'refresh_token': 'test'}
encrypted = encrypt_oauth_tokens(test_tokens)
decrypted = decrypt_oauth_tokens(encrypted)
print('✅ Cifrado funcionando' if decrypted == test_tokens else '❌ Error en cifrado')
"
```

## Solución de Problemas

### Error: "OAuth not configured for service"

- Verifica que las variables de entorno estén configuradas
- Asegúrate de que ENCRYPTION_KEY esté presente
- Revisa que los nombres de las variables sean exactos

### Error: "Invalid encryption key"

- Genera una nueva clave de cifrado con el comando proporcionado
- Verifica que ENCRYPTION_KEY esté correctamente configurada

### Error en Callback: "Invalid or expired state token"

- Verifica que OAUTH_BASE_URL sea correcta
- Asegúrate de que los redirect URIs estén configurados correctamente en cada proveedor
- Revisa que no haya problemas de red o cookies

### Error: "Failed to exchange code for tokens"

- Verifica las credenciales CLIENT_ID y CLIENT_SECRET
- Asegúrate de que el redirect URI configurado coincida exactamente
- Revisa los logs del servidor para más detalles 