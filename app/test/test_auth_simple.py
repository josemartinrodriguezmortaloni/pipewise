"""
Tests simplificados del sistema de autenticación
Sin dependencias complejas - para verificar funcionalidad básica
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Configurar el path antes de imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configurar variables de entorno para tests
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


class TestAuthUtilities:
    """Tests de utilidades de autenticación"""

    def test_get_client_ip(self):
        """Test de extracción de IP del cliente"""
        from app.auth.utils import get_client_ip
        from fastapi import Request

        # Mock request con x-forwarded-for
        mock_request = Mock(spec=Request)
        mock_request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"

        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.1"

        # Mock request con x-real-ip
        mock_request.headers = {"x-real-ip": "192.168.1.2"}
        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.2"

        # Mock request sin headers especiales
        mock_request.headers = {}
        ip = get_client_ip(mock_request)
        assert ip == "127.0.0.1"

    def test_get_user_agent(self):
        """Test de extracción de User-Agent"""
        from app.auth.utils import get_user_agent
        from fastapi import Request

        mock_request = Mock(spec=Request)
        mock_request.headers = {"user-agent": "Mozilla/5.0 Test Browser"}

        user_agent = get_user_agent(mock_request)
        assert user_agent == "Mozilla/5.0 Test Browser"

        # Test sin user-agent
        mock_request.headers = {}
        user_agent = get_user_agent(mock_request)
        assert user_agent == "unknown"

    def test_generate_secure_token(self):
        """Test de generación de tokens seguros"""
        from app.auth.utils import generate_secure_token

        token1 = generate_secure_token()
        token2 = generate_secure_token()

        assert len(token1) > 20
        assert len(token2) > 20
        assert token1 != token2

        # Test con longitud específica
        short_token = generate_secure_token(16)
        long_token = generate_secure_token(64)
        assert len(short_token) != len(long_token)

    def test_hash_token(self):
        """Test de hash de tokens"""
        from app.auth.utils import hash_token, verify_token_hash

        token = "test-token-123"
        token_hash = hash_token(token)

        assert token_hash != token
        assert len(token_hash) == 64  # SHA256 hex length
        assert verify_token_hash(token, token_hash)
        assert not verify_token_hash("wrong-token", token_hash)

    def test_sanitize_email(self):
        """Test de sanitización de email"""
        from app.auth.utils import sanitize_email

        assert sanitize_email("TEST@EXAMPLE.COM") == "test@example.com"
        assert sanitize_email("  user@domain.com  ") == "user@domain.com"
        assert sanitize_email("Mixed.Case@Example.ORG") == "mixed.case@example.org"

    def test_is_development(self):
        """Test de detección de modo desarrollo"""
        from app.auth.utils import is_development

        # Ya configuramos ENVIRONMENT=test
        assert not is_development()

        # Test con environment development
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            assert is_development()

    def test_mask_sensitive_data(self):
        """Test de enmascarado de datos sensibles"""
        from app.auth.utils import mask_sensitive_data

        assert mask_sensitive_data("1234567890") == "1234******"
        assert mask_sensitive_data("abc") == "***"
        assert mask_sensitive_data("", 2) == ""
        assert mask_sensitive_data("test@example.com", 6) == "test@e**********"


class TestAuthClient:
    """Tests del cliente de autenticación (sin Supabase)"""

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock del cliente Supabase"""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = True
        mock_client.auth = MagicMock()
        return mock_client

    def test_password_hashing(self, mock_supabase_client):
        """Test de hash y verificación de contraseñas"""
        with patch("supabase.create_client", return_value=mock_supabase_client):
            from app.auth.auth_client import AuthenticationClient

            auth_client = AuthenticationClient()

            password = "TestPassword123!"
            hashed = auth_client._hash_password(password)

            # Verificar que el hash es diferente del password original
            assert hashed != password
            assert len(hashed) > 50  # bcrypt hashes son largos

            # Verificar que se puede validar
            assert auth_client._verify_password(password, hashed)
            assert not auth_client._verify_password("wrongpassword", hashed)

    def test_secure_token_generation(self, mock_supabase_client):
        """Test de generación de tokens seguros"""
        with patch("supabase.create_client", return_value=mock_supabase_client):
            from app.auth.auth_client import AuthenticationClient

            auth_client = AuthenticationClient()

            token1 = auth_client._generate_secure_token()
            token2 = auth_client._generate_secure_token()

            assert len(token1) > 20
            assert len(token2) > 20
            assert token1 != token2

    def test_backup_codes_generation(self, mock_supabase_client):
        """Test de generación de códigos de respaldo"""
        with patch("supabase.create_client", return_value=mock_supabase_client):
            from app.auth.auth_client import AuthenticationClient

            auth_client = AuthenticationClient()

            codes = auth_client._generate_backup_codes()

            assert len(codes) == 10
            assert all(len(code) == 8 for code in codes)
            # Los códigos pueden contener letras y números
            assert all(code.isalnum() for code in codes)
            assert len(set(codes)) == 10  # Todos únicos

    def test_totp_validation(self, mock_supabase_client):
        """Test de validación de códigos TOTP"""
        with patch("supabase.create_client", return_value=mock_supabase_client):
            from app.auth.auth_client import AuthenticationClient

            auth_client = AuthenticationClient()

            # Test con valores inválidos
            assert not auth_client._verify_totp_code("", "123456")
            assert not auth_client._verify_totp_code("INVALIDSECRET", "")
            assert not auth_client._verify_totp_code(None, "123456")


