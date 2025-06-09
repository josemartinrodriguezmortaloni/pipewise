"""
Pytest configuration and fixtures for PipeWise
Following Rule 4.1: Use FastAPI TestClient with Fixtures
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from unittest.mock import Mock, patch
import tempfile
import os

# Import the application and database
from app.main import app
from app.database import Base, get_db, get_async_db
from app.core.config import get_settings, override_settings
from app.models.tenant import Tenant, TenantUsage
from app.models.user import User, Role
from app.models.lead import Lead
from app.core.dependencies import get_current_security_context, TenantSecurityContext


# ============================================================================
# DATABASE FIXTURES - Following Rule 4.2: Isolated Tests with Transactions
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_database_url():
    """Create a temporary test database URL"""
    # Use SQLite in memory for fast tests
    return "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
async def test_engine(test_database_url):
    """Create test database engine"""
    engine = create_async_engine(
        test_database_url,
        echo=False,
        pool_pre_ping=True,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session with transaction rollback
    Following Rule 4.2: Isolated Tests with Transactions
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()
    
    # Create session bound to connection
    async_session_maker = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    # Rollback transaction for test isolation
    await transaction.rollback()
    await connection.close()


@pytest.fixture
def sync_db_session(test_database_url):
    """
    Synchronous database session for legacy code tests
    """
    # Convert async URL to sync for SQLAlchemy
    sync_url = test_database_url.replace("+aiosqlite", "")
    engine = create_engine(sync_url, echo=False)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
    engine.dispose()


# ============================================================================
# APPLICATION FIXTURES
# ============================================================================

@pytest.fixture
def test_settings():
    """Override settings for testing"""
    override_settings(
        TESTING=True,
        DEBUG=True,
        DATABASE_URL="sqlite:///:memory:",
        JWT_SECRET_KEY="test-secret-key-for-testing-only",
        OPENAI_API_KEY="test-openai-key",
        RATE_LIMIT_PER_MINUTE=1000,  # Higher limit for tests
        LOG_LEVEL="DEBUG"
    )
    return get_settings()


@pytest.fixture
def test_client(db_session, test_settings) -> TestClient:
    """
    Create test client with database dependency override
    Following Rule 4.1: Use FastAPI TestClient with Fixtures
    """
    def override_get_db():
        yield db_session
    
    def override_get_async_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_async_db] = override_get_async_db
    
    with TestClient(app) as client:
        yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


# ============================================================================
# TENANT AND USER FIXTURES
# ============================================================================

@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant"""
    tenant = Tenant(
        id="test-tenant-001",
        name="Test Corporation",
        domain="test.com",
        subdomain="test",
        is_active=True,
        is_premium=False,
        plan_type="basic",
        features_enabled=["basic_crm", "lead_qualification", "email_integration"],
        api_limits={
            "requests_per_minute": 100,
            "leads_per_month": 1000,
            "users_count": 5
        },
        company_size="51-200",
        industry="technology",
        country="US",
        timezone="UTC"
    )
    
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    
    return tenant


@pytest.fixture
async def test_premium_tenant(db_session: AsyncSession) -> Tenant:
    """Create a premium test tenant"""
    tenant = Tenant(
        id="premium-tenant-001",
        name="Premium Corp",
        domain="premium.com",
        subdomain="premium",
        is_active=True,
        is_premium=True,
        plan_type="premium",
        features_enabled=[
            "basic_crm", "lead_qualification", "email_integration",
            "advanced_analytics", "custom_integrations", "priority_support"
        ],
        api_limits={
            "requests_per_minute": 1000,
            "leads_per_month": 10000,
            "users_count": 50
        },
        company_size="201-1000",
        industry="enterprise",
        country="US",
        timezone="UTC"
    )
    
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    
    return tenant


@pytest.fixture
async def test_role(db_session: AsyncSession) -> Role:
    """Create a test role"""
    role = Role(
        name="admin",
        display_name="Administrator",
        description="Full access to all features",
        permissions=["admin", "lead:read", "lead:write", "user:read", "user:write"],
        is_system_role=True
    )
    
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    
    return role


