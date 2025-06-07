# app/test/auth.py
import pytest
import asyncio
import secrets
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Agregar el directorio raíz al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configurar variables de entorno para tests ANTES de importar módulos
os.environ.update(
    {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0",
        "JWT_SECRET": "test-secret-key-for-testing-purposes",
        "REDIS_URL": "redis://localhost:6379/0",
        "SMTP_USERNAME": "test@example.com",
        "SMTP_PASSWORD": "test-password",
        "FROM_EMAIL": "test@example.com",
        "ENVIRONMENT": "test",
    }
)

# Mock Supabase globalmente antes de importar los módulos
mock_supabase_client = MagicMock()
mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = True
mock_supabase_client.auth = MagicMock()

# Aplicar patches globales
supabase_patch = patch("supabase.create_client", return_value=mock_supabase_client)
supabase_patch.start()

# Patch adicional para el cliente de auth
auth_client_patch = patch(
    "app.auth.auth_client.create_client", return_value=mock_supabase_client
)
auth_client_patch.start()

# Patch Redis para evitar errores de conexión
redis_patch = patch("redis.Redis")
redis_patch.start()

# Importaciones del proyecto después de configurar mocks
from app.schemas.auth_schema import (
    UserRegisterRequest,
    UserLoginRequest,
    UserRole,
    Enable2FARequest,
    Verify2FARequest,
    Login2FARequest,
)
from app.models.user import User

# Importar la aplicación FastAPI después de configurar todo
from app.api.main import app

# Cliente de prueba
client = TestClient(app)


