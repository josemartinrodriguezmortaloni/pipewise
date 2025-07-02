# Sistema de Integraciones OAuth Simplificado - PipeWise

## Resumen

Este documento describe el sistema de integraciones OAuth simplificado para PipeWise, donde **todas las integraciones funcionan únicamente mediante OAuth 2.0**. No hay configuración manual de API keys - todo se maneja automáticamente tras la autenticación del usuario.

## Beneficios del Enfoque Simplificado

- **Experiencia de Usuario Mejorada**: Un solo clic para conectar servicios
- **Mayor Seguridad**: No hay API keys que gestionar o almacenar manualmente
- **Configuración Más Simple**: Eliminación de formularios complejos
- **Onboarding Más Rápido**: Los usuarios pueden comenzar a trabajar inmediatamente
- **Menos Errores**: Eliminación de errores de configuración manual

## Integraciones Disponibles

### 📅 Calendario
- **Calendly**: Programación automática de reuniones
- **Google Calendar**: Sincronización de eventos y disponibilidad

### 🏢 CRM
- **Pipedrive**: Gestión de leads y pipeline de ventas
- **Salesforce**: Integración completa con Salesforce CRM
- **Zoho CRM**: Sincronización de contactos y oportunidades

### 📧 Email
- **SendGrid**: Envío automatizado de emails (OAuth a través de Twilio)

### 📱 Redes Sociales
- **Twitter/X**: Engagement y gestión de conversaciones
- **Instagram**: Gestión de mensajes directos

## Arquitectura del Sistema

### Backend Components

```
app/
├── core/
│   ├── oauth_config.py      # Configuración centralizada OAuth
│   └── security.py          # Cifrado de tokens
├── api/
│   ├── oauth_handler.py     # Lógica principal OAuth
│   ├── oauth_router.py      # Endpoints OAuth
│   └── user_config_router.py # Gestión de cuentas conectadas
```

### Frontend Components

```
frontend/
├── lib/
│   └── integrations-config.ts    # Configuración de integraciones
├── components/
│   ├── oauth-integration-card.tsx # Tarjetas de integración OAuth
│   └── integrations-settings.tsx  # Interfaz principal
```

## Configuración de Variables de Entorno

Para cada servicio OAuth, configura las siguientes variables:

```bash
# URLs base
OAUTH_BASE_URL=http://localhost:8000  # Desarrollo
# OAUTH_BASE_URL=https://yourdomain.com  # Producción

# Calendly
CALENDLY_CLIENT_ID=your_calendly_client_id
CALENDLY_CLIENT_SECRET=your_calendly_client_secret

# Google Calendar
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Pipedrive
PIPEDRIVE_CLIENT_ID=your_pipedrive_client_id
PIPEDRIVE_CLIENT_SECRET=your_pipedrive_client_secret

# Salesforce
SALESFORCE_CLIENT_ID=your_salesforce_client_id
SALESFORCE_CLIENT_SECRET=your_salesforce_client_secret

# Zoho CRM
ZOHO_CLIENT_ID=your_zoho_client_id
ZOHO_CLIENT_SECRET=your_zoho_client_secret

# Twitter
TWITTER_CLIENT_ID=your_twitter_client_id
TWITTER_CLIENT_SECRET=your_twitter_client_secret

# Instagram
INSTAGRAM_CLIENT_ID=your_instagram_client_id
INSTAGRAM_CLIENT_SECRET=your_instagram_client_secret

# SendGrid (OAuth via Twilio)
SENDGRID_CLIENT_ID=your_sendgrid_client_id
SENDGRID_CLIENT_SECRET=your_sendgrid_client_secret

# Cifrado de tokens
ENCRYPTION_KEY=your_fernet_encryption_key
```

## URLs de Callback para Registrar Aplicaciones

### Desarrollo (localhost:8000)
```
Calendly: http://localhost:8000/api/integrations/calendly/oauth/callback
Google: http://localhost:8000/api/integrations/google_calendar/oauth/callback
Pipedrive: http://localhost:8000/api/integrations/pipedrive/oauth/callback
Salesforce: http://localhost:8000/api/integrations/salesforce_rest_api/oauth/callback
Zoho: http://localhost:8000/api/integrations/zoho_crm/oauth/callback
Twitter: http://localhost:8000/api/integrations/twitter_account/oauth/callback
Instagram: http://localhost:8000/api/integrations/instagram_account/oauth/callback
SendGrid: http://localhost:8000/api/integrations/sendgrid_email/oauth/callback
```

### Producción
Reemplaza `localhost:8000` con tu dominio de producción.

## Flujo de Usuario

1. **Acceso a Integraciones**: Usuario navega a `/integrations`
2. **Selección de Servicio**: Hace clic en "Conectar" para cualquier servicio
3. **Redirección OAuth**: Es redirigido al proveedor para autenticación
4. **Autorización**: Autoriza el acceso a su cuenta
5. **Callback y Almacenamiento**: El sistema almacena tokens de forma segura
6. **Confirmación**: Usuario regresa con confirmación de éxito
7. **Uso Inmediato**: La integración está lista para usar

## Características de Seguridad

- **Cifrado de Tokens**: Todos los tokens OAuth se cifran con Fernet
- **State Parameters**: Protección contra ataques CSRF
- **Refresh Automático**: Renovación automática de tokens expirados
- **Almacenamiento Seguro**: Tokens cifrados en Supabase
- **Validación de Estado**: Verificación de integridad en callbacks

## Solución de Problemas

### Error: "OAuth configuration not found"
- Verifica que las variables de entorno estén configuradas
- Asegúrate de que el servicio esté en la lista de proveedores soportados

### Error: "Invalid redirect URI"
- Verifica que la URL de callback esté registrada en la aplicación del proveedor
- Confirma que `OAUTH_BASE_URL` sea correcta

### Error: "Token refresh failed"
- El usuario debe reconectarse manualmente
- Verifica que el refresh token sea válido

### Error: "Missing React keys"
- Este error ya está solucionado con las keys únicas en componentes

## Comandos de Setup

```bash
# Instalar dependencias
pip install cryptography httpx

# Generar clave de cifrado (opcional - se genera automáticamente)
python app/scripts/setup_oauth.py --generate-key

# Validar configuración OAuth
python app/scripts/setup_oauth.py --validate

# Iniciar servidores
python server.py &
cd frontend && npm run dev
```

## Próximos Pasos

1. **Configurar Credenciales**: Registra aplicaciones OAuth con cada proveedor
2. **Configurar Variables**: Añade credenciales a tu archivo `.env`
3. **Probar Integraciones**: Verifica que cada OAuth funcione correctamente
4. **Documentar Casos de Uso**: Define qué funcionalidades usará cada integración
5. **Implementar Webhooks**: Configura webhooks para actualizaciones en tiempo real

## Referencias de APIs

- [Calendly API](https://developer.calendly.com/)
- [Google Calendar API](https://developers.google.com/calendar)
- [Pipedrive API](https://developers.pipedrive.com/)
- [Salesforce API](https://developer.salesforce.com/)
- [Zoho CRM API](https://www.zoho.com/crm/developer/)
- [Twitter API v2](https://developer.twitter.com/en/docs/twitter-api)
- [Instagram Basic Display API](https://developers.facebook.com/docs/instagram-basic-display-api)
- [SendGrid API](https://docs.sendgrid.com/)

El sistema está ahora completamente simplificado y listo para su uso en producción. 