@pytest.fixture
async def test_user(db_session: AsyncSession, test_tenant: Tenant, test_role: Role) -> User:
    """Create a test user"""
    user = User(
        id="test-user-001",
        email="test@test.com",
        username="testuser",
        hashed_password="$2b$12$test.hashed.password",  # bcrypt hash for "password123"
        first_name="Test",
        last_name="User",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        tenant_id=test_tenant.id,
        timezone="UTC",
        language="en"
    )
    
    user.roles.append(test_role)
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest.fixture
async def test_lead(db_session: AsyncSession, test_tenant: Tenant) -> Lead:
    """Create a test lead"""
    lead = Lead(
        id="test-lead-001",
        name="John Doe",
        email="john.doe@example.com",
        company="Example Corp",
        phone="+1-555-0123",
        message="We need a CRM solution for our growing team",
        source="website_form",
        status="new",
        qualified=False,
        contacted=False,
        meeting_scheduled=False,
        tenant_id=test_tenant.id,
        metadata={
            "company_size": "25-50",
            "industry": "technology",
            "interest_level": "high"
        }
    )
    
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)
    
    return lead


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================

@pytest.fixture
def mock_security_context(test_user: User, test_tenant: Tenant) -> TenantSecurityContext:
    """Create a mock security context for authenticated requests"""
    return TenantSecurityContext(
        user=test_user,
        tenant=test_tenant,
        permissions=["admin", "lead:read", "lead:write"]
    )


@pytest.fixture
def authenticated_client(test_client: TestClient, mock_security_context: TenantSecurityContext):
    """
    Create an authenticated test client
    """
    def override_get_security_context():
        return mock_security_context
    
    app.dependency_overrides[get_current_security_context] = override_get_security_context
    
    # Add required headers
    test_client.headers.update({
        "X-Tenant-ID": mock_security_context.tenant.id,
        "Authorization": "Bearer test-token"
    })
    
    yield test_client
    
    # Clean up
    if get_current_security_context in app.dependency_overrides:
        del app.dependency_overrides[get_current_security_context]


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing AgentSDK"""
    with patch('agents.Runner.run_async') as mock_runner:
        # Mock response structure
        mock_result = Mock()
        mock_result.output = Mock()
        mock_result.output.qualified = True
        mock_result.output.qualification_score = 85.0
        mock_result.output.key_factors = ["Enterprise size", "Clear budget"]
        mock_result.output.recommendations = ["Schedule demo", "Send proposal"]
        
        mock_runner.return_value = mock_result
        yield mock_runner


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    with patch('app.supabase.supabase_client.SupabaseCRMClient') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_celery_task():
    """Mock Celery tasks"""
    with patch('celery.Task.delay') as mock_delay:
        mock_delay.return_value = Mock(id="test-task-id")
        yield mock_delay


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def temp_file():
    """Create a temporary file for testing file uploads"""
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp.write(b"Test file content")
        temp_path = temp.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def sample_lead_data():
    """Sample lead data for testing"""
    return {
        "name": "Jane Smith",
        "email": "jane.smith@techcorp.com",
        "company": "TechCorp Solutions",
        "phone": "+1-555-0456",
        "message": "Looking for an AI-powered CRM solution for our 150-person sales team. Budget is $50k annually.",
        "source": "website_form",
        "utm_params": {
            "campaign": "enterprise_landing",
            "medium": "paid_search"
        },
        "metadata": {
            "company_size": "100-500",
            "industry": "technology",
            "interest_level": "high",
            "budget_range": "$50k+",
            "decision_timeline": "Q1 2025"
        }
    }


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset Prometheus metrics before each test"""
    # Import metrics and reset them
    try:
        from app.core.middleware import REQUEST_COUNT, REQUEST_DURATION
        REQUEST_COUNT.clear()
        REQUEST_DURATION.clear()
    except ImportError:
        pass  # Metrics not available in test environment


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest settings"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add unit marker to tests in unit/ directory
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        # Add integration marker to tests in integration/ directory  
        elif "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        # Add e2e marker to tests in e2e/ directory
        elif "e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)


# ============================================================================
# ASYNC TEST UTILITIES
# ============================================================================

@pytest.fixture
def anyio_backend():
    """Configure anyio backend for async tests"""
    return "asyncio"