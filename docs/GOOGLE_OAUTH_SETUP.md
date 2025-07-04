# Google OAuth Setup para PipeWise

## Problema Identificado
Error: "Unable to exchange external code" indica que Google Cloud Console no está configurado correctamente para el flujo OAuth con Supabase.

## Configuración Requerida en Google Cloud Console

### 1. Crear/Configurar Proyecto OAuth

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Selecciona tu proyecto o crea uno nuevo
3. Ve a **APIs & Services** > **Credentials**
4. Crea **OAuth 2.0 Client ID** si no existe

### 2. Configurar URLs de Redirección Autorizadas

**CRÍTICO**: Las URLs de redirección deben coincidir exactamente con Supabase.

#### Para Desarrollo Local:
```
http://localhost:3000/auth/callback
https://[tu-proyecto-id].supabase.co/auth/v1/callback
```

#### Para Producción:
```
https://tu-dominio.com/auth/callback
https://[tu-proyecto-id].supabase.co/auth/v1/callback
```

### 3. Configurar en Supabase Dashboard

1. Ve a tu proyecto en [Supabase Dashboard](https://app.supabase.com)
2. Ve a **Authentication** > **Providers** > **Google**
3. Habilita Google OAuth
4. Agrega tu **Client ID** y **Client Secret** de Google Cloud Console
5. **Redirect URL** debe ser: `https://[tu-proyecto-id].supabase.co/auth/v1/callback`

### 4. Variables de Entorno Requeridas

#### Frontend (.env.local):
```env
NEXT_PUBLIC_SUPABASE_URL=https://[tu-proyecto-id].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=tu-anon-key
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

#### Backend (.env):
```env
SUPABASE_URL=https://[tu-proyecto-id].supabase.co
SUPABASE_ANON_KEY=tu-anon-key
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key
GOOGLE_CLIENT_ID=tu-google-client-id
GOOGLE_CLIENT_SECRET=tu-google-client-secret
```

## Pasos para Solucionar el Error Actual

### 1. Verificar URLs en Google Cloud Console

1. Ve a Google Cloud Console > APIs & Services > Credentials
2. Edita tu OAuth 2.0 Client ID
3. En **Authorized redirect URIs**, asegúrate de tener:
   ```
   https://[tu-proyecto-id].supabase.co/auth/v1/callback
   ```
   
### 2. Verificar Configuración en Supabase

1. Ve a Supabase Dashboard > Authentication > Providers > Google
2. Verifica que **Client ID** y **Client Secret** coincidan con Google Cloud Console
3. La **Redirect URL** debe ser exactamente: `https://[tu-proyecto-id].supabase.co/auth/v1/callback`

### 3. Reiniciar Servicios

Después de cambiar la configuración:
1. Guarda cambios en Google Cloud Console (puede tardar unos minutos en propagarse)
2. Guarda cambios en Supabase Dashboard
3. Reinicia tu aplicación frontend

## Debugging

### Verificar Variables de Entorno
```bash
# En el frontend
echo $NEXT_PUBLIC_SUPABASE_URL
echo $NEXT_PUBLIC_SUPABASE_ANON_KEY

# En el backend
echo $SUPABASE_URL
echo $GOOGLE_CLIENT_ID
```

### Logs Útiles
- **Frontend**: Revisa la consola del navegador para errores de OAuth
- **Supabase**: Ve a Dashboard > Logs para ver errores del servidor
- **Google Cloud**: Ve a APIs & Services > Credentials para verificar uso

## URLs de Referencia

- [Supabase Auth with Google](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Google OAuth 2.0 Setup](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)

## Solución Rápida

Si sigues teniendo problemas, verifica que tu URL de callback en el código coincida exactamente:

```typescript
// frontend/lib/auth.ts - línea 165
await supabase.auth.signInWithOAuth({
  provider: "google",
  options: {
    redirectTo: `${window.location.origin}/auth/callback`, // Debe coincidir con Google Cloud Console
  },
});
``` 