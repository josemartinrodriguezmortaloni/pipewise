"""Test configuration and fixtures for pipewise application."""

import os
import uuid
from typing import AsyncGenerator, Dict, Any, TYPE_CHECKING
from unittest.mock import Mock, AsyncMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from pytest import MonkeyPatch


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for testing."""
    mock_client = Mock()
    mock_client.auth = Mock()
    mock_client.table = Mock()
    mock_client.storage = Mock()
    return mock_client


@pytest.fixture
def test_user():
    """Sample test user data as mock object."""
    user = Mock()
    user.id = str(uuid.uuid4())
    user.email = "test@example.com"
    user.name = "Test User"
    user.role = "admin"
    user.tenant_id = str(uuid.uuid4())
    user.is_active = True
    user.created_at = "2024-01-01T00:00:00Z"
    user.updated_at = "2024-01-01T00:00:00Z"
    return user


@pytest.fixture
def test_tenant():
    """Sample test tenant data as mock object."""
    tenant = Mock()
    tenant.id = str(uuid.uuid4())
    tenant.name = "Test Tenant"
    tenant.domain = "test.example.com"
    tenant.subscription_tier = "premium"
    tenant.is_active = True
    tenant.features_enabled = ["analytics", "custom_integrations", "premium_support"]
    tenant.api_limits = {"requests_per_minute": 100, "users_count": 5}
    tenant.created_at = "2024-01-01T00:00:00Z"
    tenant.updated_at = "2024-01-01T00:00:00Z"
    return tenant


@pytest.fixture
def test_agent_config() -> Dict[str, Any]:
    """Sample test agent configuration."""
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "name": "Test Agent",
        "type": "lead_qualifier",
        "enabled": True,
        "config": {"max_messages": 50, "timeout": 3600, "model": "gpt-4"},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def test_contact() -> Dict[str, Any]:
    """Sample test contact data."""
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "platform": "email",
        "status": "new",
        "tags": ["prospect", "qualified"],
        "metadata": {"source": "website"},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def test_conversation() -> Dict[str, Any]:
    """Sample test conversation data."""
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "contact_id": str(uuid.uuid4()),
        "agent_id": str(uuid.uuid4()),
        "platform": "email",
        "status": "active",
        "metadata": {"thread_id": "thread_123"},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def test_message() -> Dict[str, Any]:
    """Sample test message data."""
    return {
        "id": str(uuid.uuid4()),
        "conversation_id": str(uuid.uuid4()),
        "sender_type": "user",
        "content": "Hello, this is a test message",
        "platform": "email",
        "metadata": {"thread_id": "thread_123"},
        "created_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def test_lead() -> Dict[str, Any]:
    """Sample test lead data."""
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "contact_id": str(uuid.uuid4()),
        "score": 85,
        "status": "qualified",
        "qualification_notes": "Strong interest in our services",
        "next_action": "schedule_demo",
        "assigned_to": str(uuid.uuid4()),
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_environment(monkeypatch: "MonkeyPatch"):
    """Set up mock environment variables for testing."""
    test_env = {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test-anon-key",
        "OPENAI_API_KEY": "test-openai-key",
        "REDIS_URL": "redis://localhost:6379",
        "SECRET_KEY": "test-secret-key",
        "ENVIRONMENT": "test",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    return test_env


@pytest.fixture
def test_client(mock_environment, mock_supabase) -> TestClient:
    """Create a test client for the FastAPI application."""
    from app.api.main import app

    # Mock the Supabase dependency
    app.dependency_overrides = {}

    return TestClient(app)


@pytest.fixture
def authenticated_client(test_client: TestClient, test_user) -> TestClient:
    """Create an authenticated test client."""
    # Mock authentication for testing
    test_client.headers.update(
        {
            "Authorization": f"Bearer test-token",
            "X-User-ID": test_user.id,
            "X-Tenant-ID": test_user.tenant_id,
        }
    )
    return test_client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = AsyncMock()

    # Mock response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "Test AI response"
    mock_client.chat.completions.create.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=True)
    mock_client.ping = AsyncMock(return_value=True)
    return mock_client


@pytest.fixture
def mock_email_service():
    """Mock email service for testing."""
    mock_service = Mock()
    mock_service.send_email = AsyncMock(return_value=True)
    mock_service.get_emails = AsyncMock(return_value=[])
    return mock_service


@pytest.fixture
def mock_whatsapp_client():
    """Mock WhatsApp client for testing."""
    mock_client = Mock()
    mock_client.send_message = AsyncMock(return_value={"success": True})
    mock_client.get_messages = AsyncMock(return_value=[])
    return mock_client


@pytest.fixture
def mock_calendly_client():
    """Mock Calendly client for testing."""
    mock_client = Mock()
    mock_client.create_scheduling_link = AsyncMock(
        return_value="https://calendly.com/test"
    )
    mock_client.get_events = AsyncMock(return_value=[])
    return mock_client


@pytest.fixture
def sample_tenant_context(test_tenant) -> Dict[str, Any]:
    """Sample tenant context for testing."""
    return {
        "tenant_id": test_tenant.id,
        "name": test_tenant.name,
        "domain": test_tenant.domain,
        "subscription_tier": test_tenant.subscription_tier,
        "settings": {
            "max_agents": 10,
            "max_contacts": 1000,
            "features": ["lead_qualification", "meeting_scheduling"],
        },
    }


@pytest.fixture
async def mock_agent_tools():
    """Mock agent tools for testing."""
    tools = {
        "email_tool": Mock(),
        "whatsapp_tool": Mock(),
        "calendly_tool": Mock(),
        "search_tool": Mock(),
    }

    for tool in tools.values():
        tool.func = AsyncMock(return_value={"success": True, "data": "test"})

    return tools


@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    session = Mock()
    session.query = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session
