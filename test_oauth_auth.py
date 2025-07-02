#!/usr/bin/env python3
"""
Prueba de autenticación OAuth para PipeWise
"""

import os
import requests
import jwt
import logging
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configurar URLs
API_URL = os.getenv("API_URL", "http://localhost:8001")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# JWT Secret para decodificar tokens (solo para debug)
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key")


def create_test_token(
    user_id: str = "mock_user_id", email: str = "test@example.com", role: str = "user"
) -> str:
    """Crear un token JWT de prueba para autenticación"""
    try:
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "exp": 9999999999,  # Token válido por mucho tiempo
        }

        # Intentar usar el JWT_SECRET del .env
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        logger.info(f"Token de prueba creado para {email}")
        return token
    except Exception as e:
        logger.error(f"Error al crear token: {e}")
        return ""


def decode_token(token: str) -> Dict[str, Any]:
    """Decodificar token JWT para inspección"""
    try:
        # Intentar decodificar con nuestro secret
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except Exception as e:
        logger.error(f"Error al decodificar token: {e}")
        try:
            # Si falla, intentar decodificar sin verificación (solo para inspección)
            payload = jwt.decode(token, options={"verify_signature": False})
            logger.warning("Token decodificado sin verificar firma")
            return payload
        except Exception as e2:
            logger.error(f"Error al decodificar token sin verificación: {e2}")
            return {}


def test_oauth_endpoint(service: str, token: Optional[str] = None) -> None:
    """Probar endpoint de inicio OAuth con token de autenticación"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{API_URL}/api/integrations/{service}/oauth/start"
    logger.info(f"Probando endpoint OAuth: {url}")
    logger.info(f"Headers: {headers}")

    try:
        # Hacer solicitud sin seguir redirecciones
        response = requests.get(url, headers=headers, allow_redirects=False)

        logger.info(f"Código de estado: {response.status_code}")

        if response.status_code == 302:  # Redirección esperada
            location = response.headers.get("Location", "")
            logger.info(f"Redirección a: {location}")
            logger.info("✅ Endpoint OAuth funcionando correctamente")
        elif response.status_code == 401:
            logger.error("❌ Error de autenticación: Token no válido o expirado")
        elif response.status_code == 403:
            logger.error("❌ Error de permisos: No tienes permisos para esta acción")
        elif response.status_code == 404:
            logger.error("❌ Error 404: Endpoint no encontrado")
        else:
            # Intentar obtener cuerpo de la respuesta
            try:
                body = response.json()
                logger.error(f"❌ Error {response.status_code}: {body}")
            except:
                logger.error(f"❌ Error {response.status_code}: {response.text}")

    except Exception as e:
        logger.error(f"❌ Error al hacer la solicitud: {e}")


def test_token_validation(token: str) -> None:
    """Probar validación de token en el backend"""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_URL}/auth/validate"

    logger.info(f"Probando validación de token: {url}")

    try:
        response = requests.get(url, headers=headers)
        if response.ok:
            data = response.json()
            logger.info(f"✅ Token válido: {data}")
        else:
            logger.error(f"❌ Token inválido: {response.status_code}")
            try:
                logger.error(response.json())
            except:
                logger.error(response.text)
    except Exception as e:
        logger.error(f"❌ Error al validar token: {e}")


def main():
    """Función principal"""
    logger.info("== Test de autenticación OAuth ==")

    # 1. Crear token de prueba
    test_token = create_test_token()
    logger.info(f"Token de prueba: {test_token[:10]}...")

    # 2. Decodificar token para inspección
    payload = decode_token(test_token)
    logger.info(f"Contenido del token: {payload}")

    # 3. Probar endpoint OAuth sin token (debe fallar)
    logger.info("\n== Prueba sin token (debe fallar) ==")
    test_oauth_endpoint("google_calendar")

    # 4. Probar endpoint OAuth con token
    logger.info("\n== Prueba con token de prueba ==")
    test_oauth_endpoint("google_calendar", test_token)

    # 5. Probar validación de token
    logger.info("\n== Prueba de validación de token ==")
    test_token_validation(test_token)

    logger.info("\nPruebas completadas.")


if __name__ == "__main__":
    main()
