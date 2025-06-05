from typing import Optional
import secrets
from fastapi import APIRouter, HTTPException, Query, Response, Depends
from fastapi.responses import RedirectResponse

from app.schemas.auth import GoogleAuthInit, AuthCallback, UserAuth, Token
from app.services.auth import AuthService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["authentication"])
auth_service = AuthService()

# Almacenar estados temporalmente (en producción usar Redis/base de datos)
oauth_states: dict[str, bool] = {}


@router.get("/login/google", response_model=GoogleAuthInit)
async def login_google():
    """Iniciar proceso de autenticación con Google."""
    state = secrets.token_urlsafe(32)
    oauth_states[state] = True
    auth_url = auth_service.get_google_auth_url(state)
    return GoogleAuthInit(auth_url=auth_url, state=state)


@router.get("/callback")
async def auth_callback(code: str = Query(...), state: str = Query(...)):
    """Callback de Google OAuth."""
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Estado inválido")
    del oauth_states[state]
    user_auth = await auth_service.handle_google_callback(code, state)
    if not user_auth:
        raise HTTPException(status_code=400, detail="Error en autenticación")
    return {
        "access_token": user_auth.access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user_auth.id),
            "email": user_auth.email,
            "full_name": user_auth.full_name,
            "avatar_url": user_auth.avatar_url,
        },
    }


# ------------------------------------------------------------------
# Email/Password auth endpoints
# ------------------------------------------------------------------
@router.post("/signup", response_model=Token)
async def signup_email(payload: dict):
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email y password requeridos")

    token = await auth_service.sign_up_email(email, password)
    if not token:
        raise HTTPException(status_code=400, detail="No se pudo registrar usuario")
    return token


@router.post("/login", response_model=Token)
async def login_email(payload: dict):
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email y password requeridos")

    token = await auth_service.login_email(email, password)
    if not token:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return token


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    tokens = await auth_service.refresh_token(refresh_token)
    if not tokens:
        raise HTTPException(status_code=401, detail="Token de refresh inválido")
    return Token(
        access_token=tokens["access_token"],
        token_type="bearer",
        expires_in=tokens["expires_in"],
        refresh_token=tokens.get("refresh_token"),
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Sesión cerrada exitosamente"}


@router.get("/me", response_model=UserAuth)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserAuth(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        provider=current_user.provider,
        access_token="",
        refresh_token=None,
    )