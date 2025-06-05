from app.schemas.auth import GoogleAuthInit, AuthCallback, UserAuth, Token

@router.post("/signup", response_model=Token)
async def signup_email(data: dict):
    """Registro vía email/password."""
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email y password requeridos")

    resp = await auth_service.sign_up_email(email, password)
    if not resp:
        raise HTTPException(status_code=400, detail="No se pudo registrar usuario")
    return resp


@router.post("/login", response_model=Token)
async def login_email(data: dict):
    """Login vía email/password."""
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email y password requeridos")

    resp = await auth_service.login_email(email, password)
    if not resp:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return resp