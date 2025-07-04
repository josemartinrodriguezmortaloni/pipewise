# Google OAuth Implementation - PipeWise

## 🎯 Overview

Complete implementation of Google OAuth authentication for the PipeWise application using Supabase Auth with custom backend synchronization.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Supabase      │    │   Backend API   │
│   (Next.js)     │    │   Auth          │    │   (FastAPI)     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • LoginForm     │───▶│ • Google OAuth  │───▶│ • User Sync     │
│ • useAuth Hook  │    │ • Token Exchange│    │ • Session Mgmt  │
│ • Callback Page │◀───│ • Session Mgmt  │◀───│ • Profile Data  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔄 Authentication Flow

### 1. **User Initiates Login**
```javascript
// User clicks "Sign in with Google"
const handleGoogleLogin = async () => {
  await loginWithGoogle();
};
```

### 2. **Supabase OAuth Redirect**
```javascript
// lib/auth.ts
export async function loginWithGoogle(): Promise<void> {
  const { supabase } = await import("@/lib/supabase");
  
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: `${window.location.origin}/dashboard`,
      queryParams: {
        access_type: 'offline',
        prompt: 'consent',
      },
    },
  });
}
```

### 3. **Google Authentication**
- User is redirected to Google OAuth consent screen
- Google validates credentials and permissions
- Google redirects back to Supabase with authorization code

### 4. **Supabase Token Exchange**
- Supabase exchanges authorization code for access token
- Creates authenticated session
- Triggers `onAuthStateChange` event

### 5. **Frontend State Management**
```javascript
// hooks/use-auth.tsx
const { data: authListener } = supabase.auth.onAuthStateChange(
  async (event, session) => {
    if (session?.user && session.access_token) {
      const isOAuthProvider = session.user.app_metadata?.provider !== "email";
      
      if (isOAuthProvider) {
        // Sync with backend
        const backendAuth = await syncAuthWithBackend(session);
        if (backendAuth?.user) {
          setUser(backendAuth.user);
        }
      }
    }
  }
);
```

### 6. **Backend Synchronization**
```python
# app/api/auth.py
@router.post("/supabase-sync", response_model=UserLoginResponse)
async def sync_supabase_auth(
    request: Request,
    auth_data: SupabaseAuthSync,
    background_tasks: BackgroundTasks,
):
    # Verify Supabase token
    # Create/update user in database
    # Generate backend tokens
    # Return user profile
```

### 7. **User Profile Creation/Update**
```python
# app/auth/auth_client.py
async def sync_supabase_user(
    self,
    supabase_user: Dict[str, Any],
    provider_token: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Dict[str, Any]:
    # Verify token with Supabase
    # Check if user exists
    # Create or update user record
    # Create session tokens
    # Log authentication event
```

## 📁 File Structure

### Frontend Files
```
frontend/
├── lib/
│   ├── auth.ts              # loginWithGoogle implementation
│   └── supabase.ts          # syncAuthWithBackend function
├── hooks/
│   └── use-auth.tsx         # OAuth state management
├── components/
│   └── login-form.tsx       # Google login button
└── app/auth/callback/
    └── page.tsx             # OAuth callback handler
```

### Backend Files
```
app/
├── api/
│   └── auth.py              # /supabase-sync endpoint
├── auth/
│   └── auth_client.py       # sync_supabase_user method
└── schemas/
    └── auth_schema.py       # SupabaseAuthSync model
```

## 🔧 Configuration

### Environment Variables

#### Frontend (.env.local)
```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8001
```

#### Backend (.env)
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
JWT_SECRET=your-jwt-secret
```

### Supabase Dashboard Configuration

1. **Navigate to Authentication → Providers → Google**
2. **Enable Google Provider**
3. **Configure OAuth Settings:**
   ```
   Client ID: your-google-client-id
   Client Secret: your-google-client-secret
   ```

### Google Cloud Console Configuration

1. **Create OAuth 2.0 Client ID**
2. **Configure Authorized Redirect URIs:**
   ```
   https://your-project.supabase.co/auth/v1/callback
   ```

## 🔐 Security Features

### Token Validation
```python
async def validate_token(self, token: str) -> TokenValidationResponse:
    # Try Supabase token validation first
    try:
        auth_response = self.client.auth.get_user(token)
        if auth_response and auth_response.user:
            return TokenValidationResponse(valid=True, ...)
    except AuthApiError:
        # Fallback to local JWT validation
        payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        return TokenValidationResponse(valid=True, ...)
