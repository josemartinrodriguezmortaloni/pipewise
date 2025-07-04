# Solución al Error OAuth de Google

## 🚨 Error Identificado
```
Error: OAuth error: "server_error" "Unable to exchange external code: 4/0AVMBsJh..."
```

## 🔍 Causa Raíz
Las URLs de redirección en **Google Cloud Console** no coinciden con la configuración de **Supabase**.

## ✅ Solución Paso a Paso

### 1. **Configurar Google Cloud Console**

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Selecciona tu proyecto
3. Ve a **APIs & Services** → **Credentials**
4. Edita tu **OAuth 2.0 Client ID**

### 2. **URLs de Redirección Correctas**

En **Authorized redirect URIs**, agrega EXACTAMENTE estas URLs:

```
http://localhost:3000/auth/callback
https://jqnfcscgtcawazgdwxsh.supabase.co/auth/v1/callback
```

**⚠️ IMPORTANTE**: 
- La primera URL es para desarrollo local
- La segunda URL es específica de tu proyecto Supabase
- NO agregues barras adicionales al final
- Las URLs deben coincidir EXACTAMENTE

### 3. **Verificar Configuración en Supabase**

1. Ve a tu [Panel de Supabase](https://supabase.com/dashboard)
2. Ve a **Authentication** → **Providers** → **Google**
3. Verifica que tengas:
   - **Client ID**: Tu Google Client ID
   - **Client Secret**: Tu Google Client Secret
   - **Redirect URL**: `https://jqnfcscgtcawazgdwxsh.supabase.co/auth/v1/callback`

### 4. **Variables de Entorno**

Verifica que tengas estas variables en tu `.env.local`:

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://jqnfcscgtcawazgdwxsh.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=tu_anon_key_aqui

# Google OAuth (opcional para el frontend)
NEXT_PUBLIC_GOOGLE_CLIENT_ID=tu_google_client_id_aqui
```

## 🧪 Prueba la Configuración

### Ejecutar Script de Verificación

```bash
node scripts/verify-oauth-config.js
```

### Prueba Manual

1. Ve a `http://localhost:3000/login`
2. Haz clic en "Iniciar sesión con Google"
3. Deberías ser redirigido a Google sin errores
4. Después de autorizar, deberías volver a tu aplicación autenticado

## 🔧 Configuración Adicional Recomendada

### En Google Cloud Console:

1. **Authorized JavaScript origins**:
   ```
   http://localhost:3000
   https://tu-dominio.com
   ```

2. **Scopes requeridos**:
   - `openid`
   - `email`
   - `profile`

### En Supabase:

1. **Configuración adicional**:
   - Habilitar **Email confirmations**: Deshabilitado para OAuth
   - **Auto-confirm users**: Habilitado para OAuth

## 🚨 Errores Comunes

### Error: "redirect_uri_mismatch"
- **Causa**: Las URLs no coinciden exactamente
- **Solución**: Verifica que las URLs sean idénticas (sin espacios, barras extra, etc.)

### Error: "unauthorized_client"
- **Causa**: El Client ID o Secret son incorrectos
- **Solución**: Verifica las credenciales en Google Cloud Console

### Error: "access_denied"
- **Causa**: El usuario canceló la autorización
- **Solución**: Normal, el usuario puede intentar de nuevo

## 📋 Checklist de Verificación

- [ ] URLs de redirección configuradas en Google Cloud Console
- [ ] Client ID y Secret configurados en Supabase
- [ ] Variables de entorno correctas en `.env.local`
- [ ] Proyecto de Google Cloud tiene APIs habilitadas
- [ ] Supabase tiene Google OAuth habilitado
- [ ] URLs coinciden EXACTAMENTE (sin espacios o barras extra)

## 🔄 Reiniciar Servicios

Después de hacer cambios:

1. **Reinicia el servidor de desarrollo**:
   ```bash
   npm run dev
   ```

2. **Limpia caché del navegador** o usa modo incógnito

3. **Verifica logs** en la consola del navegador y Supabase

## 📞 Soporte Adicional

Si el problema persiste:

1. Verifica los logs en Supabase Dashboard → Logs
2. Revisa la consola del navegador para errores adicionales
3. Contacta al soporte de Supabase si es necesario

---

**Última actualización**: 2025-01-04  
**Estado**: Solución verificada y funcional 