class TestEmailService:
    """Tests del servicio de email"""

    def test_initialization(self):
        """Test de inicialización del servicio"""
        from app.services.email_service import EmailService

        email_service = EmailService()

        # Verificar configuración
        assert email_service.smtp_server == "smtp.gmail.com"
        assert email_service.smtp_port == 587
        assert email_service.smtp_username == "test@example.com"
        assert (
            email_service.enabled is True
        )  # Debería estar habilitado con las credenciales mock

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test de health check del servicio de email"""
        from app.services.email_service import EmailService

        email_service = EmailService()
        health = await email_service.health_check()

        assert "status" in health
        assert "enabled" in health
        assert health["enabled"] is True


class TestRedisClient:
    """Tests del cliente Redis (modo memoria)"""

    def test_initialization(self):
        """Test de inicialización del cliente Redis"""
        from app.auth.redis_client import RedisAuthClient

        redis_client = RedisAuthClient()

        # Verificar configuración básica
        assert redis_client.redis_url is not None
        assert hasattr(redis_client, "enabled")

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test de health check básico"""
        from app.auth.redis_client import RedisAuthClient

        redis_client = RedisAuthClient()

        # Forzar modo memoria para el test
        redis_client.enabled = False

        health = await redis_client.health_check()
        assert "status" in health


class TestSchemas:
    """Tests de schemas de validación"""

    def test_user_register_validation(self):
        """Test de validación de registro de usuario"""
        from app.schemas.auth_schema import UserRegisterRequest

        # Datos válidos
        valid_data = {
            "email": "test@example.com",
            "password": "StrongPassword123!",
            "full_name": "Test User",
            "company": "Test Company",
        }

        user_request = UserRegisterRequest(**valid_data)
        assert user_request.email == "test@example.com"
        assert user_request.full_name == "Test User"

        # Test contraseña débil (debería fallar)
        with pytest.raises(ValueError):
            UserRegisterRequest(
                email="test@example.com", password="weak", full_name="Test User"
            )

    def test_user_login_validation(self):
        """Test de validación de login"""
        from app.schemas.auth_schema import UserLoginRequest

        login_data = {"email": "test@example.com", "password": "password123"}

        login_request = UserLoginRequest(**login_data)
        assert login_request.email == "test@example.com"
        assert login_request.password == "password123"

    def test_user_roles(self):
        """Test de roles de usuario"""
        from app.schemas.auth_schema import UserRole

        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.MANAGER.value == "manager"


# ===================== TESTS DE INTEGRACIÓN BÁSICA =====================


def test_imports_work():
    """Test básico de que todos los imports funcionan"""
    try:
        from app.auth.auth_client import AuthenticationClient
        from app.auth.redis_client import RedisAuthClient
        from app.services.email_service import EmailService
        from app.auth.utils import generate_secure_token
        from app.schemas.auth_schema import UserRole
        from app.models.user import User

        # Si llegamos aquí, todos los imports funcionaron
        assert True

    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


def test_environment_configuration():
    """Test de configuración de entorno"""
    assert os.getenv("ENVIRONMENT") == "test"
    assert os.getenv("SUPABASE_URL") == "https://test.supabase.co"
    assert os.getenv("JWT_SECRET") == "test-secret-key-for-testing-purposes"


# ===================== CONFIGURACIÓN DE PYTEST =====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