```

### Session Management
```python
async def _create_user_session(
    self,
    user: User,
    remember_me: bool,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[str, str]:
    # Generate access and refresh tokens
    # Create session record in database
    # Set appropriate expiration times
```

### Audit Logging
```python
async def _log_auth_event(
    self,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    action: str = "",
    success: bool = True,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    # Log all authentication events for security auditing
```

## 🎨 User Experience

### Loading States
- **Initial OAuth redirect**: Immediate feedback
- **Callback processing**: Loading spinner with status updates
- **Error handling**: Clear error messages with retry options

### Error Handling
```javascript
// Comprehensive error handling in callback page
const error = searchParams.get("error");
if (error === "server_error" && 
    errorDescription?.includes("Unable to exchange external code")) {
  userFriendlyMessage = "Error de configuración OAuth. Verifica credenciales.";
}
```

### Success Flow
```javascript
// Smooth transition to dashboard
if (isAuthenticated) {
  setStatus("success");
  setMessage("¡Autenticación exitosa! Redirigiendo...");
  setTimeout(() => router.replace("/dashboard"), 1500);
}
```

## 🧪 Testing

### Manual Testing
1. **Start both servers:**
   ```bash
   # Backend
   python -m uvicorn server:app --reload --port 8001
   
   # Frontend
   cd frontend && npm run dev
   ```

2. **Test OAuth flow:**
   - Navigate to `http://localhost:3000/login`
   - Click "Sign in with Google"
   - Complete Google authentication
   - Verify redirect to dashboard

### Debugging
```bash
# Run test script
node scripts/test-google-oauth-flow.js
```

### Common Issues
- **"Unable to exchange external code"**: Check Supabase OAuth credentials
- **"Backend sync failed"**: Verify `SUPABASE_SERVICE_ROLE_KEY`
- **Redirect loops**: Check `redirectTo` configuration

## 📊 Monitoring

### Frontend Logs
```javascript
console.log("OAuth login detected, syncing with backend...");
console.log("✅ OAuth user synchronized with backend");
console.warn("⚠️ Backend sync failed, using fallback user profile");
```

### Backend Logs
```python
logger.info("🔄 Syncing Supabase auth with backend...")
logger.info("✅ Backend sync successful")
logger.error("❌ Failed to sync auth with backend")
```

### Database Monitoring
- Monitor `users` table for new OAuth registrations
- Check `auth_audit_logs` for authentication events
- Review `user_sessions` for active sessions

## 🚀 Deployment Considerations

### Environment Variables
- Ensure all production environment variables are set
- Use different Google OAuth credentials for production
- Configure production redirect URLs

### Security
- Enable RLS policies on user tables
- Use HTTPS in production
- Implement rate limiting on auth endpoints

### Performance
- Consider Redis for session storage in production
- Implement token caching strategies
- Monitor authentication latency

## 📝 API Reference

### Frontend API
```typescript
// Authentication hook
const { loginWithGoogle, isAuthenticated, user } = useAuth();

// Direct auth functions
import { loginWithGoogle } from "@/lib/auth";
import { syncAuthWithBackend } from "@/lib/supabase";
```

### Backend API
```python
# Supabase sync endpoint
POST /api/auth/supabase-sync
{
  "user": { /* Supabase user object */ },
  "provider_token": "supabase_access_token"
}

# Response
{
  "access_token": "backend_jwt_token",
  "refresh_token": "refresh_token",
  "user": { /* User profile */ }
}
```

## 🎯 Implementation Status

- ✅ **Frontend OAuth Flow**: Complete
- ✅ **Backend Synchronization**: Complete  
- ✅ **Error Handling**: Complete
- ✅ **User Experience**: Enhanced
- ✅ **Security Features**: Implemented
- ✅ **Documentation**: Complete

## 🔄 Next Steps

1. **Test the complete flow** with your specific Google OAuth credentials
2. **Monitor logs** during testing to ensure smooth operation
3. **Customize user profile fields** as needed for your application
4. **Implement additional OAuth providers** if required (GitHub, etc.)

The Google OAuth implementation is now complete and ready for use! 🎉 