class TestAuthenticationFlow:
    """Tests del flujo completo de autenticación"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup automático de mocks para cada test"""
        with (
            patch("app.api.auth.auth_client") as mock_auth,
            patch("app.auth.redis_client.redis_auth_client") as mock_redis,
            patch("app.services.email_service.email_service") as mock_email,
        ):
            # Configurar mocks por defecto
            mock_auth.register_user = AsyncMock()
            mock_auth.login_user = AsyncMock()
            mock_auth.login_with_2fa = AsyncMock()
            mock_auth.refresh_token = AsyncMock()
            mock_auth.enable_2fa = AsyncMock()
            mock_auth.verify_2fa_setup = AsyncMock()
            mock_auth.disable_2fa = AsyncMock()
            mock_auth.get_user_by_id = AsyncMock()
            mock_auth._get_current_timestamp = lambda: datetime.utcnow()
            mock_auth.client = mock_supabase_client

            mock_redis.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_email.health_check = AsyncMock(return_value={"status": "healthy"})

            self.mock_auth = mock_auth
            self.mock_redis = mock_redis
            self.mock_email = mock_email
            yield

    @pytest.fixture
    def sample_user_data(self):
        """Datos de usuario de prueba"""
        return {
            "email": f"test.{secrets.token_hex(4)}@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User",
            "company": "Test Company",
            "role": "user",
        }

    @pytest.fixture
    def sample_user(self):
        """Usuario de prueba"""
        return User(
            id="123e4567-e89b-12d3-a456-426614174000",
            email="test@example.com",
            full_name="Test User",
            company="Test Company",
            role=UserRole.USER,
            is_active=True,
            email_confirmed=True,
            has_2fa=False,
            created_at=datetime.utcnow(),
        )

    # ===================== TESTS BÁSICOS =====================

    def test_root_endpoint(self):
        """Test del endpoint raíz"""
        response = client.get("/")

        # Verificar respuesta
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "PipeWise CRM API with Authentication"
        assert data["version"] == "2.0.0"

    def test_main_health_check(self):
        """Test de health check principal"""
        response = client.get("/health")

        # Verificar respuesta
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data

    def test_auth_health_check(self):
        """Test de health check del sistema de autenticación"""
        response = client.get("/auth/health")

        # Verificar respuesta
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    # ===================== TESTS DE REGISTRO =====================

    def test_register_user_success(self, sample_user_data):
        """Test de registro exitoso"""
        # Configurar mock
        self.mock_auth.register_user.return_value = {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "email": sample_user_data["email"],
            "full_name": sample_user_data["full_name"],
            "role": UserRole.USER.value,
            "email_confirmed": False,
            "message": "User registered successfully",
        }

        # Hacer request
        response = client.post("/auth/register", json=sample_user_data)

        # Verificar respuesta
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["full_name"] == sample_user_data["full_name"]
        assert "user_id" in data

    def test_register_user_email_exists(self, sample_user_data):
        """Test de registro con email existente"""
        # Configurar mock para email existente
        self.mock_auth.register_user.side_effect = ValueError(
            "Email already registered"
        )

        # Hacer request
        response = client.post("/auth/register", json=sample_user_data)

        # Verificar respuesta
        assert response.status_code == 400
        data = response.json()
        assert "Email already registered" in data["detail"]

    def test_register_user_invalid_password(self, sample_user_data):
        """Test de registro con contraseña inválida"""
        sample_user_data["password"] = "weak"  # Contraseña débil

        response = client.post("/auth/register", json=sample_user_data)

        # Verificar que falla la validación
        assert response.status_code == 422  # Validation error

    def test_register_user_invalid_email(self, sample_user_data):
        """Test de registro con email inválido"""
        sample_user_data["email"] = "invalid-email"

        response = client.post("/auth/register", json=sample_user_data)

        # Verificar que falla la validación
        assert response.status_code == 422  # Validation error

    # ===================== TESTS DE LOGIN =====================

    def test_login_success_without_2fa(self, sample_user):
        """Test de login exitoso sin 2FA"""
        # Configurar mock
        self.mock_auth.login_user.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "token_type": "bearer",
            "expires_in": 1800,
            "user": {
                "user_id": str(sample_user.id),
                "email": sample_user.email,
                "full_name": sample_user.full_name,
                "role": sample_user.role.value,
            },
            "requires_2fa": False,
        }

        login_data = {"email": "test@example.com", "password": "TestPassword123!"}

        response = client.post("/auth/login", json=login_data)

        # Verificar respuesta
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["requires_2fa"] is False
        assert data["user"]["email"] == sample_user.email

    def test_login_requires_2fa(self):
        """Test de login que requiere 2FA"""
        # Configurar mock para requerir 2FA
        self.mock_auth.login_user.return_value = {
            "requires_2fa": True,
            "temp_token": "temp-2fa-token",
            "message": "2FA code required",
        }

        login_data = {"email": "test@example.com", "password": "TestPassword123!"}

        response = client.post("/auth/login", json=login_data)

        # Verificar respuesta
        assert response.status_code == 200
        data = response.json()
        assert data["requires_2fa"] is True
        assert "temp_token" in data

    def test_login_invalid_credentials(self):
        """Test de login con credenciales inválidas"""
        # Configurar mock para credenciales inválidas
        self.mock_auth.login_user.side_effect = ValueError("Invalid email or password")

        login_data = {"email": "test@example.com", "password": "wrongpassword"}

        response = client.post("/auth/login", json=login_data)

        # Verificar respuesta
        assert response.status_code == 401
        data = response.json()
        assert "Invalid email or password" in data["detail"]

    # ===================== TESTS DE TOKENS =====================

    def test_refresh_token_success(self):
        """Test de renovación de token exitosa"""
        # Configurar mock
        self.mock_auth.refresh_token.return_value = {
            "access_token": "new-access-token",
            "token_type": "bearer",
            "expires_in": 1800,
        }

        refresh_data = {"refresh_token": "valid-refresh-token"}

        response = client.post("/auth/refresh", json=refresh_data)

        # Verificar respuesta
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self):
        """Test de renovación con token inválido"""
        # Configurar mock para token inválido
        self.mock_auth.refresh_token.side_effect = ValueError("Invalid refresh token")

        refresh_data = {"refresh_token": "invalid-refresh-token"}

        response = client.post("/auth/refresh", json=refresh_data)

        # Verificar respuesta
        assert response.status_code == 401
        data = response.json()
        assert "Invalid refresh token" in data["detail"]

    @patch("app.auth.middleware.get_current_user")
    def test_validate_token_success(self, mock_get_user):
        """Test de validación de token exitosa"""
        mock_get_user.return_value = User(
            id="123e4567-e89b-12d3-a456-426614174000",
            email="test@example.com",
            full_name="Test User",
            role=UserRole.USER,
            is_active=True,
        )

        headers = {"Authorization": "Bearer valid-token"}
        response = client.get("/auth/validate", headers=headers)

        # Verificar respuesta
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "user" in data

    # ===================== TESTS DE PERFIL =====================

    @patch("app.auth.middleware.get_current_user")
    def test_get_user_profile(self, mock_get_user):
        """Test de obtención de perfil de usuario"""
        mock_get_user.return_value = User(
            id="123e4567-e89b-12d3-a456-426614174000",
            email="test@example.com",
            full_name="Test User",
            company="Test Company",
            role=UserRole.USER,
            is_active=True,
            email_confirmed=True,
            has_2fa=False,
            created_at=datetime.utcnow(),
        )

        headers = {"Authorization": "Bearer valid-token"}
        response = client.get("/auth/profile", headers=headers)

        # Verificar respuesta
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["company"] == "Test Company"


class TestSimpleFunctionality:
    """Tests simples sin dependencias complejas"""

    def test_password_validation(self):
        """Test de validación de contraseña"""
        from app.auth.auth_client import AuthenticationClient

        # Crear cliente sin conectar a Supabase
        with patch("supabase.create_client", return_value=mock_supabase_client):
            auth_client = AuthenticationClient()

            # Test hash de contraseña
            password = "TestPassword123!"
            hashed = auth_client._hash_password(password)

            assert hashed != password
            assert auth_client._verify_password(password, hashed)
            assert not auth_client._verify_password("wrongpassword", hashed)

    def test_secure_token_generation(self):
        """Test de generación de token seguro"""
        from app.auth.auth_client import AuthenticationClient

        with patch("supabase.create_client", return_value=mock_supabase_client):
            auth_client = AuthenticationClient()

            token1 = auth_client._generate_secure_token()
            token2 = auth_client._generate_secure_token()

            assert len(token1) > 20
            assert len(token2) > 20
            assert token1 != token2

    def test_backup_codes_generation(self):
        """Test de generación de códigos de respaldo"""
        from app.auth.auth_client import AuthenticationClient

        with patch("supabase.create_client", return_value=mock_supabase_client):
            auth_client = AuthenticationClient()

            codes = auth_client._generate_backup_codes()

            assert len(codes) == 10
            assert all(len(code) == 8 for code in codes)
            assert len(set(codes)) == 10  # Todos únicos


class TestUtilities:
    """Tests de utilidades"""

    def test_client_ip_extraction(self):
        """Test de extracción de IP del cliente"""
        from app.auth.utils import get_client_ip
        from fastapi import Request

        # Mock request con headers
        mock_request = Mock(spec=Request)
        mock_request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"

        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.1"

    def test_token_operations(self):
        """Test de operaciones con tokens"""
        from app.auth.utils import generate_secure_token, hash_token, verify_token_hash

        token = generate_secure_token()
        token_hash = hash_token(token)

        assert verify_token_hash(token, token_hash)
        assert not verify_token_hash("wrong-token", token_hash)


# ===================== CONFIGURACIÓN DE PYTEST =====================


@pytest.fixture(scope="session")
def event_loop():
    """Crear event loop para tests async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ===================== HELPERS PARA TESTS =====================


def create_test_user() -> User:
    """Crear usuario de prueba"""
    return User(
        id="123e4567-e89b-12d3-a456-426614174000",
        email="test@example.com",
        full_name="Test User",
        company="Test Company",
        role=UserRole.USER,
        is_active=True,
        email_confirmed=True,
        has_2fa=False,
        created_at=datetime.utcnow(),
    )


def create_admin_user() -> User:
    """Crear usuario administrador de prueba"""
    return User(
        id="456e7890-e89b-12d3-a456-426614174000",
        email="admin@example.com",
        full_name="Admin User",
        company="Admin Company",
        role=UserRole.ADMIN,
        is_active=True,
        email_confirmed=True,
        has_2fa=True,
        created_at=datetime.utcnow(),
    )


# Cleanup de patches al final
def pytest_unconfigure():
    """Cleanup de patches globales"""
    try:
        supabase_patch.stop()
        auth_client_patch.stop()
        redis_patch.stop()
    except:
        pass


# ===================== CONFIGURACIÓN PARA EJECUTAR TESTS =====================

if __name__ == "__main__":
    # Ejecutar tests con pytest
    pytest.main([__file__, "-v", "--tb=short", "--disable-warnings